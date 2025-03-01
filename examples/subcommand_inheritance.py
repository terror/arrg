import sys

from arrg import app, argument, subcommand


@subcommand
class BaseCommand:
  verbose: bool = argument('-v', '--verbose', help='Enable verbose output')
  quiet: bool = argument('-q', '--quiet', help='Suppress output')

  def get_verbosity(self):
    if self.quiet:
      return 0
    elif self.verbose:
      return 2
    return 1


@subcommand
class Push(BaseCommand):
  force: bool = argument('-f', '--force', help='Force push')

  def run(self):
    print('Push command executed')
    print(f'Force: {self.force}')
    print(f'Verbose: {self.verbose}')
    print(f'Quiet: {self.quiet}')


@subcommand
class Status(BaseCommand):
  all: bool = argument('-a', '--all', help='Show all statuses')

  def run(self):
    print('Status command executed')
    print(f'Verbose: {self.verbose}')
    print(f'Quiet: {self.quiet}')
    print(f'All: {self.all}')


@subcommand
class Remote(BaseCommand):
  push: Push
  name: str = argument('--name', default='origin')


@app
class Git:
  status: Status
  remote: Remote


if __name__ == '__main__':
  print(f'Command line args: {sys.argv[1:]}')

  # Test with explicit arguments for clarity
  try:
    # Test basic inheritance
    result = Git.from_iter(['status', '-a', '-v'])
    print('=== Status command ===')
    if result.status:
      print(f'Verbose: {result.status.verbose}')
      print(f'All: {result.status.all}')
      print(f'Verbosity level: {result.status.get_verbosity()}')
      result.status.run()

    # Test nested subcommands with inheritance
    result = Git.from_iter(['remote', '-v', '--name', 'upstream'])
    print('\n=== Remote command ===')
    if result.remote:
      print(f'Verbose: {result.remote.verbose}')
      print(f'Name: {result.remote.name}')
      print(f'Verbosity level: {result.remote.get_verbosity()}')
      print(f'Push subcommand exists: {result.remote.push is not None}')

    # Test nested subcommand
    result = Git.from_iter(['remote', 'push', '-f'])
    print('\n=== Remote Push command ===')
    if result.remote and result.remote.push:
      print(f'Force: {result.remote.push.force}')
      print(f'Verbose: {result.remote.push.verbose}')
      result.remote.push.run()
  except Exception as e:
    import traceback

    print(f'Error occurred: {e}')
    traceback.print_exc()
