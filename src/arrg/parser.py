import argparse
import typing as t
from inspect import getmembers, isdatadescriptor

from .option import Option
from .utils import infer_default_value, resolve_type

R = t.TypeVar('R')


class Parser:
  def __init__(self, description: str):
    self._argument_parser = argparse.ArgumentParser(description=description)
    self._optional_argument_field_names = []

  def get_argument_parser(self) -> argparse.ArgumentParser:
    return self._argument_parser

  def add_optional_argument(self, field_name: str, field_type: t.Any, option: Option) -> None:
    kwargs = option._kwargs()

    resolved_type = resolve_type(field_type)

    if 'type' not in kwargs and resolved_type is not bool:
      kwargs['type'] = resolved_type

    if resolved_type is bool and 'type' in kwargs:
      del kwargs['type']

    if resolved_type is bool and 'action' not in kwargs:
      kwargs['action'] = 'store_true'

    if t.get_origin(field_type) is list and 'nargs' not in kwargs:
      kwargs['nargs'] = '+'

    if 'default' not in kwargs:
      kwargs['default'] = infer_default_value(field_type)

    if 'dest' not in kwargs:
      kwargs['dest'] = field_name

    if option.name_or_flags:
      self._argument_parser.add_argument(*option.name_or_flags, **kwargs)
    else:
      self._argument_parser.add_argument(f'--{field_name}', **kwargs)

    self._optional_argument_field_names.append(field_name)

  @staticmethod
  def from_instance(instance: t.Type[R]) -> 'Parser':
    parser = Parser(description=f'{instance.__name__} command-line interface')

    for field_name, field_type in t.get_type_hints(instance).items():
      field = getattr(instance, '__dataclass_fields__').get(field_name)

      if field and 'option' in field.metadata:
        parser.add_optional_argument(field_name, field_type, field.metadata['option'])
      else:
        parser.get_argument_parser().add_argument(field_name, type=resolve_type(field_type))

    for member_name, member_value in getmembers(instance, isdatadescriptor):
      if member_name in getattr(instance, '__dataclass_fields__'):
        continue

      if hasattr(member_value, '__get__'):
        try:
          temp_instance = instance(
            **{field_name: None for field_name in getattr(instance, '__dataclass_fields__')}
          )

          field = getattr(temp_instance, member_name)

          if 'option' not in field.metadata:
            continue

          option = field.metadata['option']

          field_type = (
            option.type
            or t.get_type_hints(
              getattr(getattr(member_value, 'fget'), '__func__', getattr(member_value, 'fget'))
            ).get('return')
            or field.default.__class__
          )

          parser.add_optional_argument(member_name, field_type, option)
        except Exception:
          pass

    return parser
