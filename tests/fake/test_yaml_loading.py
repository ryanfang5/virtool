from pathlib import Path

import pytest
from virtool.dev.fake import populate
from virtool.fake.factory import load_test_case_from_yml


@pytest.fixture
def example_test_case(test_files_path) -> Path:
    return test_files_path / "fake/test_case.yml"


async def test_load_yml(app, fake, example_test_case):
    await fake.users.insert()

    case = await load_test_case_from_yml(app, example_test_case, "bob")

    assert case.analysis.ready == False
    assert case.analysis._id == case.job.args["analysis_id"]
    assert case.analysis.sample["id"] == case.sample._id
    assert case.analysis.index["id"] == case.index._id
    assert case.analysis.reference["id"] == case.reference._id
    assert case.sample._id == case.job.args["sample_id"]
    assert case.index._id == case.job.args["index_id"]
    assert case.reference._id == case.job.args["ref_id"]

    for actual, expected in zip(case.subtractions, case.job.args["subtractions"]):
        assert actual._id == expected

    assert case.job.args["additional_arg"] is True


async def test_populate_does_load_yaml(
    app, example_test_case, tmp_path, config
):

    app["config"] = config
    app["config"].fake_path = example_test_case.parent
    await populate(app)

    job = await app["db"].jobs.find_one({"_id": "test_case_1"})
    assert job["_id"] == "test_case_1"
