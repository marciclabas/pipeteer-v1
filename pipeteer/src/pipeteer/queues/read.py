from typing_extensions import Generic, TypeVar, Callable, Awaitable, overload, AsyncIterable, TypeGuard, Sequence
from abc import ABC, abstractmethod
from haskellian import AsyncIter, promise as P, Either, Right, iter as I, either as E
from .errors import QueueError, ReadError
from . import ops

A = TypeVar('A', covariant=True)
B = TypeVar('B', covariant=True)

class ReadQueue(ABC, Generic[A]):
  """A read/pop-only, point-readable queue"""

  @abstractmethod
  async def _read(self, id: str | None) -> Either[ReadError, tuple[str, A]]:
    ...

  @abstractmethod
  async def pop(self, id: str) -> Either[ReadError, None]:
    ...

  @overload
  async def read(self) -> Either[QueueError, tuple[str, A]]:
    ...
  @overload
  async def read(self, id: str) -> Either[ReadError, A]:
    ...
  
  @E.do[ReadError]()
  async def read(self, id: str | None = None) -> A | tuple[str, A]:
    k, v = (await self._read(id)).unsafe()
    return (k, v) if id is None else v
      
  @abstractmethod
  def _items(self) -> AsyncIterable[Either[QueueError, tuple[str, A]]]:
    ...

  def items(self) -> AsyncIter[Either[QueueError, tuple[str, A]]]:
    return AsyncIter(self._items())
  
  def keys(self) -> AsyncIter[Either[ReadError, str]]:
    return AsyncIter(e | I.fst async for e in self._items())
  
  def values(self) -> AsyncIter[Either[ReadError, A]]:
    return AsyncIter(e | I.snd async for e in self._items())
  
  def map(self, f: Callable[[A], B]) -> 'ReadQueue[B]':
    """Maps `f` over self. Returns a new queue, but `self` is still mutated when popping from the new queue"""
    return ops.map(self, lambda kv: P.of((kv[0], f(kv[1]))))
  
  def map_kv(self, f: Callable[[str, A], B]) -> 'ReadQueue[B]':
    """Map but `f` receives both key and value"""
    return ops.map(self, lambda kv: P.of((kv[0], f(*kv))))
  
  def map_k(self, f: Callable[[str], B]) -> 'ReadQueue[B]':
    """Map but `f` receives the key"""
    return ops.map(self, lambda kv: P.of((kv[0], f(kv[0]))))
  
  def map_kvt(self, f: Callable[[tuple[str, A]], B]) -> 'ReadQueue[B]':
    """Map but `f` receives both key and value as a tuple"""
    return ops.map(self, lambda kv: P.of((kv[0], f(kv))))
  
  def amap(self, f: Callable[[A], Awaitable[B]]) -> 'ReadQueue[B]':
    """Map but `f` is asynchronous"""
    async def mapper(kv: tuple[str, A]):
      return kv[0], await f(kv[1])
    return ops.map(self, mapper)
  
  def amap_kv(self, f: Callable[[str, A], Awaitable[B]]) -> 'ReadQueue[B]':
    """Map but `f` is asynchronous and receives both key and value"""
    async def mapper(kv: tuple[str, A]):
      return kv[0], await f(*kv)
    return ops.map(self, mapper)
  
  def amap_k(self, f: Callable[[str], Awaitable[B]]) -> 'ReadQueue[B]':
    """Map but `f` is asynchronous and receives the key"""
    async def mapper(kv: tuple[str, A]):
      return kv[0], await f(kv[0])
    return ops.map(self, mapper)
  
  def amap_kvt(self, f: Callable[[tuple[str, A]], Awaitable[B]]) -> 'ReadQueue[B]':
    """Map but `f` is asynchronous and receives both key and value as a tuple"""
    async def mapper(kv: tuple[str, A]):
      return kv[0], await f(kv)
    return ops.map(self, mapper)

  @overload
  def filter(self, pred: Callable[[A], TypeGuard[B]]) -> 'ReadQueue[B]': ...
  @overload
  def filter(self, pred: Callable[[A], bool]) -> 'ReadQueue[A]': ...
  def filter(self, pred): # type: ignore
    return ops.filter(self, lambda _, v: pred(v))
  
  @overload
  def filter_kv(self, pred: Callable[[str, A], TypeGuard[B]]) -> 'ReadQueue[B]': ...
  @overload
  def filter_kv(self, pred: Callable[[str, A], bool]) -> 'ReadQueue[A]': ...
  def filter_kv(self, pred): # type: ignore
    return ops.filter(self, pred)
  
  def partition(self, pred: Callable[[A], bool]) -> 'tuple[ReadQueue[A], ReadQueue[A]]':
    """Returns `self.filter(pred), self.filter(!pred)`"""
    return self.filter(pred), self.filter(lambda x: not pred(x))
  
  def partition_kv(self, pred: Callable[[str, A], bool]) -> 'tuple[ReadQueue[A], ReadQueue[A]]':
    """Returns `self.filter_kv(pred), self.filter_kv(!pred)`"""
    return self.filter_kv(pred), self.filter_kv(lambda *x: not pred(*x))
  
  

