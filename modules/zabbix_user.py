#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) 2019 Zarren Spry <zarrenspry@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}


DOCUMENTATION = '''
---
module: zabbix_user
short_description: Create/update/delete Zabbix users
description:
   - This module allows you to create, modify and delete Zabbix users.
version_added: "2.8"
author:
    - Zarren Spry (@drgr33n)
requirements:
    - "python >= 2.6"
    - "zabbix-api >= 0.5.3"
options:
    alias:
        description:
            - User alias. This is also used as the username.
        required: True
        type: string
    autologin:
        description:
            - Whether to enable auto-login.
        type: bool
        default: False
    autologout:
        description:
            - User session life time. Accepts seconds and time unit with suffix. If set to 0s, the session will never expire.
        type: string
        default: 15m
    lang:
        description:
            - Language code of the user's language.
        type: string
        default: en_GB
    user_password:
        description:
            - User password, required when I(state=present).
        type: string
        required: True
    user_name:
        description:
            - Name of the user.
        type: string
    refresh:
        description:
            - Automatic refresh period. Accepts seconds and time unit with suffix.
        type: string
        default: 30s
    rows_per_page:
        description:
            - Amount of object rows to show per page. 
        type: integer
        default: 50
    user_surname:
        description:
            - Surname of the user.
        type: string
    user_theme:
        description: 
            - User's theme. I'm pretty sure you can also use a custom theme name if you require.
        choices: [
            "default",
            "blue-theme",
            "dark-theme"
        ]
        type: string
        default: default
    user_type:
        description:
            - Type of the user.
            - Possible values.
            -   1. (default) Zabbix user;
            -   2. Zabbix admin;
            -   3. Zabbix super admin;
        choices: [
            1,
            2,
            3
        ]
        type: integer
        default: 1
    redirect_url:
        description:
            - URL of the page to redirect the user to after logging in.
        type: string
    state:
        description:
            - State of the user.
            - On C(present), it will create if the user does not exist or update the user if the associated data is different.
            - On C(absent) will remove a user if it exists.
        choices: [
            'present',
            'absent'
        ]
        default: 'present'
        required: True
    user_groups:
        description:
            - User groups to add the user to. The user groups must have the usrgrpid property defined.
        type: list
        suboptions:
            usrgrpid:
                description:
                    - ID of the user group.
                type: string
    user_medias:
        description:
            - Medias to create for the user.
        type: list
        suboptions:
            mediatypeid:
                description:
                    - ID of the media type used by the media.
                required: True
                type: string
            sendto:
                description:
                    - Address, user name or other identifier of the recipient. If type of Media type is e-mail, values are represented as list. For other types of Media types, value is represented as a string.
                required: True
                type: string / dict
            active:
                description: 
                    - Whether the media is enabled.
                type: bool
                default: True
            severity:
                description:
                    - Trigger severities to send notifications about. Severities are stored in binary form with each bit representing the corresponding severity. For example, 12 equals 1100 in binary and means, that notifications will be sent from triggers with severities warning and average.
                type: integer
                default: 63
            period:
                description:
                    - Time when the notifications can be sent as a time period or user macros separated by a semicolon.
                default: 1-7,00:00-24:00
                type: string
extends_documentation_fragment:
    - zabbix
'''

EXAMPLES = '''
# Create a new user example
- name: Create user drgr33n
    local_action:
    module: zabbix_user
    server_url: http://monitor.example.com
    login_user: username
    login_password: password
    state: present
    alias: drgr33n
    user_name: Zarren
    user_surname: Spry
    user_type: 3 # Superadmin
    user_groups:
        usrgrpid: 7
    user_medias:
        - mediatypeid: 1
            sendto:
            - drgr33n@gmail.com
            - zarrenspry@gmail.com

# Remove user
- name: remove user
    local_action:
    module: zabbix_user
    server_url: http://zabbix.dev.local
    login_user: admin
    login_password: zabbix
    state: absent
    alias: drgr33n
'''

import json
import atexit
import traceback

try:
    from zabbix_api import ZabbixAPI
    HAS_ZABBIX_API = True
except ImportError:
    ZBX_IMP_ERR = traceback.format_exc()
    HAS_ZABBIX_API = False

from ansible.module_utils.basic import AnsibleModule, missing_required_lib

