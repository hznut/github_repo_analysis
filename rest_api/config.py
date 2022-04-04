import logging
from starlette.config import Config

config = Config(".env")

log_format = "%(asctime)s %(levelname)s:%(name)s: %(message)s"
log_level = logging.DEBUG

BASE_PATH = "/repo-analysis/api"
CHECKOUT_ROOT_DIR = config("CHECKOUT_ROOT_DIR", default="/tmp")
DB_NAME = config("DB_NAME", default="repo_analysis")
DB_HOST = config("DB_HOST", default="localhost")
DB_PORT = int(config("DB_PORT", default=3306))
DB_USERNAME = config("DB_USERNAME", default="root")
DB_PASSWORD = config("DB_PASSWORD", default="example")
DB_TYPE = config("DB_TYPE", default="sqlite")

