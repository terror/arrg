from dataclasses import field, Field

def option(*args, **kwargs) -> Field:
  return field(metadata=kwargs)
