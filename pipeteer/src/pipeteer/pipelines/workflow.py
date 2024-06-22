from typing import TypeVar, Generic, Mapping, Union
from abc import abstractmethod
from pipeteer.queues import WriteQueue, ops
from pipeteer import Pipeline, GetQueue, trees

A = TypeVar('A')
B = TypeVar('B')
Q = TypeVar('Q', bound=Mapping)
P = TypeVar('P', bound=Mapping[str, Pipeline])
T = TypeVar('T')

class Workflow(Pipeline[A, B, Q, T], Generic[A, B, P, Q, T]):
  """State-machine-like composition of pipelines"""

  def __init__(self, pipelines: P, *, Tin: type[A] | None = None, Tout: type[B] | None = None):
    self.Tin = Tin or Union[*(pipe.Tin for pipe in pipelines.values())] # type: ignore
    self.Tout = Tout
    self.pipelines = pipelines

  def __repr__(self):
    from .reprs import str_types, indent
    inner = '\n'.join(f'{id}: {repr(pipe)},' for id, pipe in self.pipelines.items())
    return '\n'.join([
      f'Workflow[{str_types(self)}](',
        indent(inner, 2),
      ')',
    ])
  
  @staticmethod
  def dict(pipelines: Mapping[str, Pipeline]) -> 'DictWorkflow[A, B, Q, T]':
    return DictWorkflow(pipelines)
  
  def push_queue(self, get_queue: GetQueue, prefix: tuple[str, ...] = (), Qout: WriteQueue[B] | None = None) -> WriteQueue[A]:
    outputs = [(pipe.push_queue(get_queue, prefix + (id,)), pipe.Tin) for id, pipe in self.pipelines.items()]
    return ops.prejoin(outputs, fallback=Qout)
  
  def connect(self, Qout: WriteQueue[B], get_queue: GetQueue, prefix: tuple[str, ...] = ()) -> Q:
    Qpush = self.push_queue(get_queue, prefix, Qout)
    return {id: pipe.connect(Qpush, get_queue, prefix + (id,)) for id, pipe in self.pipelines.items()} # type: ignore
  
  def tree(self) -> trees.Tree[Pipeline]:
    return {id: pipe.tree() for id, pipe in self.pipelines.items()}

  @abstractmethod
  def run(self, queues: Q, /) -> T:
    ...


class DictWorkflow(Workflow[A, B, Mapping[str, Pipeline], Mapping[str, Q], dict[str, T]], Generic[A, B, Q, T]):
  def run(self, queues: Mapping[str, Q], /) -> dict[str, T]:
    return {id: pipe.run(queues[id]) for id, pipe in self.pipelines.items()}