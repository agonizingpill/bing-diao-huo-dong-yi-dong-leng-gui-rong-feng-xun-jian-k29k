from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Code = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]

class ScoreSeam(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sample: Text


class RecordSeam(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Text
    token: Text


class RecordRecheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Text
    sample: Text
    verdict: Literal['确需换格', '无需换格']


class DraftVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Code
    neighbors: Annotated[int, Field(ge=1, le=12)]


class RunTrial(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Code


class RecordTrial(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Text
    token: Text


class EnableVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Code
