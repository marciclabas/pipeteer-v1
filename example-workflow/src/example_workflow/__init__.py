"""
### Example Workflow
> Example workflow using pipeteer
"""
from .pipelines import autocorrection, manual_api, validation_api
from .artifacts import Artifacts
from .flow import workflow, Input, Output