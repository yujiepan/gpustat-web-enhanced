import time
from termcolor import colored, cprint
import re


def now_time(time_stamp=None, simple=False):
    time_fmt = '%m-%d %H:%M:%S' if simple else '%Y-%m-%d %H:%M:%S'
    return time.strftime(time_fmt, time.localtime(time_stamp)) \
        if time_stamp else time.strftime(time_fmt)


def msg_from_host(host, message, **keywords):
    msg = colored(f"{now_time()} [{host}] {message}", **keywords)
    print(msg)
    return msg


def escape_ansi(line):
    ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
    return ansi_escape.sub('', line)


def get_float(x):
    '''Return flaot in GB unit.'''
    if 'G' in x:
        return float(x[:-1])
    elif 'M' in x:
        return float(x[:-1]) / 1024.0
    else:
        return 0.0


if __name__ == "__main__":
    print(now_time())
