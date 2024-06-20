from typing_extensions import TypeVar, Generic, Callable, Mapping
from types import UnionType
from dataclasses import dataclass

A = TypeVar('A')
B = TypeVar('B')
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
    pre: Callable[[S1], A], post: Callable[[S1, B], S2]
  ):
    self.Tin = Tin
    self.pipeline = pipeline
    self.pre = pre
    self.post = post

@dataclass
class Workflow(Pipeline[A, B], Generic[A, B]):
  def __init__(self, Tin: type[A], Tout: type[B] | UnionType | None = None, *, pipelines: Mapping[str, Pipeline]):
    
    input_pipelines = [id for id, pipe in pipelines.items() if issubclass(pipe.Tin, Tin)]
    if len(input_pipelines) > 1:
      raise ValueError(f'Workflow has multiple pipelines with input type {Tin}: {input_pipelines}')
    if len(input_pipelines) == 0:
      raise ValueError(f'Workflow has no pipelines with input type {Tin}')
    self.input_pipeline = input_pipelines[0]
    
    self.Tin = Tin
    self.Tout = Tout
    self.pipelines = pipelines

  def __repr__(self):
    out = f'Workflow({self.Tin.__name__},\n'
    for id, pipe in self.pipelines.items():
      out += f'  {id}: {repr(pipe)},\n'
    return out + ')'