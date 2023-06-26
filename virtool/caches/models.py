from sqlalchemy import BigInteger, Column, DateTime, Enum, Integer, String
from sqlalchemy.sql.schema import UniqueConstraint

from virtool.pg.base import Base
from virtool.samples.models import ArtifactType


class SQLSampleArtifactCache(Base):
    """
    SQL model to store a cached sample artifact

    """

    __tablename__ = "sample_artifacts_cache"
    __table_args__ = (UniqueConstraint("key", "name", "sample"),)

    id = Column(Integer, primary_key=True)
    key = Column(String, nullable=False)
    name = Column(String, nullable=False)
    name_on_disk = Column(String)
    sample = Column(String, nullable=False)
    size = Column(BigInteger)
    type = Column(Enum(ArtifactType), nullable=False, create_type=False)
    uploaded_at = Column(DateTime)


class SQLSampleReadsCache(Base):
    """
    SQL model to store cached sample reads files

    """

    __tablename__ = "sample_reads_cache"
    __tableargs__ = (UniqueConstraint("key", "name", "sample"),)

    id = Column(Integer, primary_key=True)
    key = Column(String, nullable=False)
    name = Column(String(length=13), nullable=False)
    name_on_disk = Column(String, nullable=False)
    sample = Column(String, nullable=False)
    size = Column(BigInteger)
    uploaded_at = Column(DateTime)
