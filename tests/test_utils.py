from aiohttp_ai_chatbot.utils import DEFAULT_SCRIPT_URL, clean_script_url, clean_widget_id


def test_bare_id_is_kept():
    assert clean_widget_id('asyntai_ab12cd34') == 'asyntai_ab12cd34'


def test_id_is_trimmed():
    assert clean_widget_id('  asyntai_ab12cd34 \n') == 'asyntai_ab12cd34'


def test_id_comes_out_of_a_pasted_snippet():
    snippet = '<script async src="https://widget.asyntai.com/static/js/chat-widget.js" data-asyntai-id="asyntai_ab12cd34"></script>'
    assert clean_widget_id(snippet) == 'asyntai_ab12cd34'


def test_bad_ids_switch_the_chat_off():
    for raw in ['', '   ', 'hello', 'asyntai_', 'asyntai_ab"><script>', 'asyntai_ab12 cd34', None, 42]:
        assert clean_widget_id(raw) == ''


def test_script_url_defaults_to_asyntai():
    assert clean_script_url(None) == DEFAULT_SCRIPT_URL
    assert clean_script_url('') == DEFAULT_SCRIPT_URL


def test_only_https_script_urls_are_accepted():
    assert clean_script_url('https://example.com/w.js') == 'https://example.com/w.js'
    for raw in ['http://example.com/w.js', 'javascript:alert(1)', 'https://e.com/a b.js', 'https://e.com/"x', 42]:
        assert clean_script_url(raw) == ''
