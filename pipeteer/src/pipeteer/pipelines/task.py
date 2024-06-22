from typing import TypeVar, Generic, TypedDict, Any, Callable, Awaitable, Coroutine, ParamSpec
from dataclasses import dataclass
from abc import abstractmethod
from pipeteer.queues import ReadQueue, WriteQueue
from .pipeline import Pipeline, GetQueue, Tree

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')
D = TypeVar('D')
T = TypeVar('T')
Ps = ParamSpec('Ps')


class TaskQueues(TypedDict, Generic[A, B]):
  Qin: ReadQueue[A]
  Qout: WriteQueue[B]

@dataclass
class Task(Pipeline[A, B, TaskQueues[A, B], T], Generic[A, B, T]):
  """A pipeline that reads from a single input queue, writes to a single output queue"""

  Queues = TaskQueues

  def push_queue(self, get_queue: GetQueue, prefix: tuple[str, ...] = (), Qout: WriteQueue[B] | None = None) -> WriteQueue[A]:
    return get_queue(prefix + ('Qin',), self.Tin)
  
  def connect(self, Qout: WriteQueue[B], get_queue: GetQueue, prefix: tuple[str, ...] = ()):
    Qin = get_queue(prefix + ('Qin',), self.Tin)
    return TaskQueues(Qin=Qin, Qout=Qout)

  def observe(self, get_queue: GetQueue, prefix: tuple[str, ...] = ()) -> Tree[ReadQueue]:
    return { 'Qin': get_queue(prefix + ('Qin',), self.Tin) }
  
  @abstractmethod
  def run(self, queues: TaskQueues[A, B], /) -> T:
    ...
    