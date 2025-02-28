## arrg

<div align='right'>
 <img width='10%' src='https://oldschool.runescape.wiki/images/Arrg.png?2e0cb'/>
</div>

**arrg** is a Python library for building modular command-line applications.
Heavily inspired by the Rust crate
[`structopt`](https://github.com/TeXitoi/structopt).

### Installation

Simply install the package via the Python package manager `pip`.

```bash
$ pip install arrg
```

...or if you're more hip, add it to your project with [uv](https://docs.astral.sh/uv/):

```bash
$ uv add arrg
```

### Usage

Below is a very simple example demonstrating the usage of the `app` decorator.

```python
from arrg import app

@app
class Arguments:
  input: str

  def run(self):
    print(self.input)

if __name__ == '__main__':
  Arguments.from_args().run()
```

### Prior Art

This library is heavily indebted to the rust crate [structopt](https://docs.rs/structopt/latest/structopt/),
for which heavy inspiration was drawn from.
