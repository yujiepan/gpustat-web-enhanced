"""
GPUstat-web

author: Jongwook Choi
modified: YujiePan
"""

import asyncio
import json

import aiohttp
import aiohttp_jinja2 as aiojinja2
import ansi2html
import jinja2
from aiohttp import web

import config as cfg
from context import Context
from utils import msg_from_host, now_time
from workers import (LocalDBWorker, LocalDiskWorker, RemoteGPUWorker,
                     RemoteNetworkWorker)

scheme = 'solarized'
ansi2html.style.SCHEME[scheme] = list(ansi2html.style.SCHEME[scheme])
ansi2html.style.SCHEME[scheme][0] = '#555555'
ansi_conv = ansi2html.Ansi2HTMLConverter(dark_bg=True, scheme=scheme)
context = Context()


async def spawn_clients():
    try:
        remote_gpu_workers = [RemoteGPUWorker(context, cmd_dict=cfg.REMOTE_CMD,
                                              host=host, port=cfg.SSH_PORT,
                                              poll_delay=cfg.SSH_INTERVAL,
                                              timeout=cfg.TIMEOUT) for host in cfg.REMOTE_HOST]
        local_disk_workers = [LocalDiskWorker(context, cmd_dict=cfg.LOCAL_CMD,
                                              poll_delay=cfg.LOCAL_INTERVAL)]
        remote_network_workers = [RemoteNetworkWorker(context, cmd_dict=cfg.NETWORK_CMD,
                                                      duration=cfg.NETWORK_DURATION,
                                                      interface=interface,
                                                      host=host, port=cfg.SSH_PORT,
                                                      poll_delay=cfg.NETWORK_INTERVAL,
                                                      timeout=cfg.TIMEOUT) for host, interface in cfg.NETWORK.items()]
        local_db_workers = [LocalDBWorker(context, db_path=cfg.DB_PATH, poll_delay=cfg.DB_INTERVAL)]

        all_workers = remote_gpu_workers + local_disk_workers + remote_network_workers + local_db_workers
        await asyncio.gather(*[worker.run() for worker in all_workers])
    except Exception as ex:
        msg_from_host('APP', 'Workers are down. ' + str(ex), color='red')
        raise


async def html_handler(request, ws_name='ws'):
    '''Renders the html page.'''

    data = dict(
        ansi2html_headers=ansi_conv.produce_headers().replace('\n', ' '),
        http_host=request.host,
        public_ip=cfg.PUBLIC_IP,
        ws_name=ws_name,
        interval=int(cfg.HTML_ASK_INTERVAL * 1000),
    )
    response = aiojinja2.render_template('index.html', request, data)
    response.headers['Content-Language'] = 'en'
    return response


def render_gpustat_body(show_all=False):
    results = {}
    body = ''

    hosts = cfg.REMOTE_HOST
    for host in hosts:
        status = context.get_remote_status(host)
        if not status:
            continue
        body += status
        # print(status)
    results['remote_status'] = ansi_conv.convert(body, full=False)

    disk_usage, disk_usage_time = context.get_disk_status()
    results['disk_status'] = ansi_conv.convert(disk_usage, full=False)
    results['disk_status_time'] = now_time(disk_usage_time)

    results['notification'] = ansi_conv.convert(context.get_notification(), full=False)

    status, status_time, status_comment = context.get_top_users_status()
    results['top_users_status'] = status
    results['top_users_status_time'] = now_time(status_time)
    results['top_users_status_comment'] = ansi_conv.convert(status_comment, full=False)

    status, status_time = context.get_all_network_status()
    results['network_status'] = ansi_conv.convert(status, full=False)
    results['network_status_time'] = now_time(status_time)

    return json.dumps(results, ensure_ascii=False)


async def html_handler_debug(request):
    '''Renders the html page debug.'''

    data = dict(
        ansi2html_headers=ansi_conv.produce_headers().replace('\n', ' '),
        http_host=request.host,
        public_ip=cfg.PUBLIC_IP,
        ws_name='ws',
        interval=int(cfg.HTML_ASK_INTERVAL * 1000),
        result=render_gpustat_body(show_all=True)
    )
    response = aiojinja2.render_template('index.html', request, data)
    response.headers['Content-Language'] = 'en'
    return response


async def websocket_handler(request, show_all=False):
    msg_from_host('INFO', f"Websocket connection from {request.remote} established, host {request.host}")

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async def _handle_websocketmessage(msg):
        if msg.data == 'close':
            await ws.close()
        else:
            body = render_gpustat_body(show_all=show_all)
            await ws.send_str(body)

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.CLOSE:
            break
        elif msg.type == aiohttp.WSMsgType.TEXT:
            await _handle_websocketmessage(msg)
        elif msg.type == aiohttp.WSMsgType.ERROR:
            msg_from_host('ERROR', f"Websocket connection closed with exception {ws.exception()}", color='red')

    msg_from_host('INFO', f"Websocket connection from {request.remote} closed")
    return ws


def create_app():
    app = web.Application()
    app.router.add_get('/', lambda r: html_handler(r))
    app.router.add_get('/all', lambda r: html_handler(r, 'wsall'))
    app.router.add_get('/debug', html_handler_debug)
    app.router.add_get('/ws', lambda r: websocket_handler(r))
    app.router.add_get('/wsall', lambda r: websocket_handler(r, show_all=True))
    # app.add_routes([web.get('/ws', websocket_handler)])

    async def start_background_tasks(app):
        app._tasks = asyncio.create_task(spawn_clients())
        await asyncio.sleep(0.1)
    app.on_startup.append(start_background_tasks)

    async def shutdown_background_tasks(app):
        msg_from_host('INFO', "Terminating the application...", color='yellow')
        app._tasks.cancel()
    app.on_shutdown.append(shutdown_background_tasks)

    aiojinja2.setup(app, loader=jinja2.FileSystemLoader(cfg.TEMPLATE_PATH))
    return app


def main():
    hosts = cfg.REMOTE_HOST
    msg_from_host('INFO', f"Hosts : {hosts}", color='yellow')
    msg_from_host('INFO', f"Cmd   : {cfg.REMOTE_CMD}", color='yellow')
    msg_from_host('INFO', f"Local : {cfg.LOCAL_CMD}", color='yellow')
    app = create_app()
    web.run_app(app, host='0.0.0.0', port=cfg.SERVICE_PORT)


if __name__ == '__main__':
    main()
