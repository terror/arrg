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


def test_default_value():
  @app
  class Arguments:
    name: str = option(long=True, default_value='default_name')
    count: int = option(long=True, default_value=42)
    verbose: bool = option(long=True, default_value=False)

  result = Arguments.from_iter([])
  assert result.name == 'default_name'
  assert result.count == 42
  assert not result.verbose

  result = Arguments.from_iter(['--name', 'custom', '--count', '10', '--verbose'])
  assert result.name == 'custom'
  assert result.count == 10
  assert result.verbose
