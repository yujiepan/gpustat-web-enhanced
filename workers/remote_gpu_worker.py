import re

from termcolor import colored

from utils import get_float, now_time, escape_ansi

from .worker import Worker


class RemoteGPUWorker(Worker):
    def __init__(self, context, cmd_dict, host='db1', port=22, poll_delay=8, timeout=60):
        worker_type = 'remote-gpu'
        super().__init__(context, worker_type, host=host, poll_delay=poll_delay, timeout=timeout)
        self.set_cmd_line(cmd_dict)
        self.port = port
        self.on_error(colored('Connecting...', color='red'))

    def process_result_dict(self, result_dict):
        # print(result_dict['CPU_NEW'])
        # CPU
        cpu_idle = result_dict['CPU_NEW'].strip().split(' ')[-1]
        cpu_percent = 1.0 - float(cpu_idle) / 100
        cpu_raw = '{:.1f}%'.format(cpu_percent * 100)
        if cpu_percent > 0.85:
            cpu_info = '\033[;30mCPU\033[0m \033[1;35m{}\033[0m'.format(cpu_raw.ljust(6))
        else:
            cpu_info = '\033[;30mCPU\033[0m \033[;39m{}\033[0m'.format(cpu_raw.ljust(6))

        # Network
        network = result_dict['NETWORK'].split('\n')
        uploads = []
        downloads = []
        for line in network:
            down, up = line.strip().split(' ')
            uploads.append(float(up))
            downloads.append(float(down))
        up = max(uploads) / 1024 * 8
        down = max(downloads) / 1024 * 8
        if down > 200:
            network_info = 'IO↓ ' + colored(f'{down:.1f}Mb/s'.ljust(10), 'magenta', attrs=['bold'])
        else:
            network_info = 'IO↓ ' + f'{down:.1f}Mb/s'.ljust(10)

        # MEM
        mem_result = result_dict['MEM'].split('\n')
        if 'buffers/cache' in mem_result[2]:
            # ubuntu 14
            used_str, free_str = list(filter(None, mem_result[2].split(' ')))[-2:]
            used = get_float(used_str)
            total = used + get_float(free_str)
        else:
            # ubuntu 16
            line = list(filter(None, mem_result[1].split(' ')))
            total = get_float(line[1])
            used = total - get_float(line[-1])
        memory_raw = f'{used:.0f}G/{total:.0f}G'.ljust(12)
        if used / total > 0.80:
            mem_info = '\033[;30mMEM(used)\033[0m \033[1;35m{}\033[0m'.format(memory_raw)
        else:
            mem_info = '\033[;30mMEM(used)\033[0m \033[;39m{}\033[0m'.format(memory_raw)

        # IO busy?
        if cpu_percent > 0.85 or used / total > 0.91 or down > 300:
            io_info = colored(' [busy]', 'cyan', attrs=['bold'])  # '\033[1;96m{}\033[0m'.format('[busy]')
        else:
            io_info = ''

        # CUDA
        def get_cuda_version(s):
            try:
                return re.search('cuda-([0-9]+.[0-9])', s).group(1)
            except Exception:
                return ''
        cuda_installed = "/".join(
            sorted(set(filter(None, map(get_cuda_version, result_dict['CUDA'].split('\n')))),
                   key=float, reverse=True))

        # GPUstat
        gpu_result = result_dict['GPUSTAT'].split('\n')
        time_info = '\033[;30m{}\033[0m'.format(now_time(simple=True))
        title = colored(escape_ansi(gpu_result[0]).split(' ')[0], attrs=['bold'], color='white')
        driver = gpu_result[0].split(' ')[-1]

        gpu_details = []
        for line in gpu_result[1:]:
            # line = line.replace('250 W', '')
            # line_s = line.index('/')
            parts = line.split('|')
            parts[1] = parts[1][:-32] + colored('W ', 'magenta')
            gpu_details.append(f"{parts[0][:8]}{parts[2]}|{parts[0][8:]}{parts[1]}|{'|'.join(parts[3:])}")
            # gpu_details.append('|'.join(parts))

        # final
        # io_info = ''
        gpu_info = f"{title} {io_info}  {cpu_info}  {network_info} {mem_info}{time_info}   {driver}  CUDA: {cuda_installed}\n" + \
            "\n".join(gpu_details)
        # count_info = count_top(results[gpu_at + 2:])
        count_info = None
        gpu_info = gpu_info.replace(',', '')
        # fix
        final_result = gpu_info.replace('GeForce GTX', ''), count_info

        self.context.update_remote_status(self.host, final_result[0])

    def on_error(self, msg):
        self.context.update_remote_status(self.host, msg, is_success=False)
