from typing import TypedDict, Any, Callable, Coroutine
from dataclasses import dataclass
from fastapi import FastAPI
from pipeteer import Pipeline, Wrapped, Task, Workflow
from .pipelines import auto, Validation, ManualCorrection, LoggedAPI, Logger

@dataclass
class Input: # initial state, input to auto-correction
  img: bytes
@dataclass
class AutoCorrected: # input to validation
  img: bytes
  corrected: bytes
@dataclass
class ManualInput:
  img: bytes
@dataclass
class Output:
  img: bytes
  corrected: bytes

class Queues(TypedDict):
  auto: Wrapped.Queues
  validation: Wrapped.Queues
  manual: Wrapped.Queues

class WrappedAuto(Wrapped[Input, Any, bytes, bytes|None, Task.Queues, Callable[[Logger], Coroutine]]):
  def __init__(self):
    super().__init__(Input, auto)
  def pre(self, inp: Input):
    return inp.img
  def post(self, inp: Input, out: bytes | None):
    return AutoCorrected(inp.img, out) if out else ManualInput(inp.img)
  
class WrappedValidation(Wrapped[AutoCorrected, Any, bytes, bool, Validation.Queues, Validation.Artifacts]):
  def __init__(self):
    super().__init__(AutoCorrected, Validation())
  def pre(self, inp: AutoCorrected):
    return inp.corrected
  def post(self, inp: AutoCorrected, ok: bool):
    return Output(inp.img, inp.corrected) if ok else ManualInput(inp.img)
  
class WrappedManual(Wrapped[ManualInput, Any, bytes, bytes, ManualCorrection.Queues, ManualCorrection.Artifacts]):
  def __init__(self):
    super().__init__(ManualInput, ManualCorrection())
  def pre(self, inp: ManualInput):
    return inp.img
  def post(self, inp: ManualInput, out: bytes):
    return Output(inp.img, out)
  
class Pipelines(TypedDict):
  auto: WrappedAuto
  validation: WrappedValidation
  manual: WrappedManual

@dataclass
class Artifacts:
  coro: Callable[[], Coroutine]
  api: FastAPI

class MyWorkflow(Workflow[Input, Output, Pipelines, Queues, Callable[[Logger], Artifacts]]): # type: ignore
  Queues = Queues
  Artifacts = Callable[[Logger], Artifacts]
  Pipelines = Pipelines

  def __init__(self):
    super().__init__(Pipelines(
      auto=WrappedAuto(),
      validation=WrappedValidation(),
      manual=WrappedManual(),
    ))

  def run(self, queues: Queues) -> Artifacts:
    def bound(logger: Logger):
      coro = self.pipelines['auto'].run(queues['auto'])
      val_api = self.pipelines['validation'].run(queues['validation'])
      manual_api = self.pipelines['manual'].run(queues['manual'])
      api = FastAPI()
      api.mount('/validation', val_api(logger))
      api.mount('/manual', manual_api(logger))
      return Artifacts(coro=lambda: coro(logger), api=api)

    return bound
  

Workflow.dict({
  'auto': WrappedAuto(),
  'validation': WrappedValidation(),
  'manual': WrappedManual(),
})