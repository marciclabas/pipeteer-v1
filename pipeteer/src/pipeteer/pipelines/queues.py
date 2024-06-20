from typing_extensions import TypeVar, TypedDict, Generic, Callable, Mapping, Sequence, Iterable, NotRequired
from pipeteer.queues import ReadQueue, WriteQueue, Queue, ops
from pipeteer.pipelines import Pipeline, Wrapped, Workflow

A = TypeVar('A')
B = TypeVar('B')
T = TypeVar('T')

class PipelineQueues(TypedDict, Generic[A, B]):
  """Possibly nested pipeline queues"""
  Qin: ReadQueue[A]
  Qout: WriteQueue[B]
  internal: Mapping[str, 'PipelineQueues'] | 'PipelineQueues'

def make_queues(
  Qin: ReadQueue[A], Qout: WriteQueue[B], pipeline: Pipeline[A, B], *,
  make_queue: Callable[[Sequence[str], type[T]], Queue[T]], prefix: tuple[str, ...] = ()
) -> PipelineQueues[A, B]:
  """Connect all queues of a `pipeline` into a nested tree"""
  match pipeline:
    case Workflow() as workflow:
      Qins = {
        task: (
          Qin if task == workflow.input_task else
          make_queue(prefix + (task,), workflow.pipelines[task].Tin)
        )
        for task in workflow.pipelines
      }
      inner_Qout = ops.prejoin(Qout, [(Qin, workflow.pipelines[id].Tin) for id, Qin in Qins.items()]) # type: ignore
      internal = {
        task: make_queues(Qins[task], inner_Qout, workflow.pipelines[task], make_queue=make_queue, prefix=prefix + (task,))
        for task in workflow.pipelines
      }
      return PipelineQueues(Qin=Qin, Qout=Qout, internal=internal)

    case Wrapped() as wrapped:
      inner_Qin = ops.immutable(Qin).map(wrapped.pre)
      inner_Qout = ops.premerge(Qin, Qout, wrapped.post)
      internal = make_queues(inner_Qin, inner_Qout, wrapped.pipeline, make_queue=make_queue, prefix=prefix + ('wrapped',))
      return PipelineQueues(Qin=Qin, Qout=Qout, internal=internal)
    
    case Pipeline():
      return PipelineQueues(Qin=Qin, Qout=Qout) # type: ignore
    
def flatten_queues(queues: PipelineQueues, *, prefix: tuple[str, ...] = ()) -> Iterable[tuple[Sequence[str], ReadQueue]]:
  """Flatten a nested tree of queues into a sequence of `(path, queue)` pairs"""
  for id, q in queues.items():
    if isinstance(q, dict):
      yield from flatten_queues(q, prefix + (id,)) # type: ignore
    elif isinstance(q, ReadQueue):
      yield prefix + (id,), q