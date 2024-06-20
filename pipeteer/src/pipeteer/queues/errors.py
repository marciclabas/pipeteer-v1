from typing_extensions import Literal, Any
from dataclasses import dataclass

@dataclass(eq=False)
class QueueError(BaseException):
  detail: Any | None = None
  reason: Literal['queue-error'] = 'queue-error'

  def __str__(self) -> str:
    return self.__repr__()

@dataclass(eq=False)
class InexistentItem(BaseException):
  key: str | None = None
  detail: Any | None = None
  reason: Literal['inexistent-item'] = 'inexistent-item'

  def __str__(self) -> str:
    return self.__repr__()
  
ReadError = QueueError | InexistentItem