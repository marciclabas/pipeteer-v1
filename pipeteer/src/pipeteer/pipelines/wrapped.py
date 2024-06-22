from typing import TypeVar, Generic, Mapping, TypedDict, Any, Callable, Awaitable
from types import UnionType
from dataclasses import dataclass
from abc import abstractmethod
from haskellian import funcs as F, promise as P
from pipeteer.queues import WriteQueue, Queue, ops
from pipeteer import Pipeline, GetQueue, trees

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')
D = TypeVar('D')
Q = TypeVar('Q', bound=Mapping)
Q2 = TypeVar('Q2', bound=Mapping)
T = TypeVar('T')
T2 = TypeVar('T2')
S1 = TypeVar('S1')
S2 = TypeVar('S2')
S3 = TypeVar('S3')
S4 = TypeVar('S4')

class WrappedQueues(TypedDict, Generic[S1, Q]):
  Qwrapped: Queue[S1]
  wrapped: Q

@dataclass
class Wrapped(Pipeline[S1, S2, WrappedQueues[S1, Q], T], Generic[S1, S2, A, B, Q, T]):
  """Wrap a pipeline with pre- and post-processing functions. Both wrapping and wrapped values are stored in a queue"""

  Queues = WrappedQueues

  def __init__(
    self, Tin: type[S1], pipeline: Pipeline[A, B, Q, Any], *,
    Tout: type[S2] | UnionType | None = None
  ):
    self.Tin = Tin
    self.Tout = Tout
    self.pipeline = pipeline

  def __repr__(self):
    from .reprs import str_types, indent
    inner = repr(self.pipeline)
    if len(inner) > 60:
      inner = '\n' + indent(inner) + '\n'
    return f'Wrapped[{str_types(self)}]({inner})'

  @staticmethod
  def of(
    Tin: type[S3], pipeline: Pipeline[C, D, Q2, T2],
    pre: Callable[[S3], Awaitable[C] | C], post: Callable[[S3, D], Awaitable[S4] | S4], *,
    Tout: type[S4] | UnionType | None = None
  ) -> 'Wrapped[S3, S4, C, D, Q2, T2]':
    return FuncWrapped(Tin, pipeline, pre, post, Tout=Tout)

  @abstractmethod
  def pre(self, inp: S1, /) -> Awaitable[A] | A:
    ...
  
  @abstractmethod
  def post(self, inp: S1, out: B, /) -> Awaitable[S2] | S2:
    ...

  def push_queue(self, get_queue: GetQueue, prefix: tuple[str, ...] = (), Qout: WriteQueue[S2] | None = None) -> WriteQueue[S1]:
    Qwrapper = get_queue(prefix + ('wrapper',), self.Tin)
    Qpush = self.pipeline.push_queue(get_queue, prefix + ('wrapped',), Qout)
    return ops.tee(Qwrapper, Qpush.apremap(F.flow(self.pre, P.wait)))
  
  def connect(self, Qout: WriteQueue[S2], get_queue: GetQueue, prefix: tuple[str, ...] = ()) -> WrappedQueues[S1, Q]:
    Qwrapper = get_queue(prefix + ('wrapper',), self.Tin)
    wrapped_Qout = ops.premerge(Qwrapper, Qout, self.post)
    wrapped = self.pipeline.connect(wrapped_Qout, get_queue, prefix + ('wrapped',))
    return WrappedQueues(Qwrapped=Qwrapper, wrapped=wrapped)
  
  def tree(self) -> trees.Tree[Pipeline]:
    return { 'wrapper': self, 'wrapped': self.pipeline.tree() }
  
  def run(self, queues: WrappedQueues[S1, Q], /) -> T:
    return self.pipeline.run(queues['wrapped'])
  

class FuncWrapped(Wrapped[S1, S2, A, B, Q, T], Generic[S1, S2, A, B, Q, T]):
  def __init__(
    self, Tin: type[S1], pipeline: Pipeline[A, B, Q, Any], pre: Callable[[S1], Awaitable[A] | A], post: Callable[[S1, B], Awaitable[S2] | S2], *,
    Tout: type[S2] | UnionType | None = None
  ):
    super().__init__(Tin, pipeline, Tout=Tout)
    self._pre = pre
    self._post = post

  def pre(self, inp: S1, /) -> Awaitable[A] | A:
    return self._pre(inp)
  
  def post(self, inp: S1, out: B, /) -> Awaitable[S2] | S2:
    return self._post(inp, out)