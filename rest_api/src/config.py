import logging
from starlette.config import Config
from enum import Enum


class EnvironmentEnum(str, Enum):
    default = "default"
    local = "local"
    dev = "dev"
    test = "tests"
    preprod = "preprod"
    prod = "prod"


config = Config(".env")


def load_log_level():
    s = config("LOG_LEVEL", default='DEBUG')
    m = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARN': logging.WARN,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'FATAL': logging.FATAL,
        'CRITICAL': logging.CRITICAL
    }
    return m.get(s, logging.INFO)


log_format = "%(asctime)s %(levelname)s:%(name)s: %(message)s"
log_level = load_log_level()

BASE_PATH = "/repo-analysis/api"
environment = config("environment", default=EnvironmentEnum.dev)
CHECKOUT_ROOT_DIR = config("CHECKOUT_ROOT_DIR", default="/tmp")
DB_NAME = config("DB_NAME", default="repo_analysis")
DB_HOST = config("DB_HOST", default="localhost")
DB_PORT = int(config("DB_PORT", cast=int, default=3306))
DB_USERNAME = config("DB_USERNAME", default="root")
DB_PASSWORD = config("DB_PASSWORD", default="example")
DB_TYPE = config("DB_TYPE", default="sqlite")
CREATE_DB_TABLES = config("CREATE_DB_TABLES", cast=bool, default=False)
