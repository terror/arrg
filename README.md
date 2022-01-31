## arrg

<div align='right'>
 <img width='10%' src='https://oldschool.runescape.wiki/images/Arrg.png?2e0cb'/>
</div>

**arrg** is a Python library for building better command-line applications.
Heavily inspired by the Rust crate
[`structopt`](https://github.com/TeXitoi/structopt).

### Installation

Simply install the package via the Python package manager `pip`.

```bash
$ pip install arrg
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
