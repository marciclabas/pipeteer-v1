from typing import TypeVar, Generic, Mapping, Union, Any
from abc import abstractmethod
from pipeteer.queues import WriteQueue, ops
from pipeteer import Pipeline, GetQueue, trees

A = TypeVar('A')
B = TypeVar('B')
Q = TypeVar('Q', bound=Mapping)
P = TypeVar('P')
Ps = TypeVar('Ps', bound=Mapping[str, Pipeline])
T = TypeVar('T')

class Workflow(Pipeline[A, B, Q, P, T], Generic[A, B, Q, P, T, Ps]):
  """State-machine-like composition of pipelines"""

  def __init__(self, pipelines: Ps, *, Tin: type[A] | None = None, Tout: type[B] | None = None):
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
  def dict(pipelines: Mapping[str, Pipeline[Any, Any, Any, P, T]]) -> 'DictWorkflow[A, B, Q, P, T]':
    return DictWorkflow(pipelines)
  
  def push_queue(self, get_queue: GetQueue, params: P, *, prefix: tuple[str|int, ...] = ()) -> WriteQueue[A]:
    outputs = [(pipe.push_queue(get_queue, params, prefix=prefix + (id,)), pipe.Tin) for id, pipe in self.pipelines.items()]
    return ops.prejoin(outputs)
  
  def connect(self, Qout: WriteQueue[B], get_queue: GetQueue, params: P, *, prefix: tuple[str|int, ...] = ()) -> Q:
    outputs = [(pipe.push_queue(get_queue, params, prefix=prefix + (id,)), pipe.Tin) for id, pipe in self.pipelines.items()]
    Qpush = ops.prejoin(outputs, fallback=Qout)
    queues = {id: pipe.connect(Qpush, get_queue, params, prefix=prefix + (id,)) for id, pipe in self.pipelines.items()}
    return queues # type: ignore
  
  def tree(self) -> trees.Tree[Pipeline]:
    return {id: pipe.tree() for id, pipe in self.pipelines.items()}

  @abstractmethod
  def run(self, queues: Q, params: P, /) -> T:
    ...


class DictWorkflow(Workflow[A, B, Mapping[str, Q], P, dict[str, T], Mapping[str, Pipeline]], Generic[A, B, Q, P, T]):
  def run(self, queues: Mapping[str, Q], params: P, /) -> dict[str, T]: # type: ignore
    return {id: pipe.run(queues[id], params) for id, pipe in self.pipelines.items()}