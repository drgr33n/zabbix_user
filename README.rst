Ansible Zabbix User Module
==========================

This module allows you to create, modify and delete Zabbix users. Password updates are not supported for now.
This is due to the limitations of using the API. I'm working on this now.

Requirements
------------

The below requirements are needed on the host that executes this module.

* python >= 2.6
* zabbix-api >= 0.5.3

Example playbook
----------------

Create / Update a user

.. code-block::

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


Remove a user

.. code-block::

    - name: remove user
        local_action:
        module: zabbix_user
        server_url: http://zabbix.dev.local
        login_user: admin
        login_password: zabbix
        state: absent
        alias: drgr33n


Contact
-------

:author: Zarren Spry <zarrenspry@gmail.com>