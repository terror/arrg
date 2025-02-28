from arrg import app, option


@app
class Arguments:
  input: str  # This is a required positional argument.
  count: int = option('--count')  # This is a regular option, defaults to 0.

  @property  # You can use options with `@property` decorators too!
  def multiplier(self) -> int:
    return option('--multiplier', default=1)

  def run(self):
    print(self.input)
    print(self.count * self.multiplier)


if __name__ == '__main__':
  # Try it with `uv run examples/mixed_options.py foo --count 2 --multiplier 10`
  Arguments.from_args().run()
