"""Adds the Asyntai AI chat assistant to aiohttp sites."""
from .middleware import DEFAULT_SKIP_PATHS, asyntai_middleware, setup
from .snippet import asyntai_widget, widget_snippet

__all__ = ['DEFAULT_SKIP_PATHS', 'asyntai_middleware', 'asyntai_widget', 'setup', 'widget_snippet']
__version__ = '1.0.0'
