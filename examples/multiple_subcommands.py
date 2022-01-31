from arrg import app, option, subcommand


@subcommand
class Add:
  numbers: list[float] = option(nargs='+', type=float, help='Numbers to add together')

  def run(self):
    return sum(self.numbers)


@subcommand
class Multiply:
  numbers: list[float] = option(nargs='+', type=float, help='Numbers to multiply together')

  def run(self):
    result = 1

    for num in self.numbers:
      result *= num

    return result


@app
class Calculator:
  add: Add
  multiply: Multiply
  verbose: bool = option(short=True, help='Show calculation steps')

  def run(self):
    if self.add is not None:
      result = self.add.run()
      if self.verbose:
        print(f"Adding: {' + '.join(map(str, self.add.numbers))} = {result}")
      else:
        print(result)
    elif self.multiply is not None:
      result = self.multiply.run()
      if self.verbose:
        print(f"Multiplying: {' × '.join(map(str, self.multiply.numbers))} = {result}")
      else:
        print(result)


if __name__ == '__main__':
  Calculator.from_args().run()
