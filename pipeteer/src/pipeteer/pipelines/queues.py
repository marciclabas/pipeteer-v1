from typing import Protocol, Sequence, TypeVar, TypedDict, Generic, Mapping, Iterable
from haskellian import iter as I, promise as P, funcs as F
from pipeteer.queues import ReadQueue, WriteQueue, Queue, ops
from pipeteer.pipelines import Pipeline, Wrapped, Workflow

A = TypeVar('A')
B = TypeVar('B')
S = TypeVar('S')
T = TypeVar('T')

class MakeQueue(Protocol):
  def __call__(self, path: Sequence[str], type: type[T], /) -> Queue[T]:
    ...

def push_queue(pipeline: Pipeline[A, B], make_queue: MakeQueue, prefix: tuple[str, ...] = (), Qout: WriteQueue[B] | None = None) -> WriteQueue[A]:
  def _push_queue(pipeline: Pipeline[A, B], prefix: tuple[str, ...], Qout: WriteQueue[B] | None) -> WriteQueue[A]:
    match pipeline:
      case Workflow() as wkf:
        return ops.prejoin([(_push_queue(pipe, prefix + (id,), Qout), pipe.Tin) for id, pipe in wkf.pipelines.items()], fallback=Qout)
      
      case Wrapped() as wpd:
        Qwrapper = make_queue(prefix, wpd.Tin)
        Qpush = _push_queue(wpd.pipeline, prefix + ('wrapped',), Qout)
        return ops.tee(Qwrapper, Qpush.apremap(F.flow(wpd.pre, P.wait)))
      
      case Pipeline() as pipe:
        return make_queue(prefix, pipe.Tin)
      
  return _push_queue(pipeline, prefix, Qout)


class PipelineQueues(TypedDict, Generic[A, B]):
  Qin: ReadQueue[A]
  Qout: WriteQueue[B]

Tree = T | Mapping[str, 'Tree[T]']

def connect_queues(
  pipeline: Pipeline[A, B], Qout: WriteQueue[B],
  make_queue: MakeQueue, prefix: tuple[str, ...] = (),
) -> Tree[PipelineQueues]:
  
  def _connect(pipeline: Pipeline[A, B], prefix: tuple[str, ...], Qout: WriteQueue[B]):
    
    match pipeline:
      case Workflow() as wkf:
        Qpush = push_queue(wkf, prefix=prefix, make_queue=make_queue, Qout=Qout)
        return { id: _connect(pipe, prefix + (id,), Qpush) for id, pipe in wkf.pipelines.items() }
      
      case Wrapped() as wpd:
        Qwrapper = make_queue(prefix, wpd.Tin)
        wrapped_Qout = ops.premerge(Qwrapper, Qout, wpd.post)
        return _connect(wpd.pipeline, prefix + ('wrapped', ), wrapped_Qout)
      
      case Pipeline() as pipe:
        Qin = make_queue(prefix, pipe.Tin)
        return PipelineQueues(Qin=Qin, Qout=Qout)
      
  return _connect(pipeline, prefix, Qout)

@I.lift
def flatten_queues(queues: Tree[PipelineQueues], prefix: tuple[str, ...] = ()) -> Iterable[tuple[Sequence[str], ReadQueue | WriteQueue]]:
  if isinstance(queues, Mapping):
    for id, qs in queues.items():
      yield from flatten_queues(qs, prefix + (id,)) # type: ignore
  else:
    yield prefix, queues