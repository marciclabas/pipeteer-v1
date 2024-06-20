from typing_extensions import AsyncIterable, Generic, TypeVar
import asyncio
import os
from datetime import timedelta
from haskellian import iter as I, Either, Left, IsLeft, Right
from kv.api import KV, InexistentItem as KVInexistentItem, DBError
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

  @classmethod
  def of(cls, conn_str: str, type: type[A] | None = None) -> 'QueueKV[A]':
    """Create a `Queue` with a `KV` from a connection string. Supports:
    - `file://<path>`: `FilesystemKV`
    - `sql+<protocol>://<conn_str>;Table=<table>`: `SQLKV`
    - `azure+blob://<conn_str>`: `BlobKV`
    - `azure+blob+container://<conn_str>;Container=<container_name>`: `BlobContainerKV`
    """
    from kv.api import KV
    return QueueKV(KV.of(conn_str, type))
  
  @classmethod
  def sqlite(cls, Type: type[B], path: str, table: str = 'queue') -> 'QueueKV[B]':
    try:
      from kv.sqlite import SQLiteKV
    except ImportError:
      raise ImportError('Install `kv-sqlite-sync` to run in local SQLite')
    return QueueKV(SQLiteKV.validated(Type, path, table))
  
  async def push(self, key: str, value: A):
    return (await self._kv.insert(key, value)).mapl(QueueError)
  
  async def _read(self, id: str | None = None) -> Either[ReadError, tuple[str, A]]:
    if id is None:
      key = I.head((await self._kv.keys()).unsafe())
      if key is None:
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
  