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
    environ['environment'] = 'tests'
    environ['DB_HOST'] = 'db'
    environ['DB_NAME'] = 'repo_analysis'
    environ['DB_USERNAME'] = 'root'
    environ['DB_PASSWORD'] = 'example'
    environ['DB_TYPE'] = 'mariadb'
    environ['CHECKOUT_ROOT_DIR'] = '/tmp'
    environ['TABLE_NAMES'] = f"{'CommitterStatsPerRepo'.lower()},{'CommitsPerRepoPerAuthor'.lower()},requests,repo,committer"
    environ['CREATE_DB_TABLES'] = 'true'
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
def docker_compose_up(set_environ):
    pwd = os.path.dirname(os.path.realpath(__file__))
    process = subprocess.run(shlex.split("make run"), cwd=f"{pwd}/../..")
    # process = subprocess.run(shlex.split("docker compose --env-file ../local.env up -d --build --wait --quiet-pull"),
    #                          cwd=f"{pwd}/..")
    print(process)


def docker_compose_down():
    pwd = os.path.dirname(os.path.realpath(__file__))
    process = subprocess.run(shlex.split("make stop"), cwd=f"{pwd}/../..")
    # process = subprocess.run(shlex.split("docker compose down"), cwd=f"{pwd}/..")
    print(process)


@pytest.fixture(scope="session", autouse=False)
def start_db_local(set_environ) -> (Model, str):
    environ = set_environ
    global db_container
    port = next_free_port(start_port=3306)
    try:
        containers = docker_client.containers.list(filters={'ancestor': 'mariadb'})
    except Exception as e:
        print(e)
        raise e
    for running_container in containers:
        if running_container.name.startswith('repo-analysis-db-tests'):
            running_container.stop()
            running_container.remove()
            print(f"Stopped mariadb container {running_container.short_id}")
    try:
        pwd = os.path.dirname(os.path.realpath(__file__))
        print(f"pwd={pwd}")
        volume_mapping = [f"{pwd}/../schema.sql:/docker-entrypoint-initdb.d/dump.sql"]
        db_container = docker_client.containers.run(image='mariadb',
                                                    # command="",
                                                    detach=True,
                                                    ports={'3306/tcp': port},
                                                    name=f"repo-analysis-db-tests-{random.randint(100, 999)}",
                                                    # volumes=volume_mapping,
                                                    environment={"MARIADB_ROOT_PASSWORD": environ['DB_PASSWORD']},
                                                    stderr=True,
                                                    stdout=True
                                                    )
        print(db_container.logs())
        # print(db_container.wait())
    except Exception as e:
        print(e)
        raise e
    print(f"Started mariadb container name={db_container.name} short_id={db_container.short_id} accessible on localhost port {port}")
    environ['DB_PORT'] = str(port)
    print(f"DB_PORT={environ['DB_PORT']}")
    global db_port
    db_port = port
    return db_container, port


@pytest.fixture(scope="session", autouse=False)
def start_api_container(set_environ, start_db_local) -> (Model, str):
    environ = set_environ
    global api_container
    port = next_free_port(start_port=9000)
    try:
        containers = docker_client.containers.list(filters={'ancestor': 'python:3.9'})
    except Exception as e:
        print(e)
        raise e
    for running_container in containers:
        if running_container.name.startswith('repo-analysis-rest-api-tests'):
            running_container.stop()
            running_container.remove()
            print(f"Stopped rest-api container {running_container.short_id}")
    try:
        env_vars = {
            "DB_HOST": "db",
            "DB_PORT": environ["DB_PORT"],
            "DB_USERNAME": environ["DB_USERNAME"],
            "DB_PASSWORD": environ["DB_PASSWORD"],
            "DB_NAME": environ["DB_NAME"],
            "DB_TYPE": environ["DB_TYPE"],
            "CREATE_DB_TABLES": environ["CREATE_DB_TABLES"],
            "CHECKOUT_ROOT_DIR": environ["CHECKOUT_ROOT_DIR"]
        }
        api_container = docker_client.containers.run(image='repo-analysis-rest-api',
                                                    # command="",
                                                    detach=True,
                                                    ports={"80": port},
                                                    name=f"repo-analysis-rest-api-tests-{random.randint(100, 999)}",
                                                    environment=env_vars,
                                                    stderr=True,
                                                    stdout=True,
                                                    links={db_container.name: "db"}
                                                    )
        print(api_container.logs())
        # print(api_container.wait())
    except Exception as e:
        print(e)
        raise e
    print(f"Started rest-api container name={api_container.name} short_id={api_container.short_id} accessible on localhost port {port}")
    global api_port
    api_port = port
    return api_container, port


def db_connect(environ):
    host = environ['DB_HOST']
    port = environ['DB_PORT']
    username = environ['DB_USERNAME']
    password = environ['DB_PASSWORD']
    db_name = environ['DB_NAME']
    if environ['DB_TYPE'] == 'mariadb':
        db = MySQLDatabase(None)
        db.init(db_name, host=host, port=int(port), user=username, password=password)
    else:
        db = SqliteDatabase(':memory:')
        db.connect(reuse_if_open=True)

    return db


def empty_db_tables(environ):
    db = db_connect(environ)
    table_names = environ['TABLE_NAMES'].split(',')
    for table_name in table_names:
        db.execute_sql(f"delete from {table_name}")
        print(f"Table {table_name} emptied.")
    # db.close()


def destroy_db():
    """
    In case of failure rerun after commenting out call to this method so that
    you can connect to mariadb using adminer.
    Eg. For accessing adminer on http://localhost:8080 to connect to mariadb:
    > docker run --link repo-analysis-db-tests:db -p 8080:8080 adminer
    """
    if db_container is not None:
        db_container.stop()
        db_container.remove()
        print(f"\nStopped mariadb container name={db_container.name} short_id={db_container.short_id}")


@pytest.fixture(scope="module", autouse=True)
def setup(set_environ):
    pass


@pytest.fixture(scope="session", autouse=True)
def session_cleanup(request):
    request.addfinalizer(docker_compose_down)


@pytest.fixture(scope="module")
def app(set_environ):
    environ = set_environ
    from main import app
    yield app
    # empty_db_tables(environ)


@pytest.fixture(scope="module")
def dao(setup):
    import dao
    dao.init_dao()
    return dao


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
def load_data(set_environ):
    environ = set_environ
    db = db_connect(environ)
    db.execute_sql(f"insert into repo values(repo_url='https://github.com/apache/kafka');")
    db.close()
