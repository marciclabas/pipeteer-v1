from typing_extensions import TypeVar, Generic, Callable, Awaitable, Mapping, Union, Any
from types import UnionType
from dataclasses import dataclass

A = TypeVar('A', covariant=True)
B = TypeVar('B', covariant=True)
S1 = TypeVar('S1')
S2 = TypeVar('S2')

@dataclass
class Pipeline(Generic[A, B]):
  Tin: type[A]
  Tout: type[B] | UnionType | None = None

@dataclass
class Wrapped(Pipeline[S1, S2], Generic[S1, S2, A, B]):
  def __init__(
    self, Tin: type[S1], pipeline: Pipeline[A, B],
    pre: Callable[[S1], Awaitable[A] | A], post: Callable[[S1, B], Awaitable[S2] | S2]
  ):
    self.Tin = Tin
    self.pipeline = pipeline
    self.pre = pre
    self.post = post

@dataclass
class Workflow(Pipeline[A, B], Generic[A, B]):
  
  def __init__(self, pipelines: Mapping[str, Pipeline[A, Any]]):
    self.Tin = Union[*(pipe.Tin for pipe in pipelines.values())] # type: ignore
    self.pipelines = pipelines

  def __repr__(self):
    out = f'Workflow({self.Tin.__name__},\n'
    for id, pipe in self.pipelines.items():
      out += f'  {id}: {repr(pipe)},\n'
    return out + ')'