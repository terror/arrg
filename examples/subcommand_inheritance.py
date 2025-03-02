from arrg import app, argument, subcommand


@subcommand
class Base:
  quiet: bool = argument('-q', '--quiet', help='Suppress output')
  verbose: bool = argument('-v', '--verbose', help='Enable verbose output')


@subcommand
class Push(Base):
  force: bool = argument('-f', '--force', help='Force push')


@subcommand
class Status(Base):
  all: bool = argument('-a', '--all', help='Show all statuses')


@subcommand
class Remote(Base):
  name: str = argument('--name', default='origin')
  push: Push


@app
class Git:
  remote: Remote
  status: Status

  def run(self):
    if self.status:
      print(self.status)

    if self.remote:
      print(self.remote)


if __name__ == '__main__':
  Git.from_args().run()
