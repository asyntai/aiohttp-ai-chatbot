import json

import pytest
from aiohttp import web

from aiohttp_ai_chatbot import DEFAULT_SKIP_PATHS, asyntai_middleware, setup
from aiohttp_ai_chatbot.middleware import insert_snippet, path_is_skipped

WIDGET = 'asyntai_ab12cd34'
PAGE = '<!doctype html><html><head><title>Home</title></head><body><h1>Hello</h1></body></html>'
# The hidden config element: exactly one per inserted widget.
MARKER = 'class="asyntai-widget-config"'


def html(text=PAGE, status=200, **kwargs):
    async def handler(request):
        return web.Response(text=text, content_type='text/html', status=status, **kwargs)
    return handler


def make_app(*routes, **options):
    options.setdefault('widget_id', WIDGET)
    app = web.Application(middlewares=[asyntai_middleware(**options)])
    for method, path, handler in routes:
        if method == 'GET':
            app.router.add_get(path, handler)  # also answers HEAD
        else:
            app.router.add_route(method, path, handler)
    return app


async def get_text(client, path, method='GET'):
    response = await client.request(method, path)
    return response, await response.text()


# ---------------------------------------------------------------- pages

async def test_html_page_gets_widget_once_before_body_close(aiohttp_client):
    client = await aiohttp_client(make_app(('GET', '/', html())))
    response, text = await get_text(client, '/')

    assert response.status == 200
    assert text.count(MARKER) == 1
    assert f'data-asyntai-widget="{WIDGET}"' in text
    assert text.index(MARKER) < text.rindex('</body>')
    assert text.endswith('</body></html>')
    assert int(response.headers['Content-Length']) == len(text.encode('utf-8'))


async def test_upper_case_body_tag_and_last_tag_used(aiohttp_client):
    page = '<html><body><code></body></code><p>x</p></BODY></html>'
    client = await aiohttp_client(make_app(('GET', '/', html(page))))
    _, text = await get_text(client, '/')

    assert text.count(MARKER) == 1
    assert text.index(MARKER) > text.index('<p>x</p>')
    assert text.endswith('</BODY></html>')


async def test_page_without_body_close_is_untouched(aiohttp_client):
    client = await aiohttp_client(make_app(('GET', '/', html('<p>fragment</p>'))))
    _, text = await get_text(client, '/')
    assert text == '<p>fragment</p>'


async def test_page_that_already_has_widget_is_not_doubled(aiohttp_client):
    own = PAGE.replace('</body>', '<script src="x.js" data-asyntai-id="asyntai_zz99yy88"></script></body>')
    client = await aiohttp_client(make_app(('GET', '/', html(own))))
    _, text = await get_text(client, '/')
    assert text == own
    assert MARKER not in text


async def test_charset_is_kept(aiohttp_client):
    page = '<html><body><p>Příliš žluťoučký kůň</p></body></html>'

    async def handler(request):
        return web.Response(body=page.encode('cp1250'), content_type='text/html', charset='cp1250')

    client = await aiohttp_client(make_app(('GET', '/', handler)))
    response = await client.get('/')
    raw = await response.read()

    assert 'charset=cp1250' in response.headers['Content-Type']
    decoded = raw.decode('cp1250')
    assert 'Příliš žluťoučký kůň' in decoded
    assert decoded.count(MARKER) == 1
    assert int(response.headers['Content-Length']) == len(raw)


async def test_compressed_response_gets_widget_and_stays_compressed(aiohttp_client):
    async def handler(request):
        response = web.Response(text=PAGE * 50, content_type='text/html')
        response.enable_compression()
        return response

    client = await aiohttp_client(make_app(('GET', '/', handler)))
    response = await client.get('/', headers={'Accept-Encoding': 'gzip'})
    text = await response.text()

    assert response.headers.get('Content-Encoding') == 'gzip'
    assert text.count(MARKER) == 1


async def test_pre_compressed_body_is_untouched(aiohttp_client):
    import gzip
    body = gzip.compress(PAGE.encode())

    async def handler(request):
        return web.Response(body=body, content_type='text/html', headers={'Content-Encoding': 'gzip'})

    client = await aiohttp_client(make_app(('GET', '/', handler)))
    response = await client.get('/')
    text = await response.text()  # the client unpacks the gzip body
    assert MARKER not in text
    assert text == PAGE


# ---------------------------------------------------------------- left alone

async def test_json_is_untouched(aiohttp_client):
    async def handler(request):
        return web.json_response({'body': '</body>'})

    client = await aiohttp_client(make_app(('GET', '/api', handler)))
    response = await client.get('/api')
    assert await response.json() == {'body': '</body>'}


async def test_plain_text_is_untouched(aiohttp_client):
    async def handler(request):
        return web.Response(text='</body>')

    client = await aiohttp_client(make_app(('GET', '/t', handler)))
    _, text = await get_text(client, '/t')
    assert text == '</body>'


async def test_error_status_is_untouched(aiohttp_client):
    client = await aiohttp_client(make_app(('GET', '/', html(status=500))))
    _, text = await get_text(client, '/')
    assert text == PAGE


async def test_raised_not_found_and_redirect_pass(aiohttp_client):
    async def redirect(request):
        raise web.HTTPFound('/')

    client = await aiohttp_client(make_app(('GET', '/', html()), ('GET', '/old', redirect)))

    response = await client.get('/missing')
    assert response.status == 404
    assert MARKER not in await response.text()

    response = await client.get('/old', allow_redirects=False)
    assert response.status == 302
    assert response.headers['Location'] == '/'


async def test_head_request_is_untouched(aiohttp_client):
    client = await aiohttp_client(make_app(('GET', '/', html())))
    response = await client.head('/')
    assert response.status == 200
    assert int(response.headers['Content-Length']) == len(PAGE.encode())


async def test_static_html_file_is_untouched(aiohttp_client, tmp_path):
    (tmp_path / 'page.html').write_text(PAGE, encoding='utf-8')
    app = make_app()
    app.router.add_static('/static', tmp_path)
    client = await aiohttp_client(app)

    _, text = await get_text(client, '/static/page.html')
    assert text == PAGE


async def test_prepared_stream_is_untouched(aiohttp_client):
    async def handler(request):
        response = web.StreamResponse(headers={'Content-Type': 'text/html'})
        await response.prepare(request)
        await response.write(PAGE.encode())
        await response.write_eof()
        return response

    client = await aiohttp_client(make_app(('GET', '/stream', handler)))
    _, text = await get_text(client, '/stream')
    assert text == PAGE


async def test_websocket_still_works(aiohttp_client):
    async def handler(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        async for message in ws:
            await ws.send_str('echo:' + message.data)
            await ws.close()
        return ws

    client = await aiohttp_client(make_app(('GET', '/ws', handler)))
    ws = await client.ws_connect('/ws')
    await ws.send_str('hi')
    assert (await ws.receive()).data == 'echo:hi'
    await ws.close()


# ---------------------------------------------------------------- skip paths

def test_path_rules():
    assert path_is_skipped('/admin', DEFAULT_SKIP_PATHS)
    assert path_is_skipped('/admin/users', DEFAULT_SKIP_PATHS)
    assert not path_is_skipped('/administrator', DEFAULT_SKIP_PATHS)
    assert not path_is_skipped('/', DEFAULT_SKIP_PATHS)
    assert path_is_skipped('/login', ('/login',))
    assert not path_is_skipped('/login/x', ('/login',))


async def test_skip_paths(aiohttp_client):
    client = await aiohttp_client(make_app(
        ('GET', '/admin', html()), ('GET', '/admin/x', html()),
        ('GET', '/administrator', html()), ('GET', '/login', html()),
        skip_paths=['/admin*', '/login'],
    ))
    assert MARKER not in (await get_text(client, '/admin'))[1]
    assert MARKER not in (await get_text(client, '/admin/x'))[1]
    assert MARKER not in (await get_text(client, '/login'))[1]
    assert MARKER in (await get_text(client, '/administrator'))[1]


async def test_empty_skip_paths_puts_widget_everywhere(aiohttp_client):
    client = await aiohttp_client(make_app(('GET', '/admin', html()), skip_paths=None))
    assert MARKER in (await get_text(client, '/admin'))[1]


# ---------------------------------------------------------------- settings

async def test_environment_variable_is_read_per_request(aiohttp_client, monkeypatch):
    monkeypatch.delenv('ASYNTAI_WIDGET_ID', raising=False)
    client = await aiohttp_client(make_app(('GET', '/', html()), widget_id=None))

    assert MARKER not in (await get_text(client, '/'))[1]

    monkeypatch.setenv('ASYNTAI_WIDGET_ID', 'asyntai_env12345')
    _, text = await get_text(client, '/')
    assert 'data-asyntai-widget="asyntai_env12345"' in text

    monkeypatch.setenv('ASYNTAI_WIDGET_ID', '')
    assert MARKER not in (await get_text(client, '/'))[1]


async def test_pasted_snippet_keeps_only_the_id(aiohttp_client):
    pasted = '<script async src="https://widget.asyntai.com/static/js/chat-widget.js" data-asyntai-id="asyntai_pasted99"></script>'
    client = await aiohttp_client(make_app(('GET', '/', html()), widget_id=pasted))
    _, text = await get_text(client, '/')
    assert 'data-asyntai-widget="asyntai_pasted99"' in text


@pytest.mark.parametrize('bad', ['', 'nonsense', 'asyntai_<x>', 'asyntai_"onload=', 123])
async def test_bad_widget_id_keeps_chat_off(aiohttp_client, bad):
    client = await aiohttp_client(make_app(('GET', '/', html()), widget_id=bad))
    _, text = await get_text(client, '/')
    assert text == PAGE


async def test_bad_script_url_keeps_chat_off_and_https_url_is_used(aiohttp_client):
    client = await aiohttp_client(make_app(('GET', '/', html()), script_url='javascript:alert(1)'))
    assert MARKER not in (await get_text(client, '/'))[1]

    client = await aiohttp_client(make_app(('GET', '/', html()), script_url='https://cdn.example.com/w.js'))
    _, text = await get_text(client, '/')
    assert 'data-asyntai-src="https://cdn.example.com/w.js"' in text


async def test_setup_adds_the_middleware(aiohttp_client):
    app = web.Application()
    app.router.add_get('/', html())
    setup(app, widget_id=WIDGET)
    assert len(app.middlewares) == 1

    client = await aiohttp_client(app)
    assert (await get_text(client, '/'))[1].count(MARKER) == 1


async def test_jinja2_helper_with_aiohttp_jinja2(aiohttp_client):
    aiohttp_jinja2 = pytest.importorskip('aiohttp_jinja2')
    jinja2 = pytest.importorskip('jinja2')
    from aiohttp_ai_chatbot import asyntai_widget

    app = web.Application()
    env = aiohttp_jinja2.setup(app, loader=jinja2.DictLoader({
        'page.html': '<html><body>{{ asyntai_widget("' + WIDGET + '") }}</body></html>',
    }))
    env.globals['asyntai_widget'] = asyntai_widget
    setup(app, widget_id=WIDGET)

    async def handler(request):
        return aiohttp_jinja2.render_template('page.html', request, {})

    app.router.add_get('/', handler)
    client = await aiohttp_client(app)
    _, text = await get_text(client, '/')

    # The template already carries the widget, so the middleware adds nothing.
    assert text.count(MARKER) == 1
    assert '&lt;' not in text


# ---------------------------------------------------------------- helper

def test_insert_snippet_bad_charset_returns_none():
    assert insert_snippet(b'<body></body>', 'x', 'no-such-charset') is None
    assert insert_snippet('<body>ž</body>'.encode('utf-8'), 'x', 'ascii') is None
