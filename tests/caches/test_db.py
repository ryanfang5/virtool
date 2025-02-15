import pytest
import virtool.caches.db
import os

@pytest.fixture
def trim_parameters():
    return {
        "end_quality": "20",
        "mode": "pe",
        "max_error_rate": "0.1",
        "max_indel_rate": "0.03",
        "max_length": None,
        "mean_quality": "25",
        "min_length": "20",
    }


@pytest.mark.parametrize("paired", [True, False], ids=["paired", "unpaired"])
async def test_create(
    paired, snapshot, dbi, static_time, test_random_alphanumeric, trim_parameters
):
    """
    Test that the function works with default keyword arguments and when `paired` is either `True` or `False`.

    """
    cache = await virtool.caches.db.create(dbi, "foo", "aodp-abcdefgh", paired)

    assert cache == snapshot
    assert await dbi.caches.find_one() == snapshot


async def test_create_duplicate(
    snapshot, dbi, static_time, test_random_alphanumeric, trim_parameters
):
    """
    Test that the function handles duplicate document ids smoothly. The function should retry with a new id.

    """
    await dbi.caches.insert_one(
        {"_id": test_random_alphanumeric.next_choice[:8].lower()}
    )

    cache = await virtool.caches.db.create(dbi, "foo", "aodp-abcdefgh", False)

    assert cache == snapshot
    assert (
        await dbi.caches.find_one({"_id": test_random_alphanumeric.last_choice})
        == snapshot
    )


@pytest.mark.parametrize("exists", [True, False])
async def test_get(exists, dbi):
    """
    Test that the function returns a cache document when it exists and returns `None` when it does not.

    """
    if exists:
        await dbi.caches.insert_one({"_id": "foo"})

    result = await virtool.caches.db.get(dbi, "foo")

    if exists:
        assert result == {"id": "foo"}
        return

    assert result is None


@pytest.mark.parametrize("exception", [False, True])
async def test_remove(exception, dbi, tmp_path, config):
    app = {
        "db": dbi,
        "config": config,
    }

    f1 = tmp_path / "cache"
    f1.mkdir()

    f1.joinpath("baz")

    await dbi.caches.insert_one({"_id": "baz"})

    await virtool.caches.db.remove(app, "baz")

    assert await dbi.caches.count_documents({}) == 0

    assert os.listdir(f1) == []

