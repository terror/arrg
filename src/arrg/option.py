from dataclasses import Field, field
from typing import Any, Optional, Union


def option(
  short: Optional[Union[str, bool]] = None, long: Optional[Union[str, bool]] = None, **kwargs: Any
) -> Field:
  return field(
    metadata={
      'custom': {
        'short': short,
        'long': long,
      },
      'supported': kwargs,
    }
  )
