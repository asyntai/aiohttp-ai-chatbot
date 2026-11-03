# aiohttp-ai-chatbot

Adds the [Asyntai](https://asyntai.com) AI chat assistant to an aiohttp site.
The assistant answers visitor questions from your own content, day and night,
in more than 80 languages.

Free and open source. Works on every Asyntai plan, including the free plan.

- Requires Python 3.9 or newer and aiohttp 3.8 or newer
- Documentation: https://asyntai.com/documentation/integrations/aiohttp/

## Install

```
pip install aiohttp-ai-chatbot
```

```python
from aiohttp import web
from aiohttp_ai_chatbot import setup

app = web.Application()
app.router.add_get("/", index)
setup(app, widget_id="asyntai_ab12cd34")

web.run_app(app)
```

Or pass the middleware yourself:

```python
from aiohttp_ai_chatbot import asyntai_middleware

app = web.Application(middlewares=[asyntai_middleware("asyntai_ab12cd34")])
```

You get the widget ID from the Install page of your
[Asyntai dashboard](https://asyntai.com/dashboard). You can paste the whole
snippet; the package keeps only the ID.

That is all. The chat button appears on every HTML page of the site. JSON,
files, streams, websockets and redirects pass through untouched.

## Options

```python
setup(
    app,
    widget_id="asyntai_ab12cd34",   # without it: the ASYNTAI_WIDGET_ID environment variable
    skip_paths=["/admin*"],         # the default
)
```

- Leave out `widget_id` to read the `ASYNTAI_WIDGET_ID` environment variable.
  It is read on every request, so you can change it without a code change.
  An empty value switches the chat off.
- `skip_paths` lists paths that never get the widget. A path that ends in `*`
  also matches everything below it, so `/admin*` covers `/admin` and
  `/admin/users`, but not `/administrator`.

The middleware changes complete `web.Response` pages with status 200 and the
`text/html` content type. A response that uses `enable_compression()` still
gets the widget, because aiohttp compresses the body after the middleware.
Files from `add_static` or `web.FileResponse` and responses that you prepare
and stream yourself are sent as they are.

## Placing the widget by hand

With aiohttp-jinja2, register the helper once:

```python
import aiohttp_jinja2
from aiohttp_ai_chatbot import asyntai_widget

env = aiohttp_jinja2.setup(app, loader=...)
env.globals["asyntai_widget"] = asyntai_widget
```

Then put it before the closing body tag:

```html
{{ asyntai_widget() }}
</body>
```

`widget_snippet()` returns the same HTML as a plain string. The middleware
never adds a second copy to a page that already has one.

## How it loads

The widget script loads after the page has finished loading, so your page
draws first and page speed does not change.

## License

MIT
