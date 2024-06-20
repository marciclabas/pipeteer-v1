from typing_extensions import TypeVar, TypedDict, Generic, Callable, Mapping, Sequence, Iterable, TypeAlias
from haskellian import iter as I
from pipeteer.queues import ReadQueue, WriteQueue, Queue, ops
from pipeteer.pipelines import Pipeline, Wrapped, Workflow

A = TypeVar('A')
B = TypeVar('B')
T = TypeVar('T')
Q = TypeVar('Q', Queue, ReadQueue, WriteQueue)

class PipelineQueues(TypedDict, Generic[A, B]):
  """Possibly nested pipeline queues"""
  Qin: ReadQueue[A]
  Qout: WriteQueue[B]
  internal: Mapping[str, 'PipelineQueues'] | 'PipelineQueues'

Tree: TypeAlias = A | Mapping[str, 'Tree[A]']

def input_queues(
  Qin: Q, pipeline: Pipeline, *,
  make_queue: Callable[[Sequence[str], type], Q], prefix: tuple[str, ...] = ()
) -> Tree[Q]:
  """All actual input queues"""
  match pipeline:
    case Workflow() as wkf:
      Qins = {
        id: make_queue(prefix + (id,), pipe.Tin)
        for id, pipe in wkf.pipelines.items()
          if id != pipeline.input_pipeline
      }
      return {
        id: input_queues(Qins[id], pipe, make_queue=make_queue, prefix=prefix + (id,))
        for id, pipe in wkf.pipelines.items()
          if id != pipeline.input_pipeline
      }
    case Wrapped() as wpd:
      return input_queues(Qin, wpd.pipeline, make_queue=make_queue, prefix=prefix + ('wrapped',))
    case Pipeline():
      return Qin
    
def connect_queues(
  Qin: ReadQueue[A], Qout: WriteQueue[B], pipeline: Pipeline[A, B], *,
  make_queue: Callable[[Sequence[str], type[T]], Queue[T]], prefix: tuple[str, ...] = ()
) -> PipelineQueues[A, B]:
  """Connect all queues of a `pipeline` into a nested tree"""
  match pipeline:
    case Workflow() as workflow:
      Qins = {
        task: (
          Qin if task == workflow.input_pipeline else
          make_queue(prefix + (task,), workflow.pipelines[task].Tin)
        )
        for task in workflow.pipelines
      }
      inner_Qout = ops.prejoin(Qout, [(Qin, workflow.pipelines[id].Tin) for id, Qin in Qins.items()]) # type: ignore
      internal = {
        task: connect_queues(Qins[task], inner_Qout, workflow.pipelines[task], make_queue=make_queue, prefix=prefix + (task,))
        for task in workflow.pipelines
      }
      return PipelineQueues(Qin=Qin, Qout=Qout, internal=internal)

    case Wrapped() as wrapped:
      inner_Qin = ops.immutable(Qin).map(wrapped.pre)
      inner_Qout = ops.premerge(Qin, Qout, wrapped.post)
      internal = connect_queues(inner_Qin, inner_Qout, wrapped.pipeline, make_queue=make_queue, prefix=prefix + ('wrapped',))
      return PipelineQueues(Qin=Qin, Qout=Qout, internal=internal)
    
    case Pipeline():
      return PipelineQueues(Qin=Qin, Qout=Qout) # type: ignore
    
@I.lift
def flatten_queues(queues: Tree[Q], prefix: tuple[str, ...] = ()) -> Iterable[tuple[Sequence[str], Q]]:
  """Flatten a nested tree of queues into a sequence of `(path, queue)` pairs"""
  match queues:
    case ReadQueue() | WriteQueue():
      yield prefix, queues
    case Mapping():
      for id, subtree in queues.items():
        yield from flatten_queues(subtree, prefix + (id,))