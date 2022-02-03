from typing import List

class Argument:
  def __init__(self, name: str, parameters: dict | None) -> None:
    self.name = name
    self.parameters = parameters

  def run(self) -> List[str]:
    if not self.parameters:
      return [f'{self.name}']

    ret = [f'--{self.name}']
    for key, value in self.parameters.items():
      if (output := getattr(self, f'_{key}')(value)):
        ret.append(output)

    return ret

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
