# Pipeteer

> Queue-based workflow orchestration

## What is Pipeteer?

Pipeteer is a framework for orchestrating complex, data-first workflows using queues. It simplifies the process of transforming data, including workflows that require user interaction.

## Use Case Example

Imagine you need to perspective correct images. Your workflow might include:
1. Automatic correction
2. Manual validation
3. Manual correction (if auto-correction fails)

### Defining Pipelines

Pipelines are functions that read inputs and write outputs. Here’s how you can define them:

#### Automatic Correction

```python
from pipeteer import ReadQueue, WriteQueue

async def automatic_correction(Qin: ReadQueue[bytes], Qout: WriteQueue[bytes|None]):
  while True:
    id, img = await Qin.read()
    result = magic_autoprocessing(img) # may fail and return None
    await Qout.push(id, result)
    await Qin.pop(id)
```

#### Manual Validation

Manual processes return *artifacts*, which are anything that you'll know how to run. For example:

```python
from fastapi import FastAPI
from pipeteer import ReadQueue, WriteQueue

def validation_api(Qin: ReadQueue[bytes], Qout: WriteQueue[bool]) -> FastAPI:
  app = FastAPI()
  
  @app.get('/tasks')
  async def tasks():
    return await Qin.items()

  @app.post('/validate')
  async def validate(id: str, ok: bool):
    await Qout.push(id, ok)
    await Qin.pop(id)

  return app
```

### Orchestration

We want our data to follow this path:
1. Automatic correction
  - If OK -> Validation
  - If KO -> Manual correction
2. Validation
  - If OK -> Done
  - If KO -> Manual correction
3. Manual correction
  - Always Done

#### Defining States

Define the state of data at each step:

```python
class Input: # initial state, input to auto-correction
  img: bytes

class AutoCorrected: # input to validation
  img: bytes
  corrected: bytes

class ManualInput:
  img: bytes

class Output:
  img: bytes
  corrected: bytes
```

#### Wrapping Pipelines

Wrap the original pipelines to match the types:

```
State -pre-> Input ---> Pipeline ---> Output -post-> Next State
  |                                            |
  └--------------------------------------------┘
```

```python
from pipeteer import Pipeline, Wrapped

def post_auto(inp: Input, out: bytes | None):
  return AutoCorrected(inp.img, out) if out else ManualInput(inp.img)

def post_validate(inp: AutoCorrected, ok: bool):
  return Output(inp.img, inp.corrected) if ok else ManualInput(inp.img)

def post_manual(inp: ManualInput, out: bytes):
  return Output(inp.img, out)

auto = Wrapped(Input, Pipeline(bytes, bytes), pre=lambda inp: inp.img, post=post_auto)
val = Wrapped(AutoCorrected, Pipeline(bytes, bool), pre=lambda inp: inp.corrected, post=post_validate)
manual = Wrapped(ManualInput, Pipeline(bytes, bytes), pre=lambda inp: inp.img, post=post_manual)
```

#### Defining the Workflow

```python
from pipeteer import Workflow

workflow = Workflow(
  Input, Output,
  pipelines={
    'auto-correct': auto,
    'validation': val,
    'manual-correct': manual
  },
)
```

#### Defining Artifacts

```python
from fastapi import FastAPI
from pipeteer import ReadQueue, WriteQueue, PipelineQueues

class Artifacts:
  validation_api: FastAPI
  manual_api: FastAPI
  auto_correct: Coroutine

  @staticmethod
  def of(queues: Mapping[str, PipelineQueues]):
    return Artifacts(
      validation_api=validation_api(**queues['validation']['internal']),
      manual_api=manual_api(**queues['manual-correct']['internal']),
      auto_correct=automatic_correction(**queues['auto-correct']['internal']),
    )
```

### What Does Pipeteer Do?

Pipeteer connects the queues (and provides multiple queue implementations). For example:

```python
from pipeteer import Queue, make_queues, QueueKV

def make_queue(Type: type, path: Sequence[str]) -> Queue:
  table = '-'.join(path)
  return QueueKV.sqlite(Type, path='queues.db', table=table)

Qin = make_queue(Input, ['input'])
Qout = make_queue(Output, ['output'])
queues = make_queues(Qin, Qout, workflow, make_queue)
artifacts = Artifacts.of(queues)
```

### Running the Artifacts

You can run the artifacts as needed. For instance:

```python
from multiprocessing import Process
import asyncio
from fastapi import FastAPI
import uvicorn

api = FastAPI()
api.mount('/validation', artifacts.validation_api)
api.mount('/correction', artifacts.manual_api)

procs = [
  Process(target=uvicorn.run, args=(api, )),
  Process(target=asyncio.run, args=(artifacts.auto_correct,))
]
for proc in procs:
  proc.start()
for proc in procs:
  proc.join()
```

### Installation

```sh
pip install pipeteer
```

### Usage

Follow the example provided to define your workflows, wrap pipelines, and run the artifacts.
