import re
import shutil
import subprocess

import pytest

from aiohttp_ai_chatbot import asyntai_widget, widget_snippet


def test_snippet_carries_id_and_script_url():
    html = widget_snippet('asyntai_ab12cd34')
    assert 'data-asyntai-widget="asyntai_ab12cd34"' in html
    assert 'data-asyntai-src="https://widget.asyntai.com/static/js/chat-widget.js"' in html


def test_snippet_is_empty_without_a_good_id(monkeypatch):
    monkeypatch.delenv('ASYNTAI_WIDGET_ID', raising=False)
    assert widget_snippet() == ''
    assert widget_snippet('bad') == ''


def test_snippet_reads_the_environment(monkeypatch):
    monkeypatch.setenv('ASYNTAI_WIDGET_ID', 'asyntai_env12345')
    assert 'asyntai_env12345' in widget_snippet()


def test_template_helper_is_safe_markup():
    markupsafe = pytest.importorskip('markupsafe')
    value = asyntai_widget('asyntai_ab12cd34')
    assert isinstance(value, markupsafe.Markup)
    assert str(markupsafe.escape(value)) == str(value)


def test_jinja_template_renders_the_widget():
    jinja2 = pytest.importorskip('jinja2')
    env = jinja2.Environment(autoescape=True)
    env.globals['asyntai_widget'] = asyntai_widget
    html = env.from_string('<body>{{ asyntai_widget("asyntai_ab12cd34") }}</body>').render()
    assert '<script>' in html
    assert 'data-asyntai-widget="asyntai_ab12cd34"' in html


def test_script_is_valid_javascript(tmp_path):
    node = shutil.which('node')
    if not node:
        pytest.skip('node is not installed')
    script = re.search(r'<script>(.*)</script>', widget_snippet('asyntai_ab12cd34'), re.S).group(1)
    path = tmp_path / 'widget.js'
    path.write_text(script, encoding='utf-8')
    result = subprocess.run([node, '--check', str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
