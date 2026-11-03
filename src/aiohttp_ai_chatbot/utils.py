"""Reading and checking the two values the widget needs.

Every decision the package makes about a configured value lives here, so the
tests can run it on its own.
"""
import re

DEFAULT_SCRIPT_URL = 'https://widget.asyntai.com/static/js/chat-widget.js'

#: Shape of a widget identifier from the Asyntai dashboard.
ID_PATTERN = re.compile(r'^asyntai_[A-Za-z0-9]{6,64}$')

#: The identifier inside a pasted snippet.
SNIPPET_PATTERN = re.compile(r'data-asyntai-id\s*=\s*["\']([^"\']+)["\']')

_HTTPS_PATTERN = re.compile(r'^https://[^\s"\'<>]+$', re.IGNORECASE)


def clean_widget_id(raw):
    """Return a usable widget identifier, or an empty string.

    Accepts a bare identifier or the whole snippet from the Asyntai
    dashboard, because people paste the snippet. An empty string means the
    chat stays off, which is how you switch it off again.
    """
    if not isinstance(raw, str):
        return ''

    value = raw.strip()
    if not value:
        return ''

    match = SNIPPET_PATTERN.search(value)
    if match:
        value = match.group(1).strip()

    return value if ID_PATTERN.match(value) else ''


def clean_script_url(raw):
    """Return the script address, or an empty string when the value is bad.

    Only an https address is accepted, so a bad value can never put a
    javascript: URL on every page of the site. No value means the Asyntai
    address.
    """
    if raw is None:
        return DEFAULT_SCRIPT_URL

    if not isinstance(raw, str):
        return ''

    value = raw.strip()
    if not value:
        return DEFAULT_SCRIPT_URL

    return value if _HTTPS_PATTERN.match(value) else ''
