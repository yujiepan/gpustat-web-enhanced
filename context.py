import collections
from collections import defaultdict, namedtuple
from utils import now_time, escape_ansi
from termcolor import colored, cprint
import time


Info = namedtuple('Info', ['is_success', 'msg', 'update_time', 'comment'],
                  defaults=[True, '', 0.0, ''])


class Context(object):
    '''The global context object.'''

    def __init__(self):
        self.data = defaultdict(str)
        self.remote_status = defaultdict(Info)
        self.disk_status = Info()
        self.network_status = defaultdict(Info)

        self.notification = ''
        self.top_users = defaultdict(list)
        self.top_users_time = 0
        self.top_users_comment = ''

        self.db_last_write = Info()
        self.db_last_read = Info()

    def all_data(self):
        pass

    def update_remote_status(self, host, msg_or_comment, is_success=True):
        ''' If is_success, update the msg field. Otherwise update the comment field. '''
        if is_success:
            self.remote_status[host] = Info(is_success=True, update_time=time.time(),
                                            msg=f'{msg_or_comment}\n')
        else:
            msg = self.remote_status[host].msg
            self.remote_status[host] = Info(is_success=False, update_time=time.time(), msg=msg,
                                            comment=colored(f"({host}) ", 'white') + f'{msg_or_comment}')

    def get_remote_status(self, host):
        status = self.remote_status[host]
        if status.is_success:
            return status.msg
        else:
            cached = escape_ansi(status.msg) or '(null)'
            result = f"{status.comment} Cached info:" + (
                '\n' if len(cached.split('\n')) > 1 else '') + f"{cached}"
            return result if result.endswith('\n') else result + '\n'

    def get_all_remote_status(self):
        return self.remote_status

    def update_disk_status(self, msg_or_comment, is_success=True):
        if is_success:
            self.disk_status = Info(is_success=True, update_time=time.time(),
                                    msg=msg_or_comment)
        else:
            msg = self.disk_status.msg
            self.disk_status = Info(is_success=False, update_time=time.time(),
                                    msg=msg, comment=msg_or_comment)

    def get_disk_status(self):
        status = self.disk_status
        if status.is_success:
            return status.msg, status.update_time
        else:
            cached = escape_ansi(status.msg) or '(null)'
            result = f'{status.comment} Cached info: {cached}'
            return result if result.endswith('\n') else result + '\n', status.update_time

    def update_network_status(self, host, msg_or_comment, is_success=True):
        ''' If is_success, update the msg field. Otherwise update the comment field. '''
        if is_success:
            self.network_status[host] = Info(is_success=True, update_time=time.time(),
                                             msg=f'{msg_or_comment}\n')
        else:
            msg = self.network_status[host].msg
            self.network_status[host] = Info(is_success=False, update_time=time.time(), msg=msg,
                                             comment=colored(f"({host}) ", 'white') + f'{msg_or_comment}')

    def get_network_status(self, host):
        status = self.network_status[host]
        if status.is_success:
            return status.msg
        else:
            cached = escape_ansi(status.msg) or '(null)'
            result = f"{status.comment} Cached info:" + (
                '\n' if len(cached.split('\n')) > 1 else '') + f"{cached}"
            return result if result.endswith('\n') else result + '\n'

    def get_all_network_status(self):
        res = colored('{:<4} {:>10} {:>10}\n'.format('Host', 'Upload', 'Download'), 'white')
        max_time = 0
        for host, info in self.network_status.items():
            res += (self.get_network_status(host))
            max_time = max(max_time, info.update_time)
        return res, max_time

    def update_top_users_status(self, top_dict_or_comment, is_success=True):
        if is_success:
            for topK, v in top_dict_or_comment.items():
                self.top_users[topK] = v
            self.top_users_time = time.time()
            self.top_users_comment = ''
        else:
            self.top_users_comment = top_dict_or_comment

    def get_top_users_status(self):
        top_users = {}
        for k, v_list in self.top_users.items():
            top_users[k] = sorted(v_list, key=lambda info: info[1], reverse=True)
        return top_users, self.top_users_time, self.top_users_comment

    def update_notification(self, msg):
        self.notification = msg

    def get_notification(self):
        return self.notification
