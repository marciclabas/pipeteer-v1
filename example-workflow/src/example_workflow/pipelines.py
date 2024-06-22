from typing import Protocol
from functools import partial
from fastapi import FastAPI
from pipeteer import Task
from haskellian import either as E
from dslog import Logger
from dslog.uvicorn import setup_loggers_lifespan, DEFAULT_FORMATTER, ACCESS_FORMATTER

def magic_autoprocessing(img: bytes) -> bytes | None:
  import random
  return random.choice([f'corrected: {img}'.encode(), None])

@partial(Task.retried, bytes, retry_after=5, Tout=bytes|None)
def auto(queues: Task.Queues[bytes, bytes|None]):
  Qin, Qout = queues['Qin'], queues['Qout']
  @E.do()
  async def run_one(logger: Logger):
    id, img = (await Qin.read()).unsafe()
    logger(f'Autocorrecting "{id}"')
    result = magic_autoprocessing(img) # may fail and return None
    logger(f'Autocorrected "{id}". Result:', result)
    (await Qout.push(id, result)).unsafe()
    (await Qin.pop(id)).unsafe()

  return run_one


class LoggedAPI(Protocol):
  def __call__(self, logger: Logger) -> FastAPI:
    ...

class Validation(Task[bytes, bool, LoggedAPI]):

  Artifacts = LoggedAPI
  Queues = Task.Queues[bytes, bool]
  Pipeline = Task[bytes, bool, LoggedAPI]

  def __init__(self):
    super().__init__(bytes, bool)

  def run(self, queues: Task.Queues[bytes, bool]) -> LoggedAPI:
    Qin, Qout = queues['Qin'], queues['Qout']

    def validation_api(logger: Logger) -> FastAPI:
      app = FastAPI(lifespan=setup_loggers_lifespan(access=logger.format(ACCESS_FORMATTER), uvicorn=logger.format(DEFAULT_FORMATTER)))
      
      @app.get('/tasks')
      async def tasks():
        return await Qin.items().map(E.unsafe).sync()

      @app.get('/validate')
      async def validate(id: str, ok: bool):
        (await Qin.read(id)).unsafe()
        (await Qout.push(id, ok)).unsafe()
        (await Qin.pop(id)).unsafe()

      return app
    
    return validation_api
  
class ManualCorrection(Task[bytes, bytes, LoggedAPI]):

  Artifacts = LoggedAPI
  Queues = Task.Queues[bytes, bytes]

  def __init__(self):
    super().__init__(bytes, bytes)

  def run(self, queues: Task.Queues[bytes, bytes]) -> LoggedAPI:
    Qin, Qout = queues['Qin'], queues['Qout']

    def manual_api(logger: Logger) -> FastAPI:
      app = FastAPI(lifespan=setup_loggers_lifespan(access=logger.format(ACCESS_FORMATTER), uvicorn=logger.format(DEFAULT_FORMATTER)))
      
      @app.get('/tasks')
      async def tasks():
        return await Qin.items().map(E.unsafe).sync()

      @app.get('/correct')
      async def validate(id: str, corrected: bytes):
        (await Qin.read(id)).unsafe()
        (await Qout.push(id, corrected)).unsafe()
        (await Qin.pop(id)).unsafe()

      return app
    
    return manual_api
  