# -*- coding:utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning
from stat import S_ISDIR
import os
import time
import ipaddress
import logging
import fnmatch
import paramiko
import shutil


_log = logging.getLogger(__name__)

class Backup(models.Model):
    _name = 'wise.backup'
    _description = 'Daily Cron backup'
    _rec_name = 'backup_name'

    demo_mode = fields.Boolean(string='Demo Mode', default=False)
    backup_name = fields.Char(string='Backup Name', required=True)
    backup_dir = fields.Char(string='Odoo Daily Backup Directory', default = '/home/odoo/backup.daily/')
    backup_time = fields.Float(string='Previous Backup Time')

    sftp_host = fields.Char(string='SFTP Host', required=True, default='localhost')
    sftp_port = fields.Integer(string='SFTP Port', required=True, default=22)
    sftp_user = fields.Char(string='SFTP Username', required=True)
    sftp_pass = fields.Char(string='SFTP Password', required=True)
    sftp_dir = fields.Char(string='SFTP Backup Directory', required=True)
    sftp_del = fields.Boolean(string='Delete previous backups on SFTP', default=False)

    '''
    Make sure sftp_host is either a valid ip address,
    or that it is 'localhost'
    '''
    @api.constrains('sftp_host')
    def _ensure_valid_ip(self):
        for rec in self:
            if rec.sftp_host != 'localhost':
                try:
                    ipaddress.ip_address(rec.sftp_host)
                except:
                    raise ValidationError(_('Invalid IP Address for SFTP Host'))
    # '''
    # Make sure that backup_dir exists to help user with
    # troubleshooting
    # '''
    # @api.constrains('backup_dir')
    # def _ensure_valid_dir(self):
    #     for rec in self:
    #         if not os.path.exists(rec.backup_dir) and not rec.demo_mode:
    #             raise ValidationError(_('Invalid Odoo Daily Backup Directory'))
    
    @api.model_create_multi
    def create(self, vals_list):
        new_backups = super(Backup, self).create(vals_list)
        for backup in new_backups:
            if backup.demo_mode:
                demo_cwd = '/home/odoo/backup.daily.test'
                backup._create_demo_data(demo_cwd)
                backup.backup_dir = demo_cwd
        return new_backups

    '''
    If demo_mode is changed to true, change the the backup_dir to the
    demo directory, and make the directory if it doesn't exist
    '''
    def write(self, vals):
        if 'demo_mode' in vals:
            demo_cwd = '/home/odoo/backup.daily.test'
            if vals['demo_mode']:
                self._create_demo_data(demo_cwd)
                self.backup_dir = demo_cwd
            else:
                self._delete_demo_data(demo_cwd)
                self.backup_dir = '/home/odoo/backup.daily'
        
        return super(Backup, self).write(vals)
    
    
    '''
    Action that tests if sftp connection is valid. Raises a Warning
    popup that shows whether the connection is successful or not.
    '''
    def test_connection(self):
        ssh = self._ssh()
        if type(ssh) == str:
            popup_msg = f'Could not connect to the remote SFTP. Full Error: {ssh}'
        else:
            ssh.open_sftp()
            popup_msg = 'Don\'t worry, nothing went wrong. Successfully connected to remote SFTP'
            ssh.close()
        raise Warning(_(popup_msg))

    '''
    This function will run every 5 minutes via a scheduled action. It checks 
    the time the backup folder was last modified, and if it does not match
    the stored time, it will send the new backup to the sftp server
    '''
    def check_backup(self):
        '''
        Since we can create multiple backups,
        run them all, though will typically 
        just be 1 
        '''
        for rec in self.search([]):
            if not os.path.exists(rec.backup_dir):
                _log.critical(f'The folder {rec.backup_dir} does not exist')
                continue
            
            '''
            If demo_mode is enabled, then delete the old
            backup and make a new one
            '''
            if rec.demo_mode:
                rec._refresh_demo_data()

            '''
            If rec.backup_time == 0, then there was never a backup made
            '''
            if rec.backup_time == 0 or rec.backup_time != os.path.getmtime(rec.backup_dir):
                try:
                    old_backup_time = rec.backup_time
                    rec.backup_time = os.path.getmtime(rec.backup_dir)
                    sql_file_name, json_file_name = rec._prepare_backup()
                    rec._transfer_backup(sql_file_name, json_file_name)
                except Exception as e:
                    rec.backup_time = old_backup_time
                    _log.critical(str(e))
                _log.info('New backup was detected and sent to the remote ftp server')
            else:
                _log.info('This backup should already exist on SFTP server, skipping')

    '''
    Returns the full file names of the tar'd sql file and the
    json metadata file. Will throw an exception if either of 
    them do not exist, or if self.backup_dir does not exist
    '''
    def _prepare_backup(self):
        '''
        Make sure that the backup_dir still exists and that it's 
        a valid directory
        '''
        if os.path.exists(self.backup_dir) and os.path.isdir(self.backup_dir):
            os.chdir(self.backup_dir)
            sql_file_name = ''
            json_file_name = ''
            for file in os.listdir('.'):
                if fnmatch.fnmatch(file, '*.sql.gz'):
                    sql_file_name = file
                if fnmatch.fnmatch(file, '*.json'):
                    json_file_name = file

            if sql_file_name == '':
                raise Exception('The sql backup file does not exist')
            elif json_file_name == '':
                raise Exception('The json backup metadata does not exist')
            else:
                return os.path.join(self.backup_dir,sql_file_name), \
                       os.path.join(self.backup_dir, json_file_name)
        else:  
            raise Exception(f'The folder {self.backup_dir} does not exist or is not a directory')

    def _transfer_backup(self, sql_file, json_file):
        ssh = self._ssh()
        if type(ssh) == str:
            return
        sftp = ssh.open_sftp()

        if self.sftp_del:
            self._delete_old_backups(sftp)
        try:
            sftp.chdir(self.sftp_dir)
            backup_folder_name = f'backup_{time.strftime("%Y_%m_%d_%H_%M_%S")}'
            sftp.mkdir(backup_folder_name)
            sftp.chdir(backup_folder_name)
            sftp.put(json_file, 'json_metadata.json')
            sftp.put(sql_file, 'sql_backup.sql.gz')
        except Exception as e:
            _log.critical(f'Could not place the files in the sftp directory: {str(e)}')
        finally:
            sftp.close()
            ssh.close()

    def _delete_old_backups(self, sftp):
        try:
            remoteArtifactPath = self.sftp_dir
            filesInRemoteArtifacts = sftp.listdir(path=remoteArtifactPath)
            for file in filesInRemoteArtifacts:
                file_path = os.path.join(self.sftp_dir, file)
                if self._isdir(sftp, os.path.join(self.sftp_dir, file)):
                    self._rm(sftp, file_path)
                else:
                    sftp.remove(file_path)
        except Exception as e:
            _log.critical(f'Could not delete the previous files: {str(e)}')

    '''
    Tries to connect to the remote ftp server. If the return type is 
    an ssh client, then it was successful. If the return type is a str
    then there was an error, and the return string is the message 
    describing what went wrong
    '''
    def _ssh(self):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.sftp_host, self.sftp_port, self.sftp_user, self.sftp_pass, timeout=10)
            return ssh

        except Exception as e:
            _log.critical(f'Could not connect to the remote ftp: {str(e)}')
            if ssh:
                ssh.close()
                return str(e)

    def _isdir(self, sftp, path):
        try:
            return S_ISDIR(sftp.stat(path).st_mode)
        except IOError:
            return False

    '''
    Will recursively delete a folder given as 
    path
    '''
    def _rm(self, sftp, path):
        for f in sftp.listdir(path=path):
            filepath = os.path.join(path, f)
            if self._isdir(sftp,filepath):
                self._rm(sftp, filepath)
            else:
                sftp.remove(filepath)
        sftp.rmdir(path)

    def _refresh_demo_data(self):
        if self.demo_mode:
            self._delete_demo_data(self.backup_dir)
            self._create_demo_data(self.backup_dir)

    def _create_demo_data(self, test_folder_pwd):
        try:
            os.mkdir(test_folder_pwd)
            os.chdir(test_folder_pwd)
            with open('test_backup_sql.sql.gz', 'wb') as f:
                f.seek(20048575)
                f.write(b'\0')
                f.close()
            with open('test_backup_json.json', 'wb') as f:
                f.seek(1048575)
                f.write(b'\0')
                f.close()
        except Exception as e:
            _log.critical(str(e))

    def _delete_demo_data(self, test_folder_pwd):
        if os.path.exists(test_folder_pwd):
            shutil.rmtree(test_folder_pwd, ignore_errors=True)