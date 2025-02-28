import typing as t

from arrg import app, argument


@app
class Arguments:
  input: t.Union[int, str] = argument('--input')

  def run(self):
    print(self.input)


if __name__ == '__main__':
  # `uv run examples/automatic_union_type_conversion.py --value foo` works,
  # and `input` will be a `str`.
  Arguments.from_args().run()
