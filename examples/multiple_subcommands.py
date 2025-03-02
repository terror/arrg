from functools import reduce

from arrg import app, argument, subcommand


@subcommand(description='Add numbers together')
class Add:
  numbers: list[float] = argument(help='Numbers to add together')

  def run(self):
    return sum(self.numbers)


@subcommand(description='Multiply numbers together')
class Multiply:
  numbers: list[float] = argument(help='Numbers to multiply together')

  def run(self):
    return reduce(lambda x, y: x * y, self.numbers, 1)


@app(description='A calculator that can add and multiply numbers')
class Calculator:
  add: Add
  multiply: Multiply
  verbose: bool = argument('-v', help='Show calculation steps')

  def run(self):
    if self.add:
      result = self.add.run()

      if self.verbose:
        print(f"Adding: {' + '.join(map(str, self.add.numbers))} = {result}")
      else:
        print(result)

    if self.multiply:
      result = self.multiply.run()

      if self.verbose:
        print(f"Multiplying: {' × '.join(map(str, self.multiply.numbers))} = {result}")
      else:
        print(result)


if __name__ == '__main__':
  Calculator.from_args().run()
