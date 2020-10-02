import re
from collections import defaultdict

from termcolor import colored

from utils import get_float, now_time

from .worker import Worker


class LocalDiskWorker(Worker):
    def __init__(self, context, cmd_dict, host='localhost', poll_delay=8, timeout=60):
        worker_type = 'local-disk'
        super().__init__(context, worker_type, host=host, poll_delay=poll_delay, timeout=timeout)
        self.set_cmd_line(cmd_dict)

    def process_result_dict(self, result_dict):
        # disk
        template = colored("{:<12}", 'green') + " \033[90m{:>6} {:>6}\033[0m"
        res = colored('{:<12} {:>6} {:>6}'.format('Filesystem', 'Used', 'Avail'), 'white')
        disks = []
        for line in result_dict['DISK'].split('\n'):
            blocks = list(filter(None, line.split(' ')))
            if len(blocks) <= 3 or len(blocks[-1]) < 3:
                continue
            disks.append(template.format(blocks[-1], blocks[-4], blocks[-3]))
        disk_info = '\n'.join([res] + sorted(disks))

        # notification
        notification_info = result_dict['NOTIFICATION']

        self.context.update_disk_status(disk_info)
        self.context.update_notification(notification_info)
        return disk_info, notification_info

    def on_error(self, msg):
        self.context.update_disk_status(msg, is_success=False)
        # self.context.update_notification()
