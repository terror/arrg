from argparse import ArgumentParser
from dataclasses import dataclass
from .argument import Argument
from .constants import CUSTOM, SUPPORTED

def process(cls, *args, **kwargs):
  parser = ArgumentParser(**kwargs)

  def parse(cls, args=[]):
    for name, field in cls.__dataclass_fields__.items():
      parser.add_argument(
        *Argument(name, field.metadata.get(CUSTOM)).run(),
        **(field.metadata.get(SUPPORTED) or {})
      )
    return vars(parser.parse_args(args))

  @classmethod
  def from_args(cls):
    return cls(**parse(cls))

  @classmethod
  def from_iter(cls, args):
    return cls(**parse(cls, args))

  cls.from_args = from_args
  cls.from_iter = from_iter

  return dataclass(cls)
