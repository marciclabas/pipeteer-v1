from typing import TypeVar, Mapping, Sequence, Iterable
from haskellian import iter as I

T = TypeVar('T')
Tree = T | Mapping[str, 'Tree[T]']

@I.lift
def flatten(tree: Tree[T], prefix: tuple[str, ...] = ()) -> Iterable[tuple[Sequence[str], T]]:
  if isinstance(tree, Mapping):
    for k, v in tree.items():
      yield from flatten(v, prefix + (k,))
  else:
    yield prefix, tree