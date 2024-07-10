from typing_extensions import TypeVar, Generic, Sequence, Callable, Awaitable, Any
from dataclasses import dataclass
import asyncio
from haskellian import Either, Left, Right, either as E, promise as P
from pipeteer.queues import WriteQueue, QueueError, ReadQueue

A = TypeVar('A')
B = TypeVar('B')
S1 = TypeVar('S1')
S2 = TypeVar('S2')

@dataclass
class prejoin(WriteQueue[A], Generic[A]):
  """Pre-join queues based on the pushed value type."""

  outputs: Sequence[tuple[WriteQueue[A], type[A]]]
  fallback: WriteQueue[A] | None = None

  def __repr__(self):
    reprs = ', '.join(repr(q) for q, _ in self.outputs)
    return f'prejoin({reprs})'

  async def push(self, key: str, value: A) -> Either[QueueError, None]:
    for q, t in self.outputs:
      if isinstance(value, t):
        return await q.push(key, value)
    if not self.fallback:
      return Left(QueueError(f'Received value with type {type(value)}, which doesn\'t match any of the available types. Value: {value}'))
    return await self.fallback.push(key, value)

@dataclass
class premerge(WriteQueue[B], Generic[B, S1, S2]):
  """Merges an input queue `Qin` with the pushed values using `merge`"""
  
  Qin: ReadQueue[S1]
  Qout: WriteQueue[S2]
  merge: Callable[[S1, B], Awaitable[S2] | S2]

  def __repr__(self):
    return f'premerge({repr(self.Qin)} -> {repr(self.Qout)})'

  @E.do[QueueError]()
  async def push(self, key: str, value: B): # type: ignore (python, bruh)
    state = (await self.Qin.read(key)).unsafe()
    next = await P.wait(self.merge(state, value))
    (await self.Qout.push(key, next)).unsafe()
    (await self.Qin.pop(key)).unsafe()


class tee(WriteQueue[A], Generic[A]):
  """A queue that pushes to the multiple queues at once"""

  def __init__(self, q1: WriteQueue[A], q2: WriteQueue[A], /, *qs: WriteQueue[A]):
    self.queues: Sequence[WriteQueue[A]] = [q1, q2, *qs]

  def __repr__(self) -> str:
    reprs = ', '.join(repr(q) for q in self.queues)
    return f'tee({reprs})'

  @E.do[QueueError]()
  async def push(self, key: str, value: A): # type: ignore (duh)
    results = await asyncio.gather(*[q.push(key, value) for q in self.queues])
    E.sequence(results).mapl(QueueError).unsafe()


class prefilter(WriteQueue[A], Generic[A]):
  
  def __init__(self, q: WriteQueue[A], p: Callable[[tuple[str, A]], Awaitable[bool]]):
    self._wrapped = q
    self._predicate = p

  def __repr__(self):
    return f'prefilter({self._wrapped!r})'

  async def push(self, key: str, value: A) -> Either[QueueError, None]:
    if await self._predicate((key, value)):
      return await self._wrapped.push(key, value)
    return Right(None)


class premap(WriteQueue[B], Generic[A, B]):
  
  def __init__(self, q: WriteQueue[A], f: Callable[[tuple[str, B]], Awaitable[Either[Any, tuple[str, A]]]]):
    self._wrapped = q
    self._mapper = f

  def __repr__(self):
    return f'premap({self._wrapped!r})'

  @E.do()
  async def push(self, key: str, value: B):
    k, v = (await self._mapper((key, value))).unsafe()
    return (await self._wrapped.push(k, v)).unsafe()