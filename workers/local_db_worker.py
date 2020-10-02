import re
import time
from collections import Counter, defaultdict

from termcolor import colored

from db import Database
from utils import escape_ansi, get_float, msg_from_host, now_time

from .worker import Worker


class LocalDBWorker(Worker):
    def __init__(self, context, db_path, host='localhost', poll_delay=8, timeout=60):
        worker_type = 'function-db'
        super().__init__(context, worker_type, host=host, poll_delay=poll_delay, timeout=timeout)
        self.db = Database(path=db_path)
        self.set_worker_function(self.read_and_write_db)

    def get_name_usage(self, text):
        name_usage_dict = defaultdict(int)
        pattern = re.compile('\s([a-zA-Z]+)\(([0-9]+)M\)')
        text = escape_ansi(text)
        for name, usage in pattern.findall(text):
            name_usage_dict[name] += int(usage)
        return name_usage_dict

    async def read_and_write_db(self):
        msg_from_host(self.worker_name, 'Database starting to process...', attrs=['bold'])
        result = {}
        start_time = time.time()
        try:
            result['read'] = {'past1hour': await self.db.past_async('-1 hour'),
                              'past24hours': await self.db.past_async('-24 hours'),
                              'past3days': await self.db.past_async('-3 days'),
                              'past7days': await self.db.past_async('-7 days')}
            result['read_error'] = None
        except Exception as ex:
            result['read_error'] = str(ex)
            # raise

        try:
            raw = self.context.get_all_remote_status()
            usages = Counter()
            write_log = []
            for host, info in raw.items():
                if time.time() - info.update_time > 100 or not info.is_success:
                    continue
                write_log.append(host)
                usages += Counter(self.get_name_usage(info.msg))
            to_write = list(usages.items())
            if to_write:
                await self.db.insert_async(to_write)
            result['write'] = ' '.join(write_log) or '(null)'
            result['write_error'] = None
        except Exception as ex:
            result['write_error'] = str(ex)
        result['consumed_time'] = time.time() - start_time
        return result

    def process_result_dict(self, result_dict):
        if result_dict['read_error'] is None:
            msg_from_host(self.worker_name, 'Database successfully read.', attrs=['bold'])
            self.context.update_top_users_status(result_dict['read'])
        if result_dict['write_error'] is None:
            msg_from_host(self.worker_name, f"Database written hosts: {result_dict['write']}", attrs=['bold'])
        if (result_dict['read_error'] is not None) or (result_dict['write_error'] is not None):
            self.on_error(f"DB error: <read> {result_dict['read_error']} <write> {result_dict['write_error']}")
        msg_from_host(self.worker_name, f"Database consumed time: {result_dict['consumed_time']:.2f}s", attrs=['bold'])
        return result_dict['consumed_time']

    def on_error(self, msg):
        self.context.update_top_users_status(msg, is_success=False)
