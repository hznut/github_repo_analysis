from pydantic import BaseModel, Field, validator
from typing import List, Dict
from enum import Enum, auto


class StatusEnum(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name

    todo = auto()
    in_progress = auto()
    done = auto()
    failed = auto()


class Item(BaseModel):
    name: str


class CommitterAnalysisRequest(BaseModel):
    repo_url: str = Field(..., title="Github repo url")
    #
    # @validator('repo_url')
    # def repo_url_format(cls, v):
    #     if v is None or not v.startswith("https://github.com/"):
    #         raise ValueError("repo_url should start with 'https://github.com/'")


class CommitterAnalysisRequestAck(BaseModel):
    request_id: str = Field(None, title='A v4 UUID which was supplied by the caller.')
    status_url: str = Field(..., title="URL which caller can keep polling to check status of provisioning.")


class CommitterLoc(BaseModel):
    email: str
    loc_percentile: float = Field(None, title="Committer's loc percentile.")
    loc_percentage: float = Field(None, title="Committer's loc percentage.")
    loc: int = Field(None, title="Committer's loc.")


class RepoAnalysisRequest(BaseModel):
    request_id: str
    repo_url: str


class RepoAnalysisResult(BaseModel):
    repo_url: str
    status: str
    loc_analysis: Dict[str, CommitterLoc] = dict()
    commit_freq_analysis: Dict[str, float] = dict()

