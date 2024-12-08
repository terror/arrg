from arrg import app, option, subcommand


@subcommand
class Add:
  numbers: list[float] = option(nargs='+', type=float, help='Numbers to add together')

  def run(self):
    print(sum(self.numbers))


@app
class Calculator:
  add: Add

  def run(self):
    if self.add is not None:
      self.add.run()


if __name__ == '__main__':
  # uv run simple_subcommand.py add --numbers 1 2 3 4
  Calculator.from_args().run()
