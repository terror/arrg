from argparse import ArgumentParser
from dataclasses import dataclass

def process(cls, *args, **kwargs):
  @classmethod
  def from_args(cls):
    parser = ArgumentParser(**kwargs)

    for field in cls.__dataclass_fields__:
      parser.add_argument(f'--{field}', **cls.__dataclass_fields__[field].metadata)

    return cls(**vars(parser.parse_args()))

  cls.from_args = from_args

  return dataclass(cls)
