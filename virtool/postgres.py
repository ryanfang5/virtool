import logging
import sys
from enum import Enum

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.ext.declarative import declarative_base

import virtool.api.json

logger = logging.getLogger(__name__)

Base = declarative_base()


async def connect(postgres_connection_string: str) -> AsyncEngine:
    """
    Create a connection of Postgres.

    :param postgres_connection_string: the postgres connection string
    :return: an AsyncEngine object

    """
    if not postgres_connection_string.startswith("postgresql+asyncpg://"):
        logger.fatal("Invalid PostgreSQL connection string")
        sys.exit(1)

    try:
        pg = create_async_engine(postgres_connection_string, json_serializer=virtool.api.json.dumps)

        await check_version(pg)
        await create_tables(pg)

        return pg
    except ConnectionRefusedError:
        logger.fatal("Could not connect to PostgreSQL: Connection refused")
        sys.exit(1)


async def check_version(engine: AsyncEngine):
    """
    Check and log the Postgres sever version.

    :param engine: an AsyncConnection object

    """
    async with engine.connect() as conn:
        info = await conn.execute(text('SHOW server_version'))

    version = info.first()[0].split()[0]
    logger.info(f"Found PostgreSQL {version}")


async def create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def to_dict(self):
    row = dict()
    for c in self.__table__.columns:
        column = getattr(self, c.name, None)

        row[c.name] = column if not isinstance(column, Enum) else column.value

    return row


Base.to_dict = to_dict
