import docker
from docker.models.resource import Model
from docker.models.containers import Container
import json
import os
import pytest
import random
from starlette.config import Environ
from starlette.testclient import TestClient
import socket
import asyncio
from peewee import *
import subprocess
import shlex

docker_client = docker.from_env()
db_container: Container = None
api_container: Container = None
db_port = None
api_port = None


@pytest.fixture(scope="session", autouse=True)
def set_environ() -> Environ:
    # Configure environment settings prior to importing app
    environ = Environ()
    environ['environment'] = 'local'
    environ['DB_HOST'] = 'db'
    environ['DB_PORT'] = '3306'
    environ['DB_NAME'] = 'repo_analysis'
    environ['DB_USERNAME'] = 'root'
    environ['DB_PASSWORD'] = 'example'
    environ['DB_TYPE'] = 'mariadb'
    environ['CHECKOUT_ROOT_DIR'] = '/tmp'
    environ['TABLE_NAMES'] = f"{'CommitterStatsPerRepo'.lower()},{'CommitsPerRepoPerAuthor'.lower()},requests,repo,committer"
    # environ['CREATE_DB_TABLES'] = 'true'
    print("Environment variables set.")
    return environ


def next_free_port(start_port=1024, max_port=65535):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port = start_port
    while port <= max_port:
        try:
            sock.bind(('', port))
            sock.close()
            return port
        except OSError:
            port += 1
    raise IOError('no free ports')


@pytest.fixture(scope="session", autouse=True)
def docker_compose_up():
    # docker compose ls | grep github_repo_analysis
    compose_ls = subprocess.Popen(shlex.split("docker compose ls"), stdout=subprocess.PIPE)
    grep = subprocess.run(shlex.split("grep github_repo_analysis"), stdin=compose_ls.stdout)
    if grep.returncode == 0:  # already running
        print("Containers already running.")
    else:
        pwd = os.path.dirname(os.path.realpath(__file__))
        process = subprocess.run(shlex.split("make run"), cwd=f"{pwd}/../..")
        print(process)


def docker_compose_down():
    pwd = os.path.dirname(os.path.realpath(__file__))
    process = subprocess.run(shlex.split("make stop"), cwd=f"{pwd}/../..")
    print(process)


def db_connect(environ):
    host = 'localhost'
    port = environ['DB_PORT']
    username = environ['DB_USERNAME']
    password = environ['DB_PASSWORD']
    db_name = environ['DB_NAME']
    db = MySQLDatabase(None)
    db.init(db_name, host=host, port=int(port), user=username, password=password)
    db.connect(reuse_if_open=True)
    print(f"conftest: DB connection {'closed' if db.is_closed() else 'open'}.")
    return db


@pytest.fixture(scope="module", autouse=True)
def setup(set_environ):
    pass


@pytest.fixture(scope="session", autouse=True)
def session_cleanup(request):
    request.addfinalizer(docker_compose_down)


@pytest.fixture(scope="module")
def dao(setup):
    import dao
    dao.init_dao()
    return dao


@pytest.fixture(scope="module")
def repo_analyzer(set_environ):
    environ = set_environ
    environ['DB_HOST'] = 'localhost'
    environ['CREATE_DB_TABLES'] = 'false'
    import repo_analyzer
    asyncio.run(repo_analyzer.repo_analyzer_init())
    return repo_analyzer


@pytest.fixture(scope="module")
def db(set_environ):
    environ = set_environ
    db = MySQLDatabase(None) if environ['DB_TYPE'] == 'mariadb' else SqliteDatabase(None)
    return db


@pytest.fixture(scope="module")
def url_base_path(setup):
    # We want the fixture 'setup' to be called before config gets loaded (directly or indirectly via import
    # statements). Hence it's important to supply thee following as a fixture rather than importing it directly in the
    # tests. In other words we don't want to put these imports directly in the tests files.
    from config import BASE_PATH
    return BASE_PATH


@pytest.fixture(scope="module")
def api_base_path(setup):
    # We want the fixture 'setup' to be called before config gets loaded (directly or indirectly via import
    # statements). Hence it's important to supply thee following as a fixture rather than importing it directly in the
    # tests. In other words we don't want to put these imports directly in the tests files.
    from config import BASE_PATH
    return f"http://localhost:80/{BASE_PATH}"


@pytest.fixture(scope="module")
def db_connection(set_environ):
    environ = set_environ
    db = db_connect(environ)
    return db


@pytest.fixture(scope="module")
def empty_db_tables(set_environ, db_connection):
    environ = set_environ
    db = db_connection
    table_names = environ['TABLE_NAMES'].split(',')
    for table_name in table_names:
        db.execute_sql(f"delete from {table_name}")
    print(f"Tables emptied.")
    db.close()
