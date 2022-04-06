from github3 import login, GitHub
import github3
from git import Repo, Commit, RefLog
from git.cmd import Git
import os
import shutil
import asyncio
from typing import List, Tuple, Dict, Optional, Any
from threading import Lock
from pprint import pprint, pformat, PrettyPrinter
from config import log_format, log_level, CHECKOUT_ROOT_DIR, REPO_URL_REGEX
import logging
import re
from models import RepoAnalysisResult, CommitterLoc, RepoAnalysisRequest, StatusEnum
import dao
from datetime import datetime
from dateutil.relativedelta import relativedelta
import sys
from exceptions import RepoNotFoundException, AppError


logging.basicConfig(format=log_format)
logger = logging.getLogger("repo_analyzer")
logger.setLevel(log_level)

pp = PrettyPrinter(sort_dicts=False)

anon_gh = GitHub()
histogram_lock = Lock()
queue = asyncio.Queue[RepoAnalysisRequest]()


def extract_owner_repo(repo_url: str) -> (str, str):
    """
    Utility method to extract owner and repo from url of the format
    https://github.com/<owner>/<repo>

    :param repo_url:
    :return: Tuple (owner, repo)
    """
    groups = re.match(REPO_URL_REGEX, repo_url).groups()
    assert len(groups) == 2
    return groups[0], groups[1]


def repo_exists(repo_url: str) -> bool:
    owner, repo_name = extract_owner_repo(repo_url)
    try:
        return anon_gh.repository(owner, repo_name) is not None
    except github3.exceptions.NotFoundError as ex:
        return False
    except Exception as ex:
        message = f"Unable to determine if repo {repo_url} exists on github.com"
        logger.error(message, ex)
        raise AppError(message)


async def blame_file(repo: Repo, file: str, histogram: Dict[str, int]) -> None:
    """
    Git blames a single file to get it's commit history and collect loc per author.

    :param repo:
    :param file:
    :param histogram: Dict of loc per committer. The method fills more data into it.
    :return:
    """
    try:
        loop = asyncio.get_running_loop()
        blame_result: List[Tuple[Commit, List[str]]] = await loop.run_in_executor(None, repo.blame, repo.head, file)
        for commit, lines in blame_result:
            with histogram_lock:
                if commit.author.email in histogram.keys():
                    histogram[commit.author.email] += len(lines)
                else:
                    histogram[commit.author.email] = len(lines)
    except Exception as ex:
        logger.error(f"Error while git blame <file>", ex)
        

async def blame_files(repo_url: str, repo: Repo, files: List[str]) -> None:
    """
    Loop through all files and spawn concurrent tasks for doing git blame on the files. Then waits till all threads
    are done. The data is then saved to DB.

    :param repo_url:
    :param repo:
    :param files:
    :return:
    """
    futures = []
    histogram: Dict[str, int] = dict()
    for f in files:
        future = asyncio.ensure_future(blame_file(repo, f, histogram))
        futures.append(future)
    await asyncio.gather(*futures)
    histogram = dict(sorted(histogram.items(), key=lambda item: item[1], reverse=True))
    dao.save_loc_data_for_repo(repo_url, histogram)
    dao.update_loc_facts_status_for_repo_url(repo_url, StatusEnum.done)
    logger.debug(pp.pformat(histogram))


async def handle_request(request_id: str, repo_url: str) -> None:
    req = RepoAnalysisRequest(request_id=request_id, repo_url=repo_url)
    await queue.put(req)
    logger.debug(f"Enqued {req}")


def get_commit_freq_analysis_by_repo(repo: dao.Repo, result: RepoAnalysisResult) -> Optional[RepoAnalysisResult]:
    """
    Checks the DB if the necessary raw data (i.e. facts) for the repo are available. If yes then runs the query to
    extract the dimensions (i.e. stats) related to commit frequency per committer.

    :param repo:
    :param result:
    :return:
    """
    if not repo or repo is None:
        return None
    result.status = repo.status

    if repo.commit_feq_facts_status == StatusEnum.done.name:
        result.commit_freq_analysis = dao.get_commit_freq_analysis_for_repo(repo)
    return result


