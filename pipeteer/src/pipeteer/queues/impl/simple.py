from typing_extensions import Generic, TypeVar, AsyncIterable, Never
from collections import OrderedDict
from haskellian import ManagedPromise, Either, Left, Right
from pipeteer.queues import Queue, InexistentItem

A = TypeVar('A')
B = TypeVar('B')

class SimpleQueue(Queue[A], Generic[A]):
  """Reactive, in-memory implementation backed by an `OrderedDict`"""

  def __init__(self, name: str | None = None):
    self.xs: OrderedDict[str, A] = OrderedDict()
    self._next = ManagedPromise()
    self.name = name

  def __repr__(self):
    return f'SimpleQueue({self.name or ""})'

  def __len__(self):
    return len(self.xs) # type: ignore

  async def _read(self, id: str | None = None) -> Either[InexistentItem, tuple[str, A]]:
    if id is None:
      if len(self.xs) == 0:
        await self._next
        self._next = ManagedPromise()
        return await self._read(id)
      else:
        return Right(next(iter(self.xs.items())))
    elif id in self.xs:
      v = self.xs[id]
      return Right((id, v))
    else:
      return Left(InexistentItem(id))
    
  async def pop(self, id: str):
    if id in self.xs:
      del self.xs[id]
      return Right(None)
    else:
      return Left(InexistentItem(id))
    
  async def push(self, key: str, value: A) -> Right[Never, None]:
    self.xs[key] = value
    if not self._next.resolved:
      self._next.resolve()
    return Right(None)
  
  async def _items(self) -> AsyncIterable[Right[Never, tuple[str, A]]]:
    for x in self.xs.items():
      yield Right(x)
  