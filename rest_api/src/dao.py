from config import log_format, log_level, DbTypeEnum
import logging
from peewee import *
from config import DB_NAME, DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_TYPE, CREATE_DB_TABLES
from typing import Dict, List, Optional, Any
import sys
from models import CommitterLoc, StatusEnum
from datetime import datetime
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from git import Repo, Commit
from playhouse.mysql_ext import MariaDBConnectorDatabase


logging.basicConfig(format=log_format)
logger = logging.getLogger("db")
logger.setLevel(log_level)

logger.info(f"{DB_TYPE} {DB_HOST} {DB_PORT} {DB_NAME} {DB_USERNAME}")

if DB_TYPE == DbTypeEnum.mariadb.name:
    db = MySQLDatabase(None)
else:
    db = SqliteDatabase(':memory:')


class Committer(Model):
    email = CharField(unique=True)

    class Meta:
        database = db


class Repo(Model):
    repo_url = CharField(unique=True)
    status = CharField(default=StatusEnum.todo.name)
    loc_facts_status = CharField(default=StatusEnum.todo.name)
    commit_feq_facts_status = CharField(default=StatusEnum.todo.name)

    class Meta:
        database = db


class CommitterStatsPerRepo(Model):
    committer = ForeignKeyField(model=Committer)
    repo = ForeignKeyField(model=Repo)
    loc = IntegerField(default=0)
    loc_percentile = FloatField(default=0.0)
    loc_percentage = FloatField(default=0.0)
    consistency_score = FloatField(default=0.0)

    class Meta:
        database = db
        primary_key = CompositeKey('repo', 'committer')


class CommitsPerRepoPerAuthor(Model):
    committer = ForeignKeyField(model=Committer)
    repo = ForeignKeyField(model=Repo)
    commit_id = CharField()
    commit_date = DateTimeField()
    hours_since_last_commit = IntegerField(null=True)
    commit_size = IntegerField()

    class Meta:
        database = db
        primary_key = CompositeKey('repo', 'committer', 'commit_id')


class Requests(Model):
    request_id = CharField(unique=True)
    repo = ForeignKeyField(model=Repo)

    class Meta:
        database = db


def save_committer(email: str):
    committer = Committer(email=email)
    try:
        committer.save(force_insert=False)
    except IntegrityError:
        logger.error(f"Committer {email} already exists in DB.")


def save_repo(repo_url: str):
    repo = Repo(repo_url=repo_url)
    try:
        repo.save(force_insert=False)
    except IntegrityError:
        logger.error(f"Repo {repo_url} already exists in DB.")


def save_request(request_id: str, repo_url: str):
    repo = get_repo_by_url(repo_url)
    try:
        Requests(request_id=request_id, repo=repo).save(force_insert=False)
    except IntegrityError:
        logger.error(f"Request {request_id},{repo.id} already exists in DB.")


def get_repo_by_reqid(request_id: str) -> Optional[Repo]:
    try:
        req = Requests.select(Requests, Repo).join(Repo).where(Requests.request_id == request_id).first()
    except DoesNotExist:
        return None
    if req is None:
        return None
    return req.repo


def get_repo_by_url(repo_url: str) -> Optional[Repo]:
    try:
        return Repo.get(Repo.repo_url == repo_url)
    except DoesNotExist:
        return None


def get_committer(email: str) -> Optional[Committer]:
    try:
        return Committer.get(Committer.email == email)
    except DoesNotExist:
        return None


def update_repo_status(repo: Repo) -> None:
    if repo.loc_facts_status == StatusEnum.todo.name and repo.commit_feq_facts_status == StatusEnum.todo.name:
        repo.update({Repo.status: StatusEnum.todo.name}).execute()
        return
    if (repo.loc_facts_status == StatusEnum.in_progress.name or
            repo.commit_feq_facts_status == StatusEnum.in_progress.name):
        repo.update({Repo.status: StatusEnum.in_progress.name}).execute()
        return
    if (repo.loc_facts_status == StatusEnum.done.name and
            repo.commit_feq_facts_status == StatusEnum.done.name):
        repo.update({Repo.status: StatusEnum.done.name}).execute()
        return
    if (repo.loc_facts_status == StatusEnum.failed.name or
            repo.commit_feq_facts_status == StatusEnum.failed.name):
        repo.update({Repo.status: StatusEnum.failed.name}).execute()
        return
    return


def update_repo_status_by_url(repo_url: str):
    repo = get_repo_by_url(repo_url)
    update_repo_status(repo)


def update_commit_feq_facts_status_for_repo(repo: Repo, status: StatusEnum):
    if ((repo.commit_feq_facts_status == StatusEnum.todo.name and status.name in (
            StatusEnum.in_progress.name, StatusEnum.done.name, StatusEnum.failed.name)) or
        (repo.commit_feq_facts_status == StatusEnum.in_progress.name and status.name in (
            StatusEnum.done.name, StatusEnum.failed.name))):
        repo.update({Repo.commit_feq_facts_status: status.name}).execute()
        update_repo_status_by_url(repo.repo_url)


def update_commit_feq_facts_status_for_repo_url(repo_url: str, status: StatusEnum):
    repo = get_repo_by_url(repo_url)
    update_loc_facts_status_for_repo(repo, status)


def update_loc_facts_status_for_repo(repo: Repo, status: StatusEnum):
    if ((repo.loc_facts_status == StatusEnum.todo.name and status.name in (
            StatusEnum.in_progress.name, StatusEnum.done.name, StatusEnum.failed.name)) or
        (repo.loc_facts_status == StatusEnum.in_progress.name and status.name in (
            StatusEnum.done.name, StatusEnum.failed.name))):
        repo.update({Repo.loc_facts_status: status.name}).execute()
        update_repo_status_by_url(repo.repo_url)


def update_loc_facts_status_for_repo_url(repo_url: str, status: StatusEnum):
    repo = get_repo_by_url(repo_url)
    update_commit_feq_facts_status_for_repo(repo, status)


def save_loc_data_for_repo(repo_url: str, histogram: Dict[str, int]):
    save_repo(repo_url)
    repo: Repo = get_repo_by_url(repo_url)
    assert repo is not None
    max_loc = max(histogram.values())
    total_loc = sum(histogram.values())
    for email, loc in histogram.items():
        if max_loc == -1:
            max_loc = loc
        save_committer(email)
        committer = get_committer(email)
        try:
            loc_in_repo = CommitterStatsPerRepo.insert(committer=committer,
                                                       repo=repo,
                                                       loc=loc,
                                                       loc_percentile=round(loc/max_loc, 2),
                                                       loc_percentage=round(loc/total_loc, 2)).execute()
            # logger.debug(f"save_loc_data_for_repo: saved {loc_in_repo}")
        except Exception as ex:
            logger.error(sys.exc_info())
            logger.error(f"save_loc_data_for_repo: Error during insert!", ex)
    update_loc_facts_status_for_repo(repo, StatusEnum.done)
    logger.debug(f"save_loc_data_for_repo")


def calc_commit_freq_analysis_for_repo(repo: Repo) -> None:
    try:
        query = (CommitsPerRepoPerAuthor.select(Committer.email,
                                                fn.SUM(1 / CommitsPerRepoPerAuthor.hours_since_last_commit).alias('consistency_score'))
                  .join(Repo, JOIN.INNER).switch(CommitsPerRepoPerAuthor).join(Committer, JOIN.INNER)
                  .where(Repo.repo_url == repo.repo_url and
                         CommitsPerRepoPerAuthor.hours_since_last_commit.is_null(False) and
                         CommitsPerRepoPerAuthor.hours_since_last_commit > 0)
                  .group_by(CommitsPerRepoPerAuthor.committer).dicts())
        logger.debug(f"calc_commit_freq_analysis_for_repo: query={query}")
        for r in query:
            committer = get_committer(r['email'])
            if DB_TYPE == DbTypeEnum.mariadb.name:
                committer_stat = (CommitterStatsPerRepo.select().join(Repo).switch(CommitterStatsPerRepo)
                                  .join(Committer).where(Repo.id == repo.id and Committer.id == committer.id).get())
                committer_stat.consistency_score = r['consistency_score']
                committer_stat.save()
            else:
                update_query = (CommitterStatsPerRepo.update(consistency_score=r['consistency_score']).where(
                    (CommitterStatsPerRepo.repo == repo and CommitterStatsPerRepo.committer == committer)))
                num_updated = update_query.execute()
                logger.debug(f"calc_commit_freq_analysis_for_repo: Update query: {update_query} updated {num_updated} rows.")
    except DoesNotExist:
        pass


def get_commit_freq_analysis_for_repo(repo: Repo) -> Dict[str, float]:
    try:
        result = dict()
        query = (CommitterStatsPerRepo.select(Committer.email, CommitterStatsPerRepo.consistency_score)
                 .where(CommitterStatsPerRepo.repo == repo.id).join(Committer).dicts())
        # logger.debug(f"get_commit_freq_analysis_for_repo: query: {query}")
        for record in query:
            result[record['email']] = record['consistency_score']
        return result
    except DoesNotExist:
        return dict()


def get_loc_analysis_for_repo(repo: Repo) -> List[Any]:
    try:
        result = list()
        query = CommitterStatsPerRepo.select().where(CommitterStatsPerRepo.repo == repo.id)
        # logger.debug(f"get_loc_analysis_for_repo: query: {query}")
        for record in query:
            # logger.debug(f"get_loc_analysis_for_repo: record: {record}")
            result = (CommitterStatsPerRepo.select(Committer.email, CommitterStatsPerRepo.loc_percentile,
                                                   CommitterStatsPerRepo.loc, CommitterStatsPerRepo.loc_percentage)
                      .join(Repo, JOIN.INNER).switch(CommitterStatsPerRepo).join(Committer, JOIN.INNER)
                      .where(Repo.repo_url == repo.repo_url)
                      .order_by(CommitterStatsPerRepo.loc_percentile.desc()).namedtuples())
        # logger.debug(f"get_loc_analysis_for_repo: result={result}")
        return result
    except DoesNotExist:
        return list()


def get_loc_analysis_result_by_req_id(request_id: str) -> List[Any]:
    repo = get_repo_by_reqid(request_id)
    logger.debug(f"get_analysis: request_id={request_id} repo={repo.repo_url}")
    return get_loc_analysis_for_repo(repo)


def get_loc_analysis_by_repo_url(repo_url: str) -> List[Any]:
    repo = get_repo_by_url(repo_url)
    return get_loc_analysis_for_repo(repo)


def get_committers_for_repo_url(repo_url: str) -> List[Committer]:
    try:
        committers = (CommitterStatsPerRepo.select(Committer.id, Committer.email)
                      .join(Repo, join_type=JOIN.INNER)
                      .switch(CommitterStatsPerRepo)
                      .join(Committer, join_type=JOIN.INNER)
                      .where(Repo.repo_url == repo_url).namedtuples())
        # logger.debug(f"get_committers_for_repo_url: query={committers}")
        if committers is None or len(committers) == 0:
            return list()
        else:
            return committers
    except DoesNotExist:
        return list()


def extract_commit_freq_stats(repo_url: str, repo: Repo, commits: List[Commit]) -> None:
    repo_orm = get_repo_by_url(repo_url)
    committers = get_committers_for_repo_url(repo_url)
    one_yr_ago = (datetime.now() - relativedelta(years=1)).strftime("%Y-%m-%d")
    committer_lookup = {committer.email: committer.id for committer in committers}
    commit_count_from_git = 0
    for commit in Commit.iter_items(repo=repo, rev=repo.head, since=one_yr_ago):
        if commit.author.email in committer_lookup.keys():
            commit_count_from_git += 1
            try:
                insert = CommitsPerRepoPerAuthor.insert(committer_id=committer_lookup[commit.author.email],
                                                        repo_id=repo_orm.id, commit_id=commit.hexsha,
                                                        commit_date=commit.committed_datetime, commit_size=commit.size)
                insert.execute()
            except IntegrityError:
                logger.info(f"Duplicate insert for {repo_url} {commit.author.email} {commit.hexsha} {commit.committed_datetime}! Moving on.")
            except Exception as ex:
                logger.error(sys.exc_info())
                logger.error(f"Insert failed for commit {repo_url} {commit.author.email} {commit.hexsha} {commit.committed_datetime}! Moving on.", ex)

    if CommitsPerRepoPerAuthor.select().count() < commit_count_from_git:
        logger.error(f"extract_commit_freq_stats: Expected inserts={commit_count_from_git} Actual insert={CommitsPerRepoPerAuthor.select().count()}")
        if CommitsPerRepoPerAuthor.select().count() < commit_count_from_git/2:
            update_commit_feq_facts_status_for_repo(repo_orm, StatusEnum.failed)
            return

    for committer in committers:
        commits = CommitsPerRepoPerAuthor.select().join(Repo).where(
            ((CommitsPerRepoPerAuthor.committer.id == committer.id) and (Repo.repo_url == repo_url))
        ).order_by(CommitsPerRepoPerAuthor.commit_date.desc())
        logger.debug(f"extract_commit_freq_stats: Commits for repo={repo_orm.id} committer={committer.id}: {commits}")
        expected_updates = 0
        for i, commit in enumerate(commits):
            # logger.debug(f"extract_commit_freq_stats: {commit}")
            if i < len(commits)-1:
                expected_updates += 1
                hours_since_last_commit = None
                try:
                    commit_date = parse(commit.commit_date) if type(commit.commit_date) == str else commit.commit_date
                    prev_commit_date = parse(commits[i + 1].commit_date) if type(commits[i + 1].commit_date) == str else commits[i + 1].commit_date
                    hours_since_last_commit = round((commit_date - prev_commit_date).seconds / 3600)

                    # logger.debug(f"extract_commit_freq_stats: {commit.commit_id} calculated hours_since_last_commit={hours_since_last_commit} commit_date={commit_date} type={type(commit.commit_date)} prev_commit_date={prev_commit_date} diff={(commit_date - prev_commit_date).seconds}")
                    if DB_TYPE == DbTypeEnum.mariadb.name:
                        commit.hours_since_last_commit = hours_since_last_commit
                        commit.save()  # Works for MariaDB but not for SQLite!
                    else:
                        # Following works for SQLite but somehow not on MariaDB!
                        update_query = (CommitsPerRepoPerAuthor.update(hours_since_last_commit=hours_since_last_commit)
                                        .where(CommitsPerRepoPerAuthor.commit_id == commit.commit_id))
                        num_updated = update_query.execute()
                        logger.debug(f"extract_commit_freq_stats: update query: {update_query} updated {num_updated} rows.")
                except Exception as ex:
                    # logger.error(sys.exc_info())
                    logger.error(f"Couldn't update hours_since_last_commit={hours_since_last_commit} for {repo_url} {commit.commit_id} {commit.commit_date}! Moving on.", ex)

        actual_updates = CommitsPerRepoPerAuthor.select((CommitsPerRepoPerAuthor.repo.id == repo_orm.id) and
                                                        (CommitsPerRepoPerAuthor.hours_since_last_commit
                                                         .is_null(False))).count()
        logger.debug(f"extract_commit_freq_stats: Expected updates={expected_updates} Actual updates={actual_updates}")
        if actual_updates < expected_updates/2:
            update_commit_feq_facts_status_for_repo(repo_orm, StatusEnum.failed)
            return

    calc_commit_freq_analysis_for_repo(repo_orm)
    update_commit_feq_facts_status_for_repo(repo_orm, StatusEnum.done)
    return


def init_dao():
    if DB_TYPE == DbTypeEnum.mariadb.name:
        db.init(DB_NAME, host=DB_HOST, port=DB_PORT, user=DB_USERNAME, password=DB_PASSWORD)
        logger.info(f"Initiated connection to MariaDB.")
    else:
        logger.info(f"Connected to in-memory SQLite.")
    db.connect(reuse_if_open=True)

    if CREATE_DB_TABLES:
        db.create_tables([Repo, Committer, CommitterStatsPerRepo, Requests, CommitsPerRepoPerAuthor])
        logger.info(f"DB tables created.")

    logger.info(f"DB connection {'closed' if db.is_closed() else 'open'}.")



