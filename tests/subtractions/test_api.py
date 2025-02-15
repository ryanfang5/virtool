import os

import pytest
from aiohttp.test_utils import make_mocked_coro
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from virtool.subtractions.models import SubtractionFile


@pytest.mark.parametrize(
    "data",
    [
        {"name": "Bar"},
        {"nickname": "Bar Subtraction"},
        {"nickname": ""},
        {"name": "Bar", "nickname": "Bar Subtraction"},
    ],
)
@pytest.mark.parametrize("has_user", [True, False])
async def test_edit(data, has_user, mocker, snapshot, fake, spawn_client):
    mocker.patch("virtool.subtractions.db.get_linked_samples", make_mocked_coro(12))

    document = {"_id": "foo", "name": "Foo", "nickname": "Foo Subtraction"}

    if has_user:
        user = await fake.users.insert()
        document["user"] = {"id": user["_id"]}

    client = await spawn_client(authorize=True, permissions=["modify_subtraction"])

    await client.db.subtraction.insert_one(document)

    resp = await client.patch("/subtractions/foo", data)

    assert resp.status == 200
    assert await resp.json() == snapshot
    assert await client.db.subtraction.find_one() == snapshot


@pytest.mark.parametrize("error", [None, "404_name", "404", "409"])
async def test_upload(error, tmp_path, spawn_job_client, snapshot, resp_is, pg: AsyncEngine):
    client = await spawn_job_client(authorize=True)
    test_dir = tmp_path / "files"
    test_dir.mkdir()
    test_dir.joinpath("subtraction.1.bt2").write_text("Bowtie2 file")
    path = test_dir / "subtraction.1.bt2"

    files = {"file": open(path, "rb")}

    client.app["config"].data_path = tmp_path

    subtraction = {"_id": "foo", "name": "Foo"}

    if error == "409":
        async with AsyncSession(pg) as session:
            session.add(SubtractionFile(name="subtraction.1.bt2", subtraction="foo"))
            await session.commit()

    await client.db.subtraction.insert_one(subtraction)

    url = "/subtractions/foo/files"

    if error == "404_name":
        url += "/reference.1.bt2"
    else:
        url += "/subtraction.1.bt2"

    resp = await client.put(url, data=files)

    if error == "404_name":
        await resp_is.not_found(resp, "Unsupported subtraction file name")
        return

    if error == "409":
        await resp_is.conflict(resp, "File name already exists")
        return

    assert resp.status == 201
    assert await resp.json() == snapshot
    assert os.listdir(tmp_path / "subtractions" / "foo") == ["subtraction.1.bt2"]


@pytest.mark.parametrize("error", [None, "404", "409", "422"])
async def test_finalize_subtraction(
    error, fake, spawn_job_client, snapshot, resp_is, test_subtraction_files
):
    user = await fake.users.insert()

    subtraction = {
        "_id": "foo",
        "name": "Foo",
        "nickname": "Foo Subtraction",
        "user": {"id": user["_id"]},
    }

    data = {
        "gc": {"a": 0.319, "t": 0.319, "g": 0.18, "c": 0.18, "n": 0.002},
        "count": 100,
    }

    client = await spawn_job_client(authorize=True)

    if error == "409":
        subtraction["ready"] = True

    if error == "422":
        data = {}

    if error != "404":
        await client.db.subtraction.insert_one(subtraction)

    resp = await client.patch("/subtractions/foo", json=data)

    if error == "404":
        await resp_is.not_found(resp)
        return

    if error == "409":
        await resp_is.conflict(resp, "Subtraction has already been finalized")
        return

    if error == "422":
        await resp_is.invalid_input(
            resp, {"gc": ["required field"], "count": ["required field"]}
        )
        return

    assert resp.status == 200
    assert await resp.json() == snapshot
    assert await client.db.subtraction.find_one("foo") == snapshot


@pytest.mark.parametrize("ready", [True, False])
@pytest.mark.parametrize("exists", [True, False])
async def test_job_remove(exists, ready, tmp_path, spawn_job_client, snapshot, resp_is):
    client = await spawn_job_client(authorize=True)
    client.app["config"].data_path = tmp_path

    if exists:
        await client.db.subtraction.insert_one(
            {
                "_id": "foo",
                "name": "Foo",
                "nickname": "Foo Subtraction",
                "deleted": False,
                "ready": ready,
            }
        )

        await client.db.samples.insert_one(
            {"_id": "test", "name": "Test", "subtractions": ["foo"]}
        )

    resp = await client.delete("/subtractions/foo")

    if not exists:
        assert resp.status == 404
        return

    if ready:
        await resp_is.conflict(resp, "Only unfinalized subtractions can be deleted")
        return

    await resp_is.no_content(resp)
    assert await client.db.subtraction.find_one("foo") == snapshot
    assert await client.db.samples.find_one("test") == snapshot


@pytest.mark.parametrize("error", [None, "400_subtraction", "400_file", "400_path"])
async def test_download_subtraction_files(
    error, tmp_path, spawn_job_client, pg: AsyncEngine
):
    client = await spawn_job_client(authorize=True)

    client.app["config"].data_path = tmp_path

    test_dir = tmp_path / "subtractions" / "foo"
    test_dir.mkdir(parents=True)

    if error != "400_path":
        test_dir.joinpath("subtraction.fa.gz").write_text("FASTA file")
        test_dir.joinpath("subtraction.1.bt2").write_text("Bowtie2 file")

    subtraction = {"_id": "foo", "name": "Foo"}

    if error != "400_subtraction":
        await client.db.subtraction.insert_one(subtraction)

    file_1 = SubtractionFile(
        id=1, name="subtraction.fa.gz", subtraction="foo", type="fasta"
    )

    file_2 = SubtractionFile(
        id=2, name="subtraction.1.bt2", subtraction="foo", type="bowtie2"
    )

    if error != "400_file":
        async with AsyncSession(pg) as session:
            session.add_all([file_1, file_2])
            await session.commit()

    fasta_resp = await client.get("/subtractions/foo/files/subtraction.fa.gz")
    bowtie_resp = await client.get("/subtractions/foo/files/subtraction.1.bt2")

    if not error:
        assert fasta_resp.status == bowtie_resp.status == 200
    else:
        assert fasta_resp.status == bowtie_resp.status == 404
        return

    fasta_expected_path = (
        client.app["config"].data_path / "subtractions" / "foo" / "subtraction.fa.gz"
    )
    bowtie_expected_path = (
        client.app["config"].data_path / "subtractions" / "foo" / "subtraction.1.bt2"
    )

    assert fasta_expected_path.read_bytes() == await fasta_resp.content.read()
    assert bowtie_expected_path.read_bytes() == await bowtie_resp.content.read()


async def test_create(spawn_client, mocker, snapshot):
    upload = mocker.Mock()
    upload.name = "test_upload"

    mocker.patch("virtool.db.utils.get_new_id", return_value="abc123")
    mocker.patch("virtool.pg.utils.get_row_by_id", return_value=upload)

    client = await spawn_client(
        authorize=True,
        base_url="https://virtool.example.com",
        permissions="modify_subtraction",
    )

    data = {"name": "Foobar", "nickname": "foo", "upload_id": 1234}

    resp = await client.post("/subtractions", data)

    assert await resp.json() == snapshot
