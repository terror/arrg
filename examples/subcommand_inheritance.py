from arrg import app, argument, subcommand


@subcommand
class BaseCommand:
  verbose: bool = argument('-v', '--verbose', help='Enable verbose output')
  quiet: bool = argument('-q', '--quiet', help='Suppress output')


@subcommand
class Push(BaseCommand):
  force: bool = argument('-f', '--force', help='Force push')


@subcommand
class Status(BaseCommand):
  all: bool = argument('-a', '--all', help='Show all statuses')


@subcommand
class Remote(BaseCommand):
  push: Push
  name: str = argument('--name', default='origin')


@app
class Git:
  status: Status
  remote: Remote

  def run(self):
    print(self.status)
    print(self.remote)


if __name__ == '__main__':
  Git.from_args().run()
