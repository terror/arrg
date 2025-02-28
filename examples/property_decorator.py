from arrg import app, argument


@app
class Arguments:
  @property
  def count(self) -> int:
    return argument('--count', type=int, default=1)

  def double_count(self):
    return self.count * 2

  def triple_count(self):
    return self.count * 3

  def run(self):
    print(self.count)
    print(self.double_count())
    print(self.triple_count())


if __name__ == '__main__':
  Arguments.from_args().run()
