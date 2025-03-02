import typing as t

from .constants import SUBCOMMAND_MARKER


def is_subcommand_type(field_type: t.Type) -> bool:
  if hasattr(field_type, SUBCOMMAND_MARKER):
    return True

  origin = t.get_origin(field_type)

  if origin is t.Union:
    args = t.get_args(field_type)

    for arg in args:
      if arg is not type(None) and hasattr(arg, SUBCOMMAND_MARKER):
        return True

  return False


def get_subcommand_type(field_type: t.Type) -> t.Type:
  if hasattr(field_type, SUBCOMMAND_MARKER):
    return field_type

  origin = t.get_origin(field_type)

  if origin is t.Union:
    args = t.get_args(field_type)

    for arg in args:
      if arg is not type(None) and hasattr(arg, SUBCOMMAND_MARKER):
        return arg

  return field_type
