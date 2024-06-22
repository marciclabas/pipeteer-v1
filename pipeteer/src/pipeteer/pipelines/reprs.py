from types import UnionType
from .pipeline import Pipeline

def indent(s: str, n: int = 1):
  return '\n'.join(' ' * n + line for line in s.splitlines())

def name(type):
  if isinstance(type, UnionType):
    return 'Union'
  return getattr(type, '__name__', str(type))

def str_types(pipeline: Pipeline):
  types = name(pipeline.Tin)
  if pipeline.Tout:
    types += f' -> {name(pipeline.Tout)}' # type: ignore
  return types