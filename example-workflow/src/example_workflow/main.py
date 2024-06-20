if __name__ == '__main__':
  from multiprocessing import Process
  import asyncio
  from fastapi import FastAPI
  import uvicorn
  from pipeteer import make_queues, QueueKV
  from example_workflow import workflow, Artifacts, Input, Output
  from dslog import Logger

  DB = 'queue.sqlite'

  def make_queue(path, type):
    return QueueKV.sqlite(type, DB, table='-'.join(path))

  Qin = QueueKV.sqlite(Input, DB, table='Qin')
  Qout = QueueKV.sqlite(Output, DB, table='Qout')
  Qs = make_queues(Qin, Qout, workflow, make_queue=make_queue)
  artfs = Artifacts.of(Qs['internal'], logger=Logger.click().prefix('[WORKFLOW]')) # type: ignore


  api = FastAPI()
  api.mount('/validation', artfs.validation_api)
  api.mount('/correction', artfs.manual_api)

  procs = [
    Process(target=uvicorn.run, args=(api,)),
    Process(target=asyncio.run, args=(artfs.auto_correct,))
  ]

  for proc in procs:
    proc.start()
  for proc in procs:
    proc.join()