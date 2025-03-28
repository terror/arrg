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
