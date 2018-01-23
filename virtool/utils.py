import arrow
import datetime
import os
import pymongo
import shutil
import sys

from random import choice
from string import ascii_letters, ascii_lowercase, digits


def base_processor(document):
    document = dict(document)
    document["id"] = document.pop("_id")

    return document


async def get_client_path():
    for client_path in [os.path.join(sys.path[0], "client"), os.path.join(sys.path[0], "client", "dist")]:
        if os.path.exists(os.path.join(client_path, "index.html")):
            return client_path


def rm(path, recursive=False):
    """
    A function that removes files or directories in a separate thread. Wraps :func:`os.remove` and func:`shutil.rmtree`.

    :param path: the path to remove.
    :type path: str

    :param recursive: the operation should recursively descend into dirs.
    :type recursive: bool

    :return: a Tornado future.
    :rtype: :class:`tornado.concurrent.Future`

    """
    try:
        os.remove(path)
        return True
    except IsADirectoryError:
        if recursive:
            shutil.rmtree(path)
            return True

        raise


def file_stats(path):
    stats = os.stat(path)

    # Append file entry to reply list
    return {
        "size": stats.st_size,
        "modify": arrow.get(stats.st_mtime).datetime
    }


def timestamp():
    """
    Returns a datetime object representing the current UTC time. The last 3 digits of the microsecond frame are set
    to zero.

    :return: a UTC timestamp
    :rtype: datetime.datetime

    """
    # Get tz-aware datetime object.
    dt = arrow.utcnow().naive

    # Set the last three ms digits to 0.
    dt = dt.replace(microsecond=int(str(dt.microsecond)[0:3] + "000"))

    return dt


def random_alphanumeric(length=6, mixed_case=False, excluded=None):
    """
    Generates a random string composed of letters and numbers.

    :param length: the length of the string.
    :type length: int

    :param mixed_case: included alpha characters will be mixed case instead of lowercase
    :type mixed_case: bool

    :param excluded: strings that may not be returned.
    :type excluded: Union[list, set]

    :return: a random alphanumeric string.
    :rtype: string

    """
    excluded = excluded or list()

    characters = digits + ascii_letters if mixed_case else ascii_lowercase

    candidate = "".join([choice(characters) for i in range(length)])

    if candidate not in excluded:
        return candidate

    return random_alphanumeric(length, excluded)


def average_list(list1, list2):
    if not isinstance(list1, list) or not isinstance(list2, list):
        raise TypeError("Both arguments must be lists")

    if len(list1) != len(list2):
        raise TypeError("Both arguments must be lists of the same length")

    return [(value + list2[i]) / 2 for i, value in enumerate(list1)]


async def get_new_id(collection, excluded=None):
    """
    Returns a new, unique, id that can be used for inserting a new document. Will not return any id that is included
    in ``excluded``.

    """
    excluded = excluded or list()

    excluded += await collection.distinct("_id")

    excluded = list(set(excluded))

    return random_alphanumeric(length=8, excluded=excluded)


def coerce_list(obj):
    """
    Takes an object of any type and returns a list. If ``obj`` is a list it will be passed back with modification.
    Otherwise, a single-item list containing ``obj`` will be returned.

    :param obj: an object of any type.
    :type obj: any

    :return: a list equal to or containing ``obj``.
    :rtype: list

    """
    return [obj] if not isinstance(obj, list) else obj


def to_bool(obj):
    return str(obj).lower() in ["1", "true"]


def get_static_hash(client_path):
    for file_name in os.listdir(client_path):
        if "style." in file_name:
            return file_name.split(".")[1]


async def reload(app):
    exe = sys.executable

    for callback in app.on_shutdown:
        await callback(app)

    if exe.endswith("python") or "python3" in exe:
        return os.execl(exe, exe, *sys.argv)

    if exe.endswith("run"):
        return os.execv(exe, sys.argv)

    raise SystemError("Could not determine executable type")


async def update_status_process(db, dispatch, _id, progress, step=None, error=None):
    """
    Update the process field in a status document. These fields are used to track long-running asynchronous processes
    such as software updates or data imports.

    More specific update function can be built around this utility.

    :param db: the application database client
    :type db: :class:`~motor.motor_asyncio.AsyncIOMotorClient`

    :param dispatch: a reference to the dispatcher's dispatch method
    :type dispatch: func

    :param _id: the database _id for the status document
    :type _id: str

    :param progress: the numeric progress number for the step
    :type progress: Union(int, float)

    :param step: the name of the step in progress
    :type step: Coroutine[str]

    :param error: an error that stopped the process
    :type error: str

    :return: processed status document
    :rtype: Coroutine[dict]

    """
    set_dict = {
        "process.progress": progress
    }

    if step:
        set_dict["process.step"] = step

    if error:
        set_dict["process.error"] = error

    document = await db.status.find_one_and_update({"_id": _id}, {
        "$set": set_dict
    }, return_document=pymongo.ReturnDocument.AFTER)

    document = base_processor(document)

    await dispatch("status", "update", document)

    return document

