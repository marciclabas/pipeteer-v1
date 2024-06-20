from fastapi import FastAPI
from pipeteer import ReadQueue, WriteQueue
from haskellian import either as E
from dslog import Logger
from dslog.uvicorn import setup_loggers_lifespan, DEFAULT_FORMATTER, ACCESS_FORMATTER

def magic_autoprocessing(img: bytes) -> bytes | None:
  import random
  return random.choice([f'corrected: {img}'.encode(), None])

async def autocorrection(
  Qin: ReadQueue[bytes], Qout: WriteQueue[bytes|None], *,
  logger: Logger
):
  while True:
    id, img = (await Qin.read()).unsafe()
    logger(f'Autocorrecting "{id}"')
    result = magic_autoprocessing(img) # may fail and return None
    logger(f'Autocorrected "{id}". Result:', result)
    (await Qout.push(id, result)).unsafe()
    (await Qin.pop(id)).unsafe()


def validation_api(
  Qin: ReadQueue[bytes], Qout: WriteQueue[bool], *,
  logger: Logger
) -> FastAPI:
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


def manual_api(
  Qin: ReadQueue[bytes], Qout: WriteQueue[bytes], *,
  logger: Logger
) -> FastAPI:
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