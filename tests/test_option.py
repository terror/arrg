import pytest

from arrg import app, option


def test_positional():
  @app
  class Arguments:
    input: str

  assert Arguments.from_iter(['test']).input == 'test'


def test_long_bool():
  @app
  class Arguments:
    input: str = option(long=True)

  assert Arguments.from_iter(['--input', 'test']).input == 'test'


def test_long_str():
  @app
  class Arguments:
    input: str = option(long='long_input')

  assert Arguments.from_iter(['--long_input', 'test']).input == 'test'


def test_short_bool():
  @app
  class Arguments:
    input: str = option(short=True)

  assert Arguments.from_iter(['-i', 'test']).input == 'test'


def test_short_str():
  @app
  class Arguments:
    input: str = option(short='i')

  assert Arguments.from_iter(['-i', 'test']).input == 'test'
