from typing import Any, Generic, Sequence, TypeVar
from pipeteer import Pipeline, trees, GetQueue, WriteQueue

A = TypeVar('A')
B = TypeVar('B')
Q = TypeVar('Q')
P = TypeVar('P')
T = TypeVar('T')

class Sequential(Pipeline[A, B, Sequence[Q], Sequence[P], Sequence[T]], Generic[A, B, Q, P, T]):
  """Sequential composition of pipelines, with a few caveats
  - The tree of queues is a list of the pipeline queues in the given order
  - The expected parameters are a list of each pipeline's parameters. There must be exactly one per pipeline
  """
  def __init__(self, pipelines: Sequence[Pipeline[Any, Any, Q, P, T]]):
    assert len(pipelines) > 0, "Sequential pipelines must have at least one pipeline"
    self.pipelines = pipelines
    self.Tin = pipelines[0].Tin
    self.Tout = pipelines[-1].Tout

  def tree(self) -> trees.Tree[Pipeline]:
    return [p.tree() for p in self.pipelines]
  
  def connect(self, Qout: WriteQueue[B], get_queue: GetQueue, params: Sequence[P], *, prefix: tuple[str|int, ...] = ()):
    queues = []
    output = Qout
    params = params or [None] * len(self.pipelines) # type: ignore
    for i, (pipe, ps) in reversed(list(enumerate(zip(self.pipelines, params)))):
      i_prefix = prefix + (i,)
      queues.append(pipe.connect(output, get_queue, ps, prefix=i_prefix))
      output = pipe.push_queue(get_queue, ps, prefix=i_prefix)
    return list(reversed(queues))

  def push_queue(self, get_queue: GetQueue, params: Sequence[P], *, prefix: tuple[str|int, ...] = ()) -> WriteQueue[A]:
    return self.pipelines[0].push_queue(get_queue, params[0], prefix=prefix + (0,))
  
  def run(self, queues: Sequence[Q], params: Sequence[P] = None): # type: ignore
    params = params or [None] * len(self.pipelines) # type: ignore
    return [pipe.run(Qs, ps) for pipe, ps, Qs in zip(self.pipelines, params, queues)]
  