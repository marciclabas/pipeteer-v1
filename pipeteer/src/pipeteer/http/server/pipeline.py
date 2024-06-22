from typing import Any, TypeVar
from fastapi import FastAPI
from pipeteer import http, trees, ReadQueue, GetQueue, Pipeline

T = TypeVar('T')

def mount(pipeline: Pipeline[Any, T, Any, Any], Qout: ReadQueue[T], get_queue: GetQueue) -> FastAPI:
  """Mounts the pipeline's queues into a FastAPI app
  - `/input/write`: write API for the input queue
  - `/{path/to/queue}/read`: read API for each observable queue
  - `/output/read`: read API for the output queue
  """
  api = FastAPI()
  Qpush = pipeline.push_queue(get_queue)
  Qs = pipeline.observe(get_queue)
  api.mount('/input/write', http.write_api(Qpush, Type=pipeline.Tin))
  Tout: type = pipeline.Tout or Any # type: ignore (duh)
  api.mount('/output/read', http.read_api(Qout, Type=Tout))
  
  for path, queue in trees.flatten(Qs):
    AnyT: type = Any # type: ignore (duh)
    api.mount(f'/{"/".join(path)}/read', http.read_api(queue, Type=AnyT))

  return api