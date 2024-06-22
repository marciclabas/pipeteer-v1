from typing import TypeVar, Generic, Protocol, Mapping, Sequence, Callable, Awaitable
from types import UnionType
from dataclasses import dataclass
from abc import ABC, abstractmethod
from pipeteer.queues import WriteQueue, ReadQueue, Queue
from pipeteer.trees import Tree

A = TypeVar('A', covariant=True)
B = TypeVar('B', covariant=True)
C = TypeVar('C')
D = TypeVar('D', covariant=True)
Q = TypeVar('Q', bound=Mapping)
T = TypeVar('T')
S1 = TypeVar('S1')
S2 = TypeVar('S2')

class GetQueue(Protocol):
  """Lazy queue accessor. Must return *the same object* given the same parameters."""
  def __call__(self, path: Sequence[str], type: type[T], /) -> Queue[T]:
    ...

@dataclass
class Pipeline(ABC, Generic[A, B, Q, T]):
  """Base class for all pipelines"""
  Tin: type[A]
  Tout: type[B] | UnionType | None

  def __repr__(self):
    return f'Pipeline({self.Tin.__name__} -> {self.Tout and repr(self.Tout) or "???"})'

  @abstractmethod
  def push_queue(self, get_queue: GetQueue, prefix: tuple[str, ...] = (), Qout: WriteQueue[B] | None = None) -> WriteQueue[A]:
    """Queue to push tasks into the pipeline"""
  
  @abstractmethod
  def connect(self, Qout: WriteQueue[B], get_queue: GetQueue, prefix: tuple[str, ...] = ()) -> Q:
    """Tree of nested connected queues (connected internally and with the provided output queue `Qout`)"""

  @abstractmethod
  def observe(self, get_queue: GetQueue, prefix: tuple[str, ...] = ()) -> Tree[ReadQueue]:
    """Tree of all nested read queues"""

  @abstractmethod
  def run(self, queues: Q, /) -> T:
    """Artifacts to run the pipeline"""
