"""Puts the chat widget on every HTML page of an aiohttp site, with no template edit.

The middleware only touches complete web.Response objects that carry an HTML
page with status 200. Everything else passes through untouched: JSON, files
from add_static or web.FileResponse, prepared streams, websockets and
redirects.
"""
from aiohttp import web

from .snippet import MARKER, resolve_widget_id, widget_snippet
from .utils import clean_script_url

BODY_CLOSE = b'</body>'

#: Paths the widget never touches by default. A path that ends in * matches
#: the path itself and everything below it.
DEFAULT_SKIP_PATHS = ('/admin*',)

#: The key under which setup() stores its settings on the application.
APP_KEY = 'aiohttp_ai_chatbot'


def path_is_skipped(path, skip_paths):
    """Answer whether the widget must stay off on this path."""
    for rule in skip_paths:
        if rule.endswith('*'):
            base = rule[:-1].rstrip('/')
            if path == base or path.startswith(base + '/'):
                return True
        elif path == rule:
            return True
    return False


def insert_snippet(body, snippet, charset='utf-8'):
    """Return the page with the snippet before the last </body>, or None.

    None means "leave the page as it is": the page has no closing body tag,
    it already carries the widget, or it is not readable text.
    """
    if MARKER.encode() in body or b'data-asyntai-id' in body:
        return None

    if BODY_CLOSE not in body.lower():
        return None

    try:
        html = body.decode(charset)
        encoded_snippet = snippet.encode(charset)
    except (UnicodeError, LookupError):
        return None

    # Split on the last closing tag, so a page that prints the tag inside an
    # example or a code block is left alone.
    index = html.lower().rfind('</body>')
    if index < 0:
        return None
    return html[:index].encode(charset) + encoded_snippet + html[index:].encode(charset)


def asyntai_middleware(widget_id=None, skip_paths=DEFAULT_SKIP_PATHS, script_url=None):
    """Return an aiohttp middleware that inserts the widget before </body>.

    widget_id      the ID from the Asyntai dashboard; without it, the
                   ASYNTAI_WIDGET_ID environment variable (read on every
                   request, so the ID can change without a code change)
    skip_paths     paths the widget never touches
    script_url     change only if Asyntai support asks

        app = web.Application(middlewares=[asyntai_middleware("asyntai_ab12cd34")])
    """
    skip = tuple(skip_paths or ())

    @web.middleware
    async def asyntai_widget_middleware(request, handler):
        response = await handler(request)

        if request.method == 'HEAD' or path_is_skipped(request.path or '/', skip):
            return response

        if not resolve_widget_id(widget_id) or not clean_script_url(script_url):
            return response

        if _can_carry_widget(response):
            snippet = widget_snippet(widget_id, script_url)
            new_body = insert_snippet(response.body, snippet, response.charset or 'utf-8') if snippet else None
            if new_body is not None:
                # The body setter also sets the new Content-Length.
                response.body = new_body

        return response

    return asyntai_widget_middleware


def setup(app, widget_id=None, skip_paths=DEFAULT_SKIP_PATHS, script_url=None):
    """Add the widget middleware to an application before it starts.

        from aiohttp_ai_chatbot import setup
        setup(app, widget_id="asyntai_ab12cd34")
    """
    middleware = asyntai_middleware(widget_id=widget_id, skip_paths=skip_paths, script_url=script_url)
    app.middlewares.append(middleware)
    return middleware


def _can_carry_widget(response):
    # A FileResponse or a hand-made StreamResponse is not a web.Response,
    # and a prepared response has already left; neither can change.
    if not isinstance(response, web.Response) or response.prepared:
        return False

    if response.status != 200 or response.headers.get('Content-Encoding'):
        return False

    if response.content_type != 'text/html':
        return False

    # A body object (a file, a stream) is sent piece by piece; only plain
    # bytes can be read and changed here.
    return isinstance(response.body, (bytes, bytearray))
