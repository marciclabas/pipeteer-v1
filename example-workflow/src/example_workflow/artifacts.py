from typing_extensions import Coroutine, Mapping
from dataclasses import dataclass
from fastapi import FastAPI
from pipeteer import PipelineQueues
from dslog import Logger
from .pipelines import validation_api, manual_api, autocorrection

@dataclass
class Artifacts:
  validation_api: FastAPI
  manual_api: FastAPI
  auto_correct: Coroutine

  @staticmethod
  def of(queues: Mapping[str, PipelineQueues], *, logger: Logger = Logger.click()):
    return Artifacts(
      validation_api=validation_api(**queues['validation'], logger=logger.prefix('[VALIDATION]')),
      manual_api=manual_api(**queues['manual-correct'], logger=logger.prefix('[MANUAL CORRECTION]')),
      auto_correct=autocorrection(**queues['auto-correct'], logger=logger.prefix('[AUTO CORRECTION]')),
    )