from tests.fixtures.authorization import *
from tests.fixtures.client import *
from tests.fixtures.config import *
from tests.fixtures.core import *
from tests.fixtures.data import *
from tests.fixtures.db import *
from tests.fixtures.dispatcher import *
from tests.fixtures.documents import *
from tests.fixtures.fake import *
from tests.fixtures.groups import *
from tests.fixtures.history import *
from tests.fixtures.indexes import *
from tests.fixtures.jobs import *
from tests.fixtures.otus import *
from tests.fixtures.redis import *
from tests.fixtures.references import *
from tests.fixtures.response import *
from tests.fixtures.samples import *
from tests.fixtures.settings import *
from tests.fixtures.setup import *
from tests.fixtures.subtractions import *
from tests.fixtures.tasks import *
from tests.fixtures.uploads import *
from tests.fixtures.users import *

pytest_plugins = [
    "tests.fixtures.migration",
    "tests.fixtures.postgres",
]


def pytest_addoption(parser):
    parser.addoption(
        "--db-connection-string",
        action="store",
        default="mongodb://root:virtool@localhost:27017",
    )

    parser.addoption(
        "--redis-connection-string",
        action="store",
        default="redis://root:virtool@localhost:6379",
    )

    parser.addoption(
        "--postgres-connection-string",
        action="store",
        default="postgresql+asyncpg://virtool:virtool@localhost",
    )
