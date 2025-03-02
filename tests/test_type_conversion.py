import typing as t

import pytest

from arrg import app, argument


def test_union_int_str_type_conversion():
  @app
  class Arguments:
    input: t.Union[int, str] = argument()

  result = Arguments.from_iter(['1'])
  assert isinstance(result.input, int)
  assert result.input == 1

  result = Arguments.from_iter(['test'])
  assert isinstance(result.input, str)
  assert result.input == 'test'
