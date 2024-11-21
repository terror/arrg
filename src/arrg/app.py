from .process import process


def app(cls=None, *args, **kwargs):
  def wrap(cls):
    return process(cls, *args, **kwargs)

  if cls is None:
    return wrap
  return wrap(cls)
