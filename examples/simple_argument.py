from arrg import app, argument


@app(description='Simple argument example')
class Arguments:
  input: str = argument()

  def run(self):
    print(self.input)


if __name__ == '__main__':
  Arguments.from_args().run()
