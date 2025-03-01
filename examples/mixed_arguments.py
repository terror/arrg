from arrg import app, argument


@app
class Arguments:
  input: str = argument()  # This is a required positional argument.

  # This is an optional argument, defaults to 0 (inferred from type).
  count: int = argument('--count')

  @property  # You can use arguments with `@property` decorators too!
  def multiplier(self) -> int:
    return argument('--multiplier', default=1)

  def run(self):
    print(self.input)
    print(self.count * self.multiplier)


if __name__ == '__main__':
  # Try it with `uv run examples/mixed_arguments.py foo --count 2 --multiplier 10`
  Arguments.from_args().run()
