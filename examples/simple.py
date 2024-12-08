from arrg import app


@app
class Arguments:
  input: str

  def run(self):
    print(self.input)


if __name__ == '__main__':
  Arguments.from_args().run()
