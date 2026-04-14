"""Rally runtime package."""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("rally")
except PackageNotFoundError:
    __version__ = "0.0.dev0"