def get_loc_analysis_by_repo(repo: dao.Repo) -> Optional[RepoAnalysisResult]:
    """
    Checks the DB if the necessary raw data (i.e. facts) for the repo are available. If yes then runs the query to
    extract the dimensions (i.e. stats) related to loc per committer.

    :param repo:
    :return:
    """
    if not repo or repo is None:
        return None
    result = RepoAnalysisResult(status=repo.status)
    if repo.loc_facts_status == StatusEnum.done.name:
        query_results: List[Any] = dao.get_loc_analysis_for_repo(repo)
        for result_row in query_results:
            # logger.debug(f"loc_in_repo={result_row}")
            result.loc_analysis[result_row.email] = CommitterLoc(email=result_row.email, loc=result_row.loc,
                                                                 loc_percentile=result_row.loc_percentile,
                                                                 loc_percentage=result_row.loc_percentage)
    return result


def get_analysis_by_repo(repo: dao.Repo) -> Optional[RepoAnalysisResult]:
    result = get_loc_analysis_by_repo(repo)
    get_commit_freq_analysis_by_repo(repo, result)
    return result


def get_analysis_by_request_id(request_id: str) -> Optional[RepoAnalysisResult]:
    repo = dao.get_repo_by_reqid(request_id)
    return get_analysis_by_repo(repo)


def get_analysis_by_repo_url(repo_url: str) -> Optional[RepoAnalysisResult]:
    if repo_exists(repo_url):
        repo, _ = dao.Repo.get_or_create(repo_url=repo_url)
        if repo is None:
            return None
        return get_analysis_by_repo(repo)
    else:
        raise RepoNotFoundException(f"Couldn't find {repo_url} on github.com")


async def extract_loc_stats(repo_url: str, repo: Repo, files: List[str]) -> None:
    await blame_files(repo_url, repo, files)


def extract_comit_freq_stats(repo_url: str, repo: Repo, files: List[str]) -> None:
    one_yr_ago = (datetime.now() - relativedelta(years=1)).strftime("%Y-%m-%d")
    commits = Commit.iter_items(repo=repo, rev=repo.head, since=one_yr_ago)
    dao.extract_commit_freq_stats(repo_url, repo, commits)


async def analyze_repo(repo_url: str) -> None:
    dao.update_loc_facts_status_for_repo_url(repo_url, StatusEnum.in_progress)
    dao.update_commit_feq_facts_status_for_repo_url(repo_url, StatusEnum.in_progress)
    owner, repo_name = extract_owner_repo(repo_url)
    checkout_dir = os.path.join(CHECKOUT_ROOT_DIR, owner, repo_name)
    if not os.path.isdir(checkout_dir):
        try:
            repo = Repo.clone_from(url=f"{repo_url}.git", to_path=checkout_dir)
        except Exception as ex:
            logger.error(sys.exc_info())
            logger.error(f"git clone failed!", ex)
            raise ex
        logger.info(f"Checked out {repo_url} to {checkout_dir}")
    else:
        repo = Repo(path=f"{checkout_dir}/.git")

    local_git_working_dir = Git(working_dir=checkout_dir)
    files_str: str = local_git_working_dir.ls_files()
    if files_str:
        files = files_str.split('\n')
        logger.info(f"{len(files)} files to analyze..")
        await extract_loc_stats(repo_url, repo, files)
        extract_comit_freq_stats(repo_url, repo, files)
    shutil.rmtree(checkout_dir)
    if os.path.isdir(checkout_dir):
        os.rmdir(path=checkout_dir)
    logger.debug(f"Deleted {checkout_dir}")


async def process_requests():
    logger.debug("process_requests started")
    while True:
        req: RepoAnalysisRequest = await queue.get()
        logger.debug(f"Picked up {req} for processing.")
        dao.save_repo(req.repo_url)
        dao.save_request(req.request_id, req.repo_url)
        await analyze_repo(req.repo_url)


async def repo_analyzer_init():
    dao.init_dao()
    asyncio.create_task(process_requests())
