from arrg import app, argument, subcommand


@subcommand
class Backup:
  path: str = argument()  # positional argument for what to backup
  compress: bool = argument('-c', help='Compress the backup')

  def run(self):
    action = 'Compressing and backing up' if self.compress else 'Backing up'
    print(f'{action} `{self.path}` to remote storage')


@subcommand
class Remote:
  backup: Backup
  verbose: bool = argument('-v', help='Show detailed output')


@subcommand
class List:
  all: bool = argument('-a', help='Show all backups including old ones')

  def run(self):
    scope = 'all' if self.all else 'current'
    print(f'Listing {scope} backups')


@app
class BackupTool:
  remote: Remote
  list: List

  def run(self):
    if self.list is not None:
      self.list.run()
    elif self.remote is not None:
      if self.remote.verbose:
        print('Running backup in verbose mode')

      self.remote.backup.run()


if __name__ == '__main__':
  BackupTool.from_args().run()
