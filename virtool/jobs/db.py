"""
Constants and utility functions for interacting with the jobs collection in the
application database.

"""
from virtool_core.models.user import UserNested

from virtool.mongo.transforms import apply_transforms
from virtool.users.db import AttachUserTransform
from virtool.utils import base_processor
from virtool_core.models.job import JobStatus

OR_COMPLETE = [{"status.state": "complete"}]

OR_FAILED = [{"status.state": "error"}, {"status.state": "cancelled"}]

#: A projection for minimal representations of jobs suitable for search results.
LIST_PROJECTION = [
    "_id",
    "archived",
    "workflow",
    "status",
    "proc",
    "mem",
    "rights",
    "user",
]

#: A projection for full job details. Excludes the secure key field.
PROJECTION = {"key": False}


async def processor(db, document: dict) -> dict:
    """
    The default document processor for job documents.

    Transforms projected job documents to a structure that can be dispatches to clients.

    1. Removes the ``status`` and ``args`` fields from the job document.
    2. Adds a ``username`` field.
    3. Adds a ``created_at`` date taken from the first status entry in the job document.
    4. Adds ``state`` and ``progress`` fields derived from the most recent ``status``
       entry in the job document.

    :param db: the application database object
    :param document: a document to process
    :return: a processed document

    """
    status = document["status"]

    last_update = status[-1]

    return await apply_transforms(
        base_processor(
            {
                **document,
                "state": last_update["state"],
                "stage": last_update["stage"],
                "created_at": status[0]["timestamp"],
                "progress": status[-1]["progress"],
            }
        ),
        [AttachUserTransform(db)],
    )


async def fetch_complete_job(db, document):
    document = await processor(db, document)
    document["user"] = UserNested(**document["user"])
    document["status"] = [JobStatus(**status) for status in document["status"]]
    return document
