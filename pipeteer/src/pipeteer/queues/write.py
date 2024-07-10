from typing_extensions import Generic, TypeVar, Callable, Awaitable, AsyncIterable, TypeGuard, overload, Any
from haskellian import promise as P, Either, Right, either as E
from abc import ABC, abstractmethod
from .errors import QueueError
from . import ops

A = TypeVar('A', contravariant=True)
B = TypeVar('B', contravariant=True)

class WriteQueue(ABC, Generic[A]):
  """A write-only queue"""
  
  async def iterate(self, items: AsyncIterable[tuple[str, A]]):
    """Push all `items`"""
    async for key, value in items:
      await self.push(key, value)

  @abstractmethod
  async def push(self, key: str, value: A) -> Either[QueueError, None]:
    ...

  def pusher(self, key: str) -> Callable[[A], Awaitable[Either[QueueError, None]]]:
    """Partially applied `push`"""
    return lambda value: self.push(key, value)
  
  @overload
  def prefilter(self, pred: Callable[[A], TypeGuard[B]]) -> 'WriteQueue[B]': ...
  @overload
  def prefilter(self, pred: Callable[[A], bool]) -> 'WriteQueue[A]': ...
  def prefilter(self, pred): # type: ignore
    return ops.prefilter(self, lambda kv: P.of(pred(kv[1])))
  
  def premap(self, f: Callable[[B], A]) -> 'WriteQueue[B]':
    return ops.premap(self, lambda kv: P.of(Right((kv[0], f(kv[1])))))
  
  def premap_kv(self, f: Callable[[str, B], A]) -> 'WriteQueue[B]':
    """Map but `f` receives both key and value"""
    @E.do()
    async def mapper(kv: tuple[str, B]):
      return kv[0], f(*kv)
    return ops.premap(self, mapper)
  
  def premap_k(self, f: Callable[[str], A]) -> 'WriteQueue':
    """Map but `f` receives the key"""
    @E.do()
    async def mapper(kv: tuple[str, B]):
      return kv[0], f(kv[1])
    return ops.premap(self, mapper)
  
  def premap_kvt(self, f: Callable[[tuple[str, B]], A]) -> 'WriteQueue[B]':
    """Map but `f` receives both key and value as a tuple"""
    @E.do()
    async def mapper(kv: tuple[str, B]):
      return kv[0], f(kv)
    return ops.premap(self, mapper)
  
  def apremap(self, f: Callable[[B], Awaitable[A]]) -> 'WriteQueue[B]':
    """Map but `f` is asynchronous"""
    @E.do()
    async def mapper(kv: tuple[str, B]):
      return kv[0], await f(kv[1])
    return ops.premap(self, mapper)
  
  def safe_apremap(self, f: Callable[[B], Awaitable[Either[Any, A]]]) -> 'WriteQueue[B]':
    """Map but `f` is asynchronous and can fail (ie. return `Left`)"""
    @E.do()
    async def mapper(kv: tuple[str, B]):
      return kv[0], (await f(kv[1])).unsafe()
    return ops.premap(self, mapper)
  
  def apremap_kv(self, f: Callable[[str, B], Awaitable[A]]) -> 'WriteQueue[B]':
    """Map but `f` is asynchronous and receives both key and value"""
    @E.do()
    async def mapper(kv: tuple[str, B]):
      return kv[0], await f(*kv)
    return ops.premap(self, mapper)
  
  def apremap_k(self, f: Callable[[str], Awaitable[A]]) -> 'WriteQueue':
    """Map but `f` is asynchronous and receives the key"""
    @E.do()
    async def mapper(kv: tuple[str, B]):
      return kv[0], await f(kv[0])
    return ops.premap(self, mapper)
  
  def apremap_kvt(self, f: Callable[[tuple[str, B]], Awaitable[A]]) -> 'WriteQueue[B]':
    """Map but `f` is asynchronous and receives both key and value as a tuple"""
    @E.do()
    async def mapper(kv: tuple[str, B]):
      return kv[0], await f(kv)
    return ops.premap(self, mapper)

