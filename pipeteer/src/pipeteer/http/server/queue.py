from typing import TypeVar, Callable, overload
from pipeteer.queues import Queue, QueueError
from fastapi import FastAPI
from pydantic import TypeAdapter
from haskellian import Right, Left, Either
from .read import read_api
from .write import write_api

T = TypeVar('T')
U = TypeVar('U')


def _api(
  queue: Queue[T], *,
  parse: Callable[[bytes], Either[QueueError, T]] = Right,
  dump: Callable[[T], bytes|str] = lambda x: x, # type: ignore
) -> FastAPI:
  app = FastAPI(generate_unique_id_function=lambda route: route.name)
  app.mount('/read', read_api(queue, dump=dump))
  app.mount('/write', write_api(queue, parse=parse))

  return app
  
@overload
def queue_api(queue: Queue[T], *, Type: type[T]) -> FastAPI: ...
@overload
def queue_api(
  queue: Queue[T], *,
  parse: Callable[[bytes], Either[QueueError, T]] = Right,
  dump: Callable[[T], bytes] = lambda x: x # type: ignore
) -> FastAPI: ...

def queue_api(queue, Type=None, dump=lambda x: x, parse=Right): # type: ignore
  if Type is not None:
    Adapter = TypeAdapter(Type)
    dump = Adapter.dump_json
    def parse(x):
      try:
        return Right(Adapter.validate_json(x))
      except Exception as e:
        return Left(QueueError(str(e)))
  return _api(queue, dump=dump, parse=parse)
