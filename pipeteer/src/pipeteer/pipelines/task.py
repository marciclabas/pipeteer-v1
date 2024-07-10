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
P = TypeVar('P')


class TaskQueues(TypedDict, Generic[A, B]):
  Qin: ReadQueue[A]
  Qout: WriteQueue[B]

class Task(Pipeline[A, B, TaskQueues[A, B], P, T], Generic[A, B, P, T]):
  """A pipeline that reads from a single input queue, writes to a single output queue"""

  Queues = TaskQueues

  def __repr__(self):
    from .reprs import str_types
    return f'Task[{str_types(self)}]'

  def push_queue(self, get_queue: GetQueue, params: P, /, *, prefix: tuple[str | int, ...] = ()) -> WriteQueue[A]:
    return get_queue(prefix, self.Tin)
  
  def connect(self, Qout: WriteQueue[B], get_queue: GetQueue, params: P, /, *, prefix: tuple[str|int, ...] = ()):
    Qin = get_queue(prefix, self.Tin)
    return TaskQueues(Qin=Qin, Qout=Qout)

  def tree(self) -> trees.Tree[Pipeline]:
    return self
  
  @abstractmethod
  def run(self, queues: TaskQueues[A, B], params: P, /) -> T:
    ...
    