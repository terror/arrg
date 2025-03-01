import argparse
import typing as t


class Argument:
  def __init__(
    self,
    *name_or_flags: str,
    action: t.Optional[t.Union[str, t.Type[argparse.Action]]] = None,
    nargs: t.Optional[t.Union[int, str]] = None,
    const: t.Any = None,
    default: t.Any = None,
    type: t.Optional[t.Callable] = None,
    choices: t.Optional[t.Iterable[t.Any]] = None,
    required: bool = False,
    help: t.Optional[str] = None,
    metavar: t.Optional[t.Union[str, tuple[str, ...]]] = None,
    dest: t.Optional[str] = None,
    version: t.Optional[str] = None,
    **kwargs: t.Any,
  ):
    self.name_or_flags = name_or_flags
    self.action = action
    self.nargs = nargs
    self.const = const
    self.default = default
    self.type = type
    self.choices = choices
    self.required = required
    self.help = help
    self.metavar = metavar
    self.dest = dest
    self.version = version
    self.kwargs = kwargs

  @property
  def positional(self) -> bool:
    return (
      True
      if not self.name_or_flags
      else not any(flag.startswith('-') for flag in self.name_or_flags)
    )

  def resolve_kwargs(self) -> t.Dict[str, t.Any]:
    kwargs = {}

    for attribute, value in vars(self).items():
      if attribute == 'name_or_flags':
        continue

      if attribute == 'kwargs':
        kwargs.update(value)
        continue

      if value is not None:
        kwargs[attribute] = value

    return kwargs
