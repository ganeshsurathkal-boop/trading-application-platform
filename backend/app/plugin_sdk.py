"""
TICKR — Plugin SDK

Stable import surface for indicator and scanner plugin authors.
Plugin code must only import from here — never reach into
app.indicators.* / app.scanners.* internals directly, since those
module paths are free to change between TICKR versions while this
SDK contract stays stable.

Usage in a plugin's plugin.py:

    from plugin_sdk import BaseIndicator

    class MyIndicator(BaseIndicator):
        name = "MY_IND"
        ...
"""
from app.indicators.base import BaseIndicator
from app.scanners.base import BaseScanner

__all__ = ["BaseIndicator", "BaseScanner"]
