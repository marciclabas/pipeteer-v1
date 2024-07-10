from typing_extensions import AsyncIterable, Generic, TypeVar
import asyncio
from datetime import timedelta
import random
from haskellian import Either, Left, IsLeft, Right
from kv import KV, InexistentItem as KVInexistentItem
from pipeteer.queues import Queue, QueueError, ReadError, InexistentItem

A = TypeVar('A')
B = TypeVar('B')

class QueueKV(Queue[A], Generic[A]):
  """Poll-based queue backed by a `KV` object"""
  def __init__(
    self, kv: KV[A],
    poll_interval: timedelta = timedelta(seconds=5),
  ):
    self._kv = kv
    self.poll_interval = poll_interval

  def __repr__(self):
    return f'QueueKV({type(self._kv).__name__})'

  @staticmethod
  def of(conn_str: str, type: type[A] | None = None) -> 'QueueKV[A]':
    """Create a `Queue` with a `KV` from a connection string"""
    return QueueKV(KV.of(conn_str, type))
  
  @staticmethod
  def sqlite(Type: type[B], path: str, table: str = 'queue') -> 'QueueKV[B]':
    from kv import SQLiteKV
    kv = SQLiteKV.at(path, Type, table=table)
    return QueueKV(kv)
  
  async def push(self, key: str, value: A):
    return (await self._kv.insert(key, value)).mapl(QueueError)
  
  async def _read(self, id: str | None = None) -> Either[ReadError, tuple[str, A]]:
    if id is None:
      keys = await self._kv.keys().sync()
      if keys:
        key = random.choice(keys).unsafe()
      else:
        await asyncio.sleep(self.poll_interval.total_seconds())
        return await self._read(id)
    else:
      key = id
    
    try:
      value = (await self._kv.read(key)).unsafe()
      return Right((key, value))
    except IsLeft as e:
      match e.value:
        case KVInexistentItem():
          return Left(InexistentItem(key))
        case err:
          return Left(QueueError(err))
        
  async def pop(self, id: str) -> Either[QueueError | InexistentItem, None]:
    match await self._kv.delete(id):
      case Left(KVInexistentItem()):
        return Left(InexistentItem(id))
      case Left(err):
        return Left(QueueError(err))
      case _:
        return Right(None)
    
  def _items(self) -> AsyncIterable[Either[QueueError, tuple[str, A]]]:
    return self._kv.items().map(lambda e: e.mapl(QueueError))
  