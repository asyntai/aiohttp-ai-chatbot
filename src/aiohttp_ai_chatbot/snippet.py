"""The HTML that loads the chat widget, for the middleware and for templates."""
import os
from html import escape

from .utils import clean_script_url, clean_widget_id

#: Text that only this package writes. The middleware looks for it, so the
#: widget is never added twice.
MARKER = 'asyntai-widget-config'

_TEMPLATE = (
    '<div class="' + MARKER + '" data-asyntai-widget="__WIDGET_ID__" '
    'data-asyntai-src="__SCRIPT_URL__" style="display: none"></div>\n'
    '<script>\n'
    '    // Loads the Asyntai chat widget after the page has finished loading,\n'
    '    // so the site draws first and page speed does not change. The two\n'
    '    // values arrive on a data attribute, so nothing is ever written into\n'
    '    // the script itself.\n'
    '    (function () {\n'
    "        var config = document.querySelector('." + MARKER + "');\n"
    '        if (!config) { return; }\n'
    '\n'
    "        var widgetId = config.getAttribute('data-asyntai-widget') || '';\n"
    "        var scriptUrl = config.getAttribute('data-asyntai-src') || '';\n"
    "        if (!widgetId || scriptUrl.indexOf('https://') !== 0) { return; }\n"
    '\n'
    '        var load = function () {\n'
    "            if (document.querySelector('script[data-asyntai-id]')) { return; }\n"
    '\n'
    "            var script = document.createElement('script');\n"
    '            script.src = scriptUrl;\n'
    '            script.async = true;\n'
    "            script.setAttribute('data-asyntai-id', widgetId);\n"
    '            document.head.appendChild(script);\n'
    '        };\n'
    '\n'
    "        if (document.readyState === 'complete') {\n"
    '            load();\n'
    '        } else {\n'
    "            window.addEventListener('load', load);\n"
    '        }\n'
    '    }());\n'
    '</script>\n'
)


def resolve_widget_id(widget_id=None):
    """The given ID, or the ASYNTAI_WIDGET_ID environment variable."""
    if widget_id is None:
        widget_id = os.environ.get('ASYNTAI_WIDGET_ID', '')
    return clean_widget_id(widget_id)


def widget_snippet(widget_id=None, script_url=None):
    """Return the widget HTML, or an empty string when the chat must stay off.

    Without a widget_id, the ASYNTAI_WIDGET_ID environment variable is used.
    """
    clean_id = resolve_widget_id(widget_id)
    clean_url = clean_script_url(script_url)
    if not clean_id or not clean_url:
        return ''

    return (_TEMPLATE
            .replace('__WIDGET_ID__', escape(clean_id, quote=True))
            .replace('__SCRIPT_URL__', escape(clean_url, quote=True)))


def asyntai_widget(widget_id=None, script_url=None):
    """Template helper: the same HTML, marked safe for Jinja2.

    With aiohttp-jinja2, register it once, then write {{ asyntai_widget() }}
    before </body>:

        aiohttp_jinja2.get_env(app).globals['asyntai_widget'] = asyntai_widget
    """
    html = widget_snippet(widget_id, script_url)
    try:
        from markupsafe import Markup
    except ImportError:  # Jinja2 is optional.
        return html
    return Markup(html)
