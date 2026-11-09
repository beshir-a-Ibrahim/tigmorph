"""tigmorph — a Tigre morphological analyzer built on Raz (1973)."""
__version__ = '2.1.0'
from .analyzer import Analyzer, Analysis  # noqa: F401
from .normalize import Normalizer, normalize_chars  # noqa: F401