class User(object):
    def __init__(self, module, zbx):
        self._module = module
        self._zapi = zbx


    def check_user_exist(self, alias):
        try:
            result = self._zapi.user.get(
                {
                    "filter": {
                        "alias": alias
                    }
                }
            )
            return result
        except Exception as err:
            self._module.fail_json(
                msg="Failed to check if the user '%s' exists. Msg: %s" % (alias, err)
            )


    def _get_user_id(self, alias):
        try:
            result = self._zapi.user.get(
                {
                    "filter": {
                        "alias": alias
                    }
                }
            )
            if result:
                return result[0]["userid"]
            else:
                self._module.fail_json(
                    msg="The user '%s' does not exists." % alias
                )
        except Exception as err:
            self._module.fail_json(
                msg="Failed to get the ID for the user '%s'. Msg: %s" % (alias, err)
            )


    def _get_user_state(self, alias, medias):
        media_keys = list(medias[0].keys())
        try:
            result = self._zapi.user.get(
                {
                    "output": [
                        "alias",
                        "autologin",
                        "autologout",
                        "lang",
                        "name",
                        "passwd",
                        "refresh",
                        "url",
                        "rows_per_page",
                        "surname",
                        "theme",
                        "type"
                    ],
                    "selectUsrgrps": "usrgrpid",
                    "selectMedias": media_keys,
                    "userids": self._get_user_id(alias)
                }
            )
            return result[0]
        except Exception as err:
            self._module.fail_json(
                msg="Failed to get the state for the user '%s'. Msg: %s" % (alias, err)
            )


    def create_user(self, alias, autologin, autologout, lang, redirect_url, refresh,
                    rows_per_page, user_groups, user_medias, user_name, user_password, 
                    user_surname, user_theme, user_type):
        try:
            if self._module.check_mode:
                self._module.exit_json(changed=True)
            params = {
                'alias': alias,
                'autologin': autologin,
                'autologout': autologout,
                'lang': lang,
                'name': user_name,
                'passwd': user_password,
                'refresh': refresh,
                'url': redirect_url,
                'rows_per_page': rows_per_page,
                'surname': user_surname,
                'theme': user_theme,
                'type': user_type,
                'usrgrps': user_groups,
                'user_medias': user_medias
            }
            self._zapi.user.create(params)
            self._module.exit_json(
                changed=True,
                result="Successfully created user '%s'." % alias
            )
        except Exception as err:
            self._module.fail_json(
                msg="Failed create the user '%s'. Msg: %s" % (alias, err)
            )


    def delete_user(self, alias):
        try:
            uid = self._get_user_id(alias)
            if uid:
                self._zapi.user.delete(
                    [
                        str(uid)
                    ]
                )
                self._module.exit_json(
                    changed=True,
                    result="Successfully deleted user '%s'." % alias
                )
            else:
                self._module.fail_json(
                    msg="The user '%s' does not exists." % alias
                )
        except Exception as err:
            self._module.fail_json(
                msg="Failed to remove the user '%s'. Msg: %s" % (alias, err)
            )


    def update_user(self, alias, autologin, autologout, lang, redirect_url, refresh,
                    rows_per_page, user_groups, user_medias, user_name, user_password,
                    user_surname, user_theme, user_type):
        try:
            params = {
                'userid': self._get_user_id(alias),
                'alias': alias,
                'autologin': autologin,
                'autologout': autologout,
                'lang': lang,
                'name': user_name,
                'passwd': user_password,
                'refresh': refresh,
                'url': redirect_url,
                'rows_per_page': rows_per_page,
                'surname': user_surname,
                'theme': user_theme,
                'type': user_type,
                'usrgrps': user_groups,
                'user_medias': user_medias
            }
            nstate = params
            del nstate['passwd']
            cstate = self._get_user_state(alias, params['user_medias'])
            cstate['user_medias'] = cstate.pop("medias")
                        
            #cstate = { k:str(v) for (k,v) in cstate_raw.items()}
            #nstate = { k:str(v) for (k,v) in nstate_raw.items()}

            if cstate != nstate:
                self._zapi.user.update(params)
                self._module.exit_json(
                    changed=True,
                    result="Successfully updated user '%s'.              cstate: '%s'              nstate: '%s'" % (alias, cstate, nstate)
                )
            else:
                self._module.exit_json(
                    changed=False,
                    result="No changes to the user '%s' required." % alias
                )
        except Exception as err:
            self._module.fail_json(
                msg="Failed to update the user '%s'. Msg: %s" % (alias, err)
            )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            alias=dict(
                type='str',
                required=True
            ),
            server_url=dict(
                type='str',
                required=True,
                aliases=[
                    'url'
                ]
            ),
            login_user=dict(
                type='str',
                required=True
            ),
            login_password=dict(
                type='str',
                required=False,
                no_log=True
            ),
            autologin=dict(
                type='bool',
                default=False
            ),
            autologout=dict(
                type='str',
                required=False,
                default="15m"
            ),
            http_login_user=dict(
                type='str',
                required=False,
                default=None
            ),
            http_login_password=dict(
                type='str',
                required=False,
                default=None,
                no_log=True
            ),
            lang=dict(
                type='str',
                default='en_GB',
                required=False
            ),
            user_name=dict(
                type='str',
                default=None,
                required=False
            ),
            user_password=dict(
                type='str',
                default=None,
                no_log=True
            ),
            redirect_url=dict(
                type='str',
                required=False,
                default=""
            ),
            refresh=dict(
                type='str',
                required=False,
                default='30s'
            ),
            rows_per_page=dict(
                type='int',
                required=False,
                default=50
            ),
            state=dict(
                default="present",
                choices=[
                    'present',
                    'absent'
                ]
            ),
            user_surname=dict(
                type='str',
                default=None,
                required=False
            ),
            user_theme=dict(
                type='str',
                default="default", 
                choices=[
                    "default",
                    "blue-theme",
                    "dark-theme"
                ],
                required=False
            ),
            timeout=dict(
                type='int',
                default=10,
                required=False
            ),
            user_type=dict(
                type='int',
                default=1,
                choices=[
                    1,
                    2,
                    3
                ],
                required=False
            ),
            user_groups=dict(
                type='list',
                required=False
            ),
            user_medias=dict(
                type='list',
                required=False,
                options=dict(
                    active=dict(
                        type='bool',
                        default=True,
                        required=False
                    ),
                    mediatypeid=dict(
                        type='int',
                        required=True
                    ),
                    period=dict(
                        type='str',
                        required=False,
                        default="1-7,00:00-24:00"
                    ),
                    sendto=dict(
                        type='list',
                        required=True,
                    ),
                    severity=dict(
                        type='str',
                        required=False,
                        default="63"
                    )
                )
            ),
            validate_certs=dict(
                type='bool',
                required=False,
                default=True
            )
        ),
        required_if=[
            (
                "state",
                "present",
                [
                    "user_password"
                ]
            )
        ],
        supports_check_mode=True
    )

    if not HAS_ZABBIX_API:
        module.fail_json(
            msg=missing_required_lib(
                'zabbix-api',
                url='https://pypi.org/project/zabbix-api/'
            ),
            exception=ZBX_IMP_ERR
        )

    server_url = module.params['server_url']
    login_user = module.params['login_user']
    login_password = module.params['login_password']
    http_login_user = module.params['http_login_user']
    http_login_password = module.params['http_login_password']
    validate_certs = module.params['validate_certs']
    state = module.params['state']
    timeout = module.params['timeout']
    alias = module.params['alias']
    if module.params['autologin'] is False:
        autologin = "0"
    else:
        autologin = "1"
    autologout = module.params['autologout']
    http_login_password = module.params['http_login_password']
    http_login_user = module.params['http_login_user']
    lang = module.params['lang']
    login_password = module.params['login_password']
    login_user = module.params['login_user']
    module.params['redirect_url']
    redirect_url = module.params['redirect_url']
    refresh = module.params['refresh']
    rows_per_page = str(module.params['rows_per_page'])
    server_url = module.params['server_url']
    state = module.params['state']
    timeout = module.params['timeout']
    user_groups = module.params['user_groups']
    user_medias = module.params.get('user_medias')
    user_name = module.params['user_name']
    user_password = module.params['user_password']
    user_surname = module.params['user_surname']
    user_theme = module.params['user_theme']
    user_type = str(module.params['user_type'])
    validate_certs = module.params['validate_certs']

    # Convert int to str
    for usrgrp_entry in user_groups:
        usrgrp_entry['usrgrpid'] = str(usrgrp_entry['usrgrpid'])
    for medias_entry in user_medias:
        if 'mediatypeid' in medias_entry:
            medias_entry['mediatypeid'] = str(medias_entry['mediatypeid'])
        if 'severity' in medias_entry:
            medias_entry['severity'] = str(medias_entry['severity'])
    zbx = None
    try:
        zbx = ZabbixAPI(
            server_url,
            timeout=timeout,
            user=http_login_user,
            passwd=http_login_password,
            validate_certs=validate_certs
        )
        zbx.login(
            login_user,
            login_password
        )
        atexit.register(zbx.logout)
    except Exception as e:
        module.fail_json(msg="Failed to connect to Zabbix server: %s" % e)

    user = User(module, zbx)
    
    if state == "absent":
        user.delete_user(alias)
    if state == "present":
        if user.check_user_exist(alias):
            user.update_user(
                alias,
                autologin,
                autologout,
                lang,
                redirect_url,
                refresh,
                rows_per_page,
                user_groups,
                user_medias,
                user_name,
                user_password,
                user_surname,
                user_theme,
                user_type
            )
        else:
            user.create_user(
                alias,
                autologin,
                autologout,
                lang,
                redirect_url,
                refresh,
                rows_per_page,
                user_groups,
                user_medias,
                user_name,
                user_password,
                user_surname,
                user_theme,
                user_type
            )
if __name__ == '__main__':
    main()
