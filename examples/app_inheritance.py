from arrg import app, argument, subcommand


@subcommand
class C:
  c: str = argument('--c')


@app
class A:
  a: str = argument('--a')
  c: C


@app
class B(A):
  b: str = argument('--b')


if __name__ == '__main__':
  arguments = B.from_args()
  print(arguments.a + arguments.b + arguments.c.c)
