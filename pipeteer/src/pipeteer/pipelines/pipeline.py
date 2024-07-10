from typing import TypeVar, Generic, Protocol, Mapping, Sequence
from types import UnionType
from dataclasses import dataclass
from abc import ABC, abstractmethod
from pipeteer import WriteQueue, ReadQueue, Queue, trees

A = TypeVar('A', covariant=True)
B = TypeVar('B', covariant=True)
C = TypeVar('C')
D = TypeVar('D', covariant=True)
Q = TypeVar('Q')
P = TypeVar('P')
T = TypeVar('T')
S1 = TypeVar('S1')
S2 = TypeVar('S2')

class GetQueue(Protocol):
  """Lazy queue accessor. Must return *the same object* given the same parameters."""
  def __call__(self, path: Sequence[str|int], type: type[T], /) -> Queue[T]:
    ...

@dataclass
class Pipeline(ABC, Generic[A, B, Q, P, T]):
  """Base class for all pipelines"""
  Tin: type[A]
  Tout: type[B] | UnionType | None

  def __repr__(self):
    from .reprs import str_types
    return f'Pipeline[{str_types(self)}]'

  @abstractmethod
  def push_queue(self, get_queue: GetQueue, params: P, /, *, prefix: tuple[str|int, ...] = ()) -> WriteQueue[A]:
    """Queue to push tasks into the pipeline"""

  @abstractmethod
  def connect(self, Qout: WriteQueue[B], get_queue: GetQueue, params: P, /, *, prefix: tuple[str|int, ...] = ()) -> Q:
    """Tree of nested connected queues (connected internally and with the provided output queue `Qout`)"""

  @abstractmethod
  def tree(self) -> trees.Tree['Pipeline']:
    """Tree of nested pipelines"""

  def observe(self, get_queue: GetQueue, prefix: tuple[str|int, ...] = ()) -> trees.Tree[ReadQueue]:
    """Tree of nested read queues"""
    return trees.path_map(self.tree(), lambda path, pipe: get_queue(prefix + tuple(path), pipe.Tin))

  @abstractmethod
  def run(self, queues: Q, params: P, /) -> T:
    """Artifacts to run the pipeline"""