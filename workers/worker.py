import asyncio
import asyncssh
import time
from utils import msg_from_host, cprint
import traceback


class Worker():
    def __init__(self, context, worker_type, host='localhost', poll_delay=8, timeout=60):
        assert worker_type.startswith('remote') or worker_type.startswith('local') \
            or worker_type.startswith('function')
        self.context = context
        self.worker_type = worker_type
        self.host = host
        self.worker_name = f"{host}-{worker_type}"
        self.poll_delay = poll_delay
        self.timeout = timeout

    def process_result_dict(self, result_dict):
        '''Given the result dict, process it and write to `self.context`.'''
        pass

    def on_error(self, msg):
        '''When error occurs, write it to `self.context`. '''
        pass

    def set_worker_function(self, func):
        '''Worker function should return a dict to be fed into `self.process_result_dict`. '''
        self.worker_function = func

    def set_cmd_line(self, cmd_dict):
        self.cmd_dict = cmd_dict
        self.cmd = ' && '.join([f"echo '<START {k}>' && {v} && echo '<END {k}>'"
                                for k, v in cmd_dict.items()])
        return self.cmd

    def get_result_dict(self, raw_result):
        lines = raw_result.split('\n')
        res = {}
        for k in self.cmd_dict.keys():
            idx1 = lines.index(f'<START {k}>')
            idx2 = lines.index(f'<END {k}>')
            res[k] = '\n'.join(lines[idx1 + 1: idx2])
        return res

    async def _loop_body_local(self, cmd, verbose=False):
        while True:
            if verbose:
                msg_from_host(self.worker_name, "Starting...", attrs=['bold'])
            start_time = time.time()
            proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE,
                                                         stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0 and stderr:
                msg = msg_from_host(self.worker_name, f"Error, exitcode={proc.returncode}, stderr={stderr.decode()}", color='red')
                self.on_error(msg)
            else:
                try:
                    if verbose:
                        msg_from_host(self.worker_name, f"OK from {self.worker_type}, ({len(stdout.decode())} bytes)", color='cyan')
                    raw_result = stdout.decode()
                    result_dict = self.get_result_dict(raw_result)
                    self.process_result_dict(result_dict)

                except Exception as ex:
                    msg = msg_from_host(self.worker_name, f"{type(ex).__name__}: {ex}", color='red')
                    self.on_error(msg)

            # wait for a while...
            consumed_time = time.time() - start_time
            await asyncio.sleep(max(0.05, self.poll_delay - consumed_time))

    async def _loop_body_remote(self, cmd, host, port, verbose=False):
        async with asyncssh.connect(host, port=port, known_hosts=None) as conn:
            msg_from_host(self.worker_name, "SSH connection established!", attrs=['bold'])

            while True:
                start_time = time.time()
                result = await asyncio.wait_for(conn.run(cmd), timeout=self.timeout)

                if result.exit_status != 0:
                    msg = msg_from_host(self.worker_name, f"Remote command error, exitcode={result.exit_status}", color='red')
                    self.on_error(msg)
                else:
                    try:
                        if verbose:
                            msg_from_host(self.worker_name, f"OK ({len(result.stdout)} bytes)", color='cyan')
                        raw_results = result.stdout
                        result_dict = self.get_result_dict(raw_results)
                        self.process_result_dict(result_dict)
                    except Exception as ex:
                        msg = msg_from_host(self.worker_name, f"{type(ex).__name__}: {ex}", color='red')
                        self.on_error(msg)

                # wait for a while...
                consumed_time = time.time() - start_time
                await asyncio.sleep(max(0.05, self.poll_delay - consumed_time))

    async def _loop_body_function(self, verbose=False):
        while True:
            await asyncio.sleep(0.2)
            if verbose:
                msg_from_host(self.worker_name, "Starting... ", attrs=['bold'])
            start_time = time.time()
            try:
                result_dict = await self.worker_function()
                self.process_result_dict(result_dict)
            except Exception as ex:
                msg = msg_from_host(self.worker_name, f"{type(ex).__name__}: {ex}", color='red')
                self.on_error(msg)
                # cprint(traceback.format_exc())
            consumed_time = time.time() - start_time
            # print('consumed:', consumed_time)
            await asyncio.sleep(max(0.05, self.poll_delay - consumed_time))

    async def run(self):
        while True:
            try:
                if self.worker_type.startswith('local'):
                    await self._loop_body_local(self.cmd)
                elif self.worker_type.startswith('remote'):
                    await self._loop_body_remote(self.cmd, self.host, self.port)
                elif self.worker_type.startswith('function'):
                    await self._loop_body_function()
                else:
                    raise NotImplementedError('Unknown worker type.')
            except asyncio.CancelledError:
                msg_from_host(self.worker_name, "Closed as being cancelled.", attrs=['bold'])
                break
            except (asyncio.TimeoutError):
                # Timeout Error
                msg = msg_from_host(self.worker_name, f"Timeout after {self.timeout} sec.", color='red')
                self.on_error(msg)
            except (asyncssh.misc.DisconnectError, asyncssh.misc.ChannelOpenError, OSError) as ex:
                # error or disconnected (retry)
                msg = msg_from_host(self.worker_name, f"Disconnected:, {str(ex)}", color='red')
                self.on_error(msg)
            except Exception as ex:
                # A general exception unhandled, throw
                msg = msg_from_host(self.worker_name, f"{self.worker_type} - {type(ex).__name__}: {ex}", color='red')
                self.on_error(msg)
                cprint(traceback.format_exc())
                raise

            # retry upon timeout/disconnected, etc.
            msg = msg_from_host(self.worker_name, f"Disconnected, retrying in {self.poll_delay} sec...", color='yellow')
            # self.on_error(msg)
            await asyncio.sleep(self.poll_delay)
