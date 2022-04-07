from fastapi import FastAPI, APIRouter, Request, Query, Path, HTTPException, status, Query
from config import log_format, log_level, BASE_PATH, REPO_URL_REGEX
from mangum import Mangum
from models import RepoAnalysisResult, CommitterAnalysisRequest, CommitterAnalysisRequestAck, StatusEnum
import repo_analyzer
from uuid import UUID
import uuid
import logging
import sys
import traceback
from typing import Any, List
from exceptions import RepoNotFoundException, AppError, GithubUnreachableException

logging.basicConfig(format=log_format)
logger = logging.getLogger("main")
logger.setLevel(log_level)

app = FastAPI(
    title="Github Repo Analysis",
    # if not custom domain
    openapi_url=f"{BASE_PATH}/openapi.json",
    docs_url=f"{BASE_PATH}/docs",
    redoc_url=f"{BASE_PATH}/redoc",
    on_startup=[repo_analyzer.repo_analyzer_init]
)

router = APIRouter()


@router.get("/status")
def health():
    return {"status": "up"}


async def analyze_repo(repo_url: str) -> UUID:
    request_id = uuid.uuid4()
    logger.debug(f"request_id={request_id} repo_url={repo_url}")
    await repo_analyzer.handle_request(str(request_id), repo_url)
    return request_id


@router.get("/analysis")
async def get_analysis(request: Request,
                       repo_url: str = Query(None,
                                             description='Github repo url of the format '
                                                         'https://github.com/<owner>/<repo> without the .git suffix.',
                                             regex=REPO_URL_REGEX),
                       ) -> RepoAnalysisResult:
    """
    Single endpoint which gives back the analysis for a repo. If it's the analysis is not available then kicks it off
    so that upon successive retries it'll eventually return the analysis. So instead of calling POST /analyze followed
    by multiple calls to GET /analysis/{request_id}, just keep calling this endpoint i.e. GET /analysis?{repo_url}

    :param request:
    :param repo_url: Query parameter
    :return: The analysis of the repo.
    """
    try:
        result = repo_analyzer.get_analysis_by_repo_url(repo_url)
        if result is None or result.status == StatusEnum.todo.name:
            await analyze_repo(repo_url)
        return result
    except RepoNotFoundException as ex:
        message = f"{repo_url} doesn't look like a valid github.com repo."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
    except GithubUnreachableException as ex:
        message = f"Having problem reaching {repo_url}. Retry after about a minute."
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=message)
    except AppError as ex:
        message = "Something blew up internally. Retry after some time. If the error persists then someone needs to look into it."
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)
    except Exception as ex:
        logger.error(sys.exc_info(), ex)
        logger.error(traceback.print_stack())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


app.include_router(router, prefix=BASE_PATH)


def handler(event, context):
    # Insert the base path to event["path"] string when it's not included
    # Addresses the scenario when the lambda is triggered from the APIs stage url.  The base path (stage name)
    # is not included as part of the event["path"] string - therefore Magnum/FastAPI is not able to map
    # to a known API.
    path = event["path"]
    event["path"] = path if path.startswith(f"{BASE_PATH}") else f"{BASE_PATH}{path}"
    magnum_handler = Mangum(app)
    return magnum_handler(event, context)
