from typing_extensions import TypeVar, Generic, Callable, Awaitable, AsyncIterable
from dataclasses import dataclass
from haskellian import Either, Right
from pipeteer.queues import ReadQueue, QueueError, ReadError

A = TypeVar('A')
B = TypeVar('B')

@dataclass
class immutable(ReadQueue[A], Generic[A]):
  """An immutable view of a `ReadQueue`"""
  queue: ReadQueue[A]

  async def _read(self, id: str | None):
    return await self.queue._read(id)
  
  async def pop(self, id: str):
    return Right(None)
  
  def _items(self):
    return self.queue._items()
  
  def __getattr__(self, name: str):
    return getattr(self.queue, name)
  
class map(ReadQueue[B], Generic[A, B]):
  
  def __init__(self, q: ReadQueue[A], f: Callable[[tuple[str, A]], Awaitable[tuple[str, B]]]):
    self._queue = q
    self._mapper = f

  def __repr__(self):
    return f'mapped({repr(self._queue)})'

  async def _items(self) -> AsyncIterable[Either[QueueError, tuple[str, B]]]:
    async for e in self._queue._items():
      if e.tag == 'left':
        yield e # type: ignore
      else:
        yield Right(await self._mapper(e.value))

  async def _read(self, id: str | None) -> Either[ReadError, tuple[str, B]]:
    match await self._queue._read(id):
      case Right((k, v)):
        return Right(await self._mapper((k, v)))
      case err:
        return err # type: ignore
      
  async def pop(self, id: str):
    return await self._queue.pop(id)
      
class filter(ReadQueue[A], Generic[A]):

  def __init__(self, queue: ReadQueue[A], pred: Callable[[str, A], bool]):
    self._pred = pred
    self._queue = queue

  def __repr__(self):
    return f'filtered({repr(self._queue)})'

  async def _point_read(self, id: str) -> Either[ReadError, tuple[str, A]]:
    e = await self._queue.read(id)
    if e.tag == 'left':
      return e # type: ignore
    item = e.value
    return Right((id, item))

  async def _read_any(self) -> Either[QueueError, tuple[str, A]]:
    async for e in self._items():
      if e.tag == 'left':
        return e
      id, item = e.value
      return Right((id, item))
    return await self._read_any()

  async def _read(self, id: str | None) -> Either[ReadError, tuple[str, A]]:
    return await (self._read_any() if id is None else self._point_read(id))
  
  async def pop(self, id: str):
    return await self._queue.pop(id)
  
  async def _items(self) -> AsyncIterable[Either[QueueError, tuple[str, A]]]:
    async for e in self._queue._items():
      if e.tag == 'left':
        yield e
      elif self._pred(*e.value):
        yield e