from typing import TypeVar, Generic, AsyncIterable, Callable, Sequence, Literal
import asyncio
from datetime import timedelta
import json
from pydantic import TypeAdapter
from haskellian import Either, Left, Right, asyn_iter as AI
from pipeteer.queues import ReadQueue, ReadError, QueueError, InexistentItem
from .util import urljoin, validate_left
from .request import request, Request

T = TypeVar('T')

KeysType = TypeAdapter(Sequence[Either[QueueError, str]])

def validate_seq(raw_json: bytes) -> Sequence[Either[QueueError, str]]:
  try:
    return KeysType.validate_json(raw_json)
  except Exception as e:
    return [Left(QueueError(e))]

  
class ReadClient(ReadQueue[T], Generic[T]):
    
  def __init__(
    self, url: str, *,
    parse: Callable[[bytes], Either[QueueError, T]] = Right,
    polling_interval = timedelta(seconds=15),
    request: Request = request
  ):
    self.read_url = url
    self.parse = parse
    self.polling_interval = polling_interval
    self.request = request

  async def _read_req(
    self, method: Literal['GET', 'POST', 'DELETE'], path: str, *,
    data: bytes | str | None = None, params: dict = {}
  ):
    try:
      r = await self.request(method, urljoin(self.read_url, path), data=data, params=params)
      return Right(r.content) if r.status_code == 200 else validate_left(r.content, r.status_code)
    except Exception as e:
      return Left(QueueError(e))

  @classmethod
  def validated(cls, Type: type[T], url: str, *, polling_interval = timedelta(seconds=15), request: Request = request) -> 'ReadClient[T]':
    from pydantic import TypeAdapter
    Adapter = TypeAdapter(Type)
    def parse(x):
      try:
        return Right(Adapter.validate_json(x))
      except Exception as e:
        return Left(QueueError(str(e)))
    return cls(url, parse=parse, polling_interval=polling_interval, request=request)


  async def _read(self, id: str | None) -> Either[ReadError, tuple[str, T]]: # type: ignore
    
    if id is None: # read/any -> returns an arbitrary id
      r = await self._read_req('GET', 'read/any')
      if r.tag == 'left':
        if r.value.reason == 'inexistent-item':
          await asyncio.sleep(self.polling_interval.total_seconds())
          return await self._read(None)

      id: str = json.loads(r.unsafe())

    data = await self._read_req('GET', 'read', params=dict(id=id))
    return data.bind(self.parse).fmap(lambda val: (id, val))
  
  async def pop(self, id: str) -> Either[QueueError | InexistentItem, None]:
    return (await self._read_req('GET', 'pop', params=dict(id=id))).fmap(lambda _: None)
    
  async def _items(self) -> AsyncIterable[Either[QueueError, tuple[str, T]]]:
    keys = await self.keys().sync()
    for key in keys:
      if key.tag == 'left':
        yield Left(key.value)
      else:
        yield (await self._read(key.value)).mapl(QueueError)

  @AI.lift
  async def keys(self) -> AsyncIterable[Either[QueueError, str]]:
    r = await self._read_req('GET', 'keys')
    if r.tag == 'left':
      yield r.mapl(QueueError)
    else:
      for key in validate_seq(r.value):
        yield key