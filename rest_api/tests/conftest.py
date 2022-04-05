import docker
from docker.models.resource import Model
import json
import os
import pytest
import random
from starlette.config import Environ
from starlette.testclient import TestClient
import socket
import asyncio
from peewee import *

docker_client = docker.from_env()
db_container = None


@pytest.fixture(scope="session", autouse=True)
def set_environ() -> Environ:
    # Configure environment settings prior to importing app
    environ = Environ()
    environ['environment'] = 'tests'
    environ['DB_HOST'] = 'localhost'
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
        volume_mapping = {f"{pwd}/schema.sql": '/docker-entrypoint-initdb.d/dump.sql'}
        db_container = docker_client.containers.run(image='mariadb',
                                                    # command="",
                                                    detach=True,
                                                    ports={'3306/tcp': port},
                                                    name=f"repo-analysis-db-tests-{random.randint(100, 999)}"#,
                                                    # volume=volume_mapping,
                                                    # env={"MARIADB_ROOT_PASSWORD": "tests"}
                                                    )
    except Exception as e:
        print(e)
        raise e
    print(f"Started mariadb container name={db_container.name} short_id={db_container.short_id} on port {port}")
    environ['DB_PORT'] = str(port)
    print(f"DB_PORT={environ['DB_PORT']}")
    return db_container, port


# @pytest.fixture(scope="module", autouse=True)
# def create_db_table(set_environ):
#     environ = set_environ
#     print(f"Table {table_name} created.")


def delete_db_tables():
    environ = Environ()
    table_names = environ['TABLE_NAMES'].split(',')
    host = environ['DB_HOST']
    port = environ['DB_PORT']
    username = environ['DB_USERNAME']
    password = environ['DB_PASSWORD']
    db_name = environ['DB_NAME']
    db = MySQLDatabase(None)
    db.init(db_name, host=host, port=port, user=username, password=password)
    for table_name in table_names:
        db.execute_sql(f"delete from {table_name}")
        print(f"Table {table_name} emptied.")
    db.close()


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
    request.addfinalizer(destroy_db)


@pytest.fixture(scope="module")
def client(setup, request):
    """
    Make a 'client' fixture available to tests cases.
    """
    print(f"module: {request.node.nodeid}")
    from main import app
    with TestClient(app=app) as test_client:
        # test_client.get_io_loop = asyncio.get_event_loop
        yield test_client
    delete_db_tables()


@pytest.fixture(scope="module")
def url_base_path(setup):
    # We want the fixture 'setup' to be called before config gets loaded (directly or indirectly via import
    # statements). Hence it's important to supply thee following as a fixture rather than importing it directly in the
    # tests. In other words we don't want to put these imports directly in the tests files.
    from config import BASE_PATH
    return BASE_PATH


