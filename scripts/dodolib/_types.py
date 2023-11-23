"""
Types for the dodolib library.
"""

from typing import Any, Optional, Union, Callable, Dict
from pathlib import Path

# general types
PathT = Union[str, Path]
OptString = Optional[str]

# doit action related types
ActionT = Union[str, tuple]
TaskFuncT = Callable[[], Dict[str, Any]]
FilterFuncT = Callable[[PathT], bool]
