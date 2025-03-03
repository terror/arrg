from arrg import app, argument, subcommand


@subcommand
class C:
  c: str = argument('--c')


@app
class B:
  b: str = argument('--b')
  c: C


@app
class A(B):
  a: str = argument('--a')


if __name__ == '__main__':
  arguments = A.from_args()
  print(arguments.a + arguments.b + arguments.c.c)
