from typing import Dict, List


class Argument:
  def __init__(self, name: str, parameters: Dict[str, str] | None) -> None:
    self.name = name
    self.parameters = parameters

  def run(self) -> List[str]:
    if not self.parameters:
      return [f'{self.name}']

    return [
      f'--{self.name}',
      *list(
        filter(
          lambda output: output is not None,
          map(lambda pair: getattr(self, f'_{pair[0]}')(pair[1]), self.parameters.items()),
        )
      ),
    ]

  def _short(self, value: str | bool | None) -> str | None:
    if isinstance(value, bool):
      return f'-{self.name[0]}'
    if isinstance(value, str):
      return f'-{value}'
    return None

  def _long(self, value: str | None) -> str | None:
    if isinstance(value, str):
      return f'--{value}'
    return None
