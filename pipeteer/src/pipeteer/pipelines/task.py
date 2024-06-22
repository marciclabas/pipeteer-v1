from typing import TypeVar, Generic, TypedDict, ParamSpec
from dataclasses import dataclass
from abc import abstractmethod
from pipeteer.queues import ReadQueue, WriteQueue
from pipeteer import Pipeline, GetQueue, trees

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')
D = TypeVar('D')
T = TypeVar('T')
Ps = ParamSpec('Ps')


class TaskQueues(TypedDict, Generic[A, B]):
  Qin: ReadQueue[A]
  Qout: WriteQueue[B]

class Task(Pipeline[A, B, TaskQueues[A, B], T], Generic[A, B, T]):
  """A pipeline that reads from a single input queue, writes to a single output queue"""

  Queues = TaskQueues

  def __repr__(self):
    from .reprs import str_types
    return f'Task[{str_types(self)}]'

  def push_queue(self, get_queue: GetQueue, prefix: tuple[str, ...] = (), Qout: WriteQueue[B] | None = None) -> WriteQueue[A]:
    return get_queue(prefix + ('Qin',), self.Tin)
  
  def connect(self, Qout: WriteQueue[B], get_queue: GetQueue, prefix: tuple[str, ...] = ()):
    Qin = get_queue(prefix + ('Qin',), self.Tin)
    return TaskQueues(Qin=Qin, Qout=Qout)

  def tree(self) -> trees.Tree[Pipeline]:
    return self
  
  @abstractmethod
  def run(self, queues: TaskQueues[A, B], /) -> T:
    ...
    