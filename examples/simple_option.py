from arrg import app


@app
class Arguments:
  input: str

  def run(self):
    print(self.input)


if __name__ == '__main__':
  # uv run simple_option.py foo
  Arguments.from_args().run()
