from arrg import app, option, subcommand


@subcommand
class Backup:
  path: str  # positional argument for what to backup
  compress: bool = option(short=True, help='Compress the backup')

  def run(self):
    action = 'Compressing and backing up' if self.compress else 'Backing up'
    print(f'{action} {self.path} to remote storage')


@subcommand
class Remote:
  backup: Backup
  verbose: bool = option(short=True, help='Show detailed output')


@subcommand
class List:
  all: bool = option(short=True, help='Show all backups including old ones')

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
