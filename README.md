## arrg

[![pypi](https://img.shields.io/pypi/v/arrg.svg)](https://pypi.org/project/arrg/)
[![ci](https://github.com/terror/arrg/actions/workflows/ci.yml/badge.svg)](https://github.com/terror/arrg/actions/workflows/ci.yml)
[![downloads](https://img.shields.io/pypi/dm/arrg.svg)](https://pypi.org/project/arrg/)

<div align='left' style='margin: 20px 0 20px 0'>
 <img width='10%' src='https://oldschool.runescape.wiki/images/Arrg.png?2e0cb'/>
</div>

**arrg** is a Python library for building modular command-line applications using
a declarative, class-based approach. It leverages Python type hints and decorators
to simplify the creation of complex command-line interfaces with arguments and
subcommands, while maintaining compatibility with the standard [argparse](https://docs.python.org/3/library/argparse.html)
library.

## Installation

Install the package via the Python package manager [pip](https://pip.pypa.io/en/stable/installation/):

```bash
pip install arrg
```

Alternatively, if you use [uv](https://docs.astral.sh/uv/), add it to your
project:

```bash
uv add arrg
```

## Quick Start

Here's a simple example demonstrating the `app` decorator:

```python
from arrg import app, argument

@app(description="A wonderful command-line interface")
class Arguments:
  input: str = argument()

  def run(self):
    print(self.input)

if __name__ == '__main__':
  Arguments.from_args().run()
```

The `input` field defaults to a positional argument with the name `input` (the
field name). Assuming this code lives in a file called `main.py`, running it
with `python3 main.py hello` will print `hello`.

## Features

### Arguments

In **arrg**, arguments are defined using the `argument` function on class fields
within a class decorated with `@app` or `@subcommand`. This function mirrors the
[add_argument](https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument)
method of a [argparse.ArgumentParser](https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser),
supporting all the familiar parameters like `action`, `nargs`, `type`,
`choices`, `default`, `help`, and more.

Arguments can be `positional` or `optional`:

```python
from arrg import app, argument

@app
class Arguments:
  input: str = argument()
```

The argument `input` here will default as a positional argument with the name
`input` (the field name). Since we're using argparse under the hood, positional
and optional arguments are differentiated by name.

Here is another example defining an argument `input` as an option with a type
and a default value.

```python
from arrg import app, argument

@app
class Arguments:
  input: str = argument('--input', type=str, default='foo')

if __name__ == '__main__':
  arguments = Argument.from_args()
  ...
```

Now you can pass in a `--input` option to your program and have substituted on
your app instance.

### Subcommands

Subcommands enable hierarchical command-line interface structures (e.g. `git add`,
`git commit`). They are defined using the `@subcommand` decorator and integrated
as fields in an `@app` class.

Here is a basic example:

```python
from arrg import subcommand

@subcommand
class Add:
  numbers: list[float] = argument('--numbers', help='Numbers to add together')

  def run(self):
    print(sum(self.numbers))
```

Incorporating them into an existing app by adding them as a field looks like:

```python
from arrg import app, argument, subcommand

@subcommand
class Add:
  numbers: list[float] = argument('--numbers', help='Numbers to add together')

  def run(self):
    print(sum(self.numbers))

@app(description='Simple calculator')
class Calculator:
  add: Add

  def run(self):
    if self.add is not None:
      self.add.run()

if __name__ == '__main__':
  Calculator.from_args().run()
```

Your program will now accept arguments like `add --numbers 1 2 3`.

This example is present in [examples/simple_subcommand.py](https://github.com/terror/arrg/blob/master/examples/simple_subcommand.py),
try it out!

### App inheritance

Apps can inherit from other apps, combining their arguments and subcommands:

```python
@app
class A:
  a: str = argument('--a')

@app
class B(A):
  b: str = argument('--b')

if __name__ == '__main__':
  arguments = B.from_args()
  print(arguments.a + arguments.b)
```

The fields `a` and `b` are accessible from `B`, so passing in `--a foo --b bar`
will yield `foobar`.

Subcommands are also inherited:

```python
@subcommand
class C:
  c: str = argument('--c')

@app
class A:
  a: str = argument('--a')
  c: C

@app
class B(A):
  b: str = argument('--b')

if __name__ == '__main__':
  arguments = B.from_args()
  print(arguments.a + arguments.b + arguments.c.c)
```

Passing in `--a foo --b bar c --c baz` will yield `foobarbaz`.

### Subcommand inheritance

Like apps, subcommands can also inherit from subcommands. This enables a more
modular design for subcommand structures, letting you easily share arguments and
behaviours:

```python
@subcommand
class Base:
  quiet: bool = argument('-q', '--quiet', help='Suppress output')
  verbose: bool = argument('-v', '--verbose', help='Enable verbose output')

@subcommand
class Push(Base):
  force: bool = argument('-f', '--force', help='Force push')

@subcommand
class Status(Base):
  all: bool = argument('-a', '--all', help='Show all statuses')
```

The subcommands `Push` and `Status` inherit the options `--quiet` and `--verbose`
from `Base`.

Nested subcommands can also benefit from inheritance:

```python
@subcommand
class Base:
  quiet: bool = argument('-q', '--quiet', help='Suppress output')
  verbose: bool = argument('-v', '--verbose', help='Enable verbose output')

@subcommand
class Remote(Base):
  name: str = argument('--name', default='origin')

@app
class Git:
  remote: Remote

if __name__ == '__main__':
  print(Git.from_args())
```

Passing in `remote origin --verbose` will yield `Git(remote=Remote(quiet=False, verbose=True, name='origin'))`.

### Smart type conversion

**arrg** automatically converts argument inputs to their annotated types,
reducing the need to specify types manually. Supported types include:

- Primitives: `int`, `float`, `str`, `bool`
- Collections: `list`, `dict`, `tuple`, `set`
- Optional/Union: `Optional[T]`, `Union[T1, T2, ...]`
- Custom Types: `datetime.date`, `datetime.time`, `uuid.UUID`, `pathlib.Path`, `ipaddress.IPv4Address`, `ipaddress.IPv6Address`, `re.Pattern`
- Enums and Literals: Custom `Enum` classes, `Literal['a', 'b']`

For instance, **arrg** will automatically resolve your union types:

```python
@app
class Arguments:
  input: t.Union[int, str] = argument('--input')

  def run(self):
    print(f"{self.input} ({type(self.input).__name__})")

if __name__ == '__main__':
  Arguments.from_args().run()
```

- `--input 42` => `42 (int)`
- `--input hello` => `hello (str)`

It will also handle your list types:

```python
@app
class Arguments:
  numbers: list[int] = argument('--numbers')

if __name__ == '__main__':
  print(Arguments.from_args())
```

Passing in `--numbers 1 2 3` will yield `Arguments(numbers=[1, 2, 3])`.

Of course, you can opt out of these smart type conversion features by specifying
the `type` for arguments yourself.

### Argparse API compatibility

**arrg** aligns with the [argparse](https://docs.python.org/3/library/argparse.html)
API for familiarity and interoperability.

As mentioned before, the `argument` accepts `add_argument` parameters on an
`argparse.ArgumentParser` instance:

```python
@app
class Arguments:
  verbose: bool = argument('--verbose', action='store_true', help='Verbose output')
```

Moreover, the `@app` decorator accepts `argparse.ArgumentParser` parameters:

```python
@app(description='My app', epilog='More info', prog='mycli')
class Arguments:
  pass
```

Running `--help` will display the custom description and epilog.

The `@subcommand` decorator supports similar options:

```python
@subcommand(name='pr', help='Create pull request', description='Detailed PR creation')
class PullRequest:
  title: str = argument('--title')
```

These get added to their respective subparser instances.

### Prior Art

This library is heavily indebted to the rust crate [structopt](https://docs.rs/structopt/latest/structopt/),
for which heavy inspiration was drawn from.
