import re

from utils import get_float, now_time, colored

from .worker import Worker


class RemoteNetworkWorker(Worker):
    def __init__(self, context, cmd_dict, duration, interface, host='db1', port=22, poll_delay=8, timeout=60):
        worker_type = 'remote-network'
        super().__init__(context, worker_type, host=host, poll_delay=poll_delay, timeout=timeout)
        self.set_cmd_line({'NETWORK': cmd_dict['NETWORK'].format(em=interface, t=duration)})
        self.port = port
        self.on_error(colored('Checking...', color='yellow'))

    def process_result_dict(self, result_dict):
        download, upload = result_dict['NETWORK'].strip().split(' ')
        # kB/s --> Mb/s
        download = float(download.strip()) / 1024 * 8
        upload = float(upload.strip()) / 1024 * 8
        
        template = colored("{:<4}", 'green') + " \033[90m{:>6}Mb/s {:>6}Mb/s\033[0m"
        res = template.format(self.host, f'{upload:.1f}', f'{download:.1f}')
        self.context.update_network_status(self.host, res)

    def on_error(self, msg):
        self.context.update_network_status(self.host, msg, is_success=False)
