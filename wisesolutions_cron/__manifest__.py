# -*- coding: utf-8 -*-
{
    'name': 'Wise Solutions: Remote Database Backup Cron',
    'summary': '''
        Moves the backup files found in Odoo.sh in the
        /home/odoo/backup.daily file to an sftp server
    ''',
    'description': '''
        MPV - TASK ID: 2497635
        Runs a scheduled action every 5 minutes to check
        whether odoo.sh has created a new backup. If it
        has, then it will move the backup that should be
        found in /home/odoo/backup.daily file to the
        specified sftp server
    ''',
    'license': 'OPL-1',
    'author': 'Odoo Inc',
    'website': 'https://www.odoo.com',
    'category': 'Development Services/Custom Development',
    'version': '1.0',
    'depends': [
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/backup_data.xml',
        'views/backup_views.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False
}