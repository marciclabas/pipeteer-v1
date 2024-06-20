from dataclasses import dataclass
from pipeteer import Pipeline, Wrapped, Workflow

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

def post_auto(inp: Input, out: bytes | None):
  return AutoCorrected(inp.img, out) if out else ManualInput(inp.img)

def post_validate(inp: AutoCorrected, ok: bool):
  return Output(inp.img, inp.corrected) if ok else ManualInput(inp.img)

def post_manual(inp: ManualInput, out: bytes):
  return Output(inp.img, out)

auto = Wrapped(Input, Pipeline(bytes, bytes), pre=lambda inp: inp.img, post=post_auto)
val = Wrapped(AutoCorrected, Pipeline(bytes, bool), pre=lambda inp: inp.corrected, post=post_validate)
manual = Wrapped(ManualInput, Pipeline(bytes, bytes), pre=lambda inp: inp.img, post=post_manual)

workflow = Workflow({
  'auto-correct': auto,
  'validation': val,
  'manual-correct': manual
})