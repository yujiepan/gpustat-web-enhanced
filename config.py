from pathlib import Path


REMOTE_HOST = [f'db{i}' for i in list(range(15, 20))]
SSH_PORT = 22
SSH_INTERVAL = 8
TIMEOUT = 80
REMOTE_CMD = {'CPU_NEW': "echo `iostat -c 1 2`",
              'NETWORK': "sar -n DEV 1 2 | grep -E '(Average|平均)+' | grep -vw lo | grep -v rxkB/s | awk '{{print $5, $6}}'",
              'MEM': "free -h",
              'CUDA': "ls /usr/local",
              'GPUSTAT': "gpustat -P --color --gpuname-width 16"}

NOTIFICATION_FILE = './notification.txt'
LOCAL_CMD = {'DISK': 'df -h | grep /D',
             'NOTIFICATION': f'cat {NOTIFICATION_FILE}'}
LOCAL_INTERVAL = 20

NETWORK = {
    'DB15': 'eno1'
}

NETWORK_DURATION = 5
NETWORK_INTERVAL = 20
NETWORK_CMD = {
    'NETWORK': "sar -n DEV 1 {t} | grep -E '(Average|平均)+' | grep -vw lo | grep -v rxkB/s | grep -w {em} | awk '{{print $5, $6}}'"
}

DB_PATH = 'usages.db'
DB_INTERVAL = 60

TEMPLATE_PATH = str(Path(__file__).parent / 'template')
HTML_ASK_INTERVAL = 8
SERVICE_PORT = 30000
PUBLIC_IP = 'localhost:30000'
