from dataclasses import field, Field
from typing import Optional, Union, Any

def option(
  short: Optional[Union[str, bool]] = None,
  long: Optional[Union[str, bool]] = None,
  **kwargs: Any
) -> Field:
  return field(
    metadata={
      'custom': {
        'short': short,
        'long': long,
      }, 'supported': kwargs
    }
  )
