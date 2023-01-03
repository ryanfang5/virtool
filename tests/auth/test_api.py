import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from virtool_core.models.enums import Permission

from virtool.auth.models import SQLPermission, ResourceType, Action


@pytest.mark.apitest
@pytest.mark.parametrize(
    "resource,status",
    [(ResourceType.app, 200), (ResourceType.group, 200), ("invalid", 400), (None, 200)],
)
async def test_find(spawn_client, resource, status, pg, snapshot):
    client = await spawn_client(authorize=True)

    async with AsyncSession(pg) as session:
        session.add_all(
            [
                SQLPermission(
                    id=Permission.create_sample,
                    name="Create Sample",
                    resource_type=ResourceType.app,
                    action=Action.create,
                    description="Required for creating a sample",
                ),
                SQLPermission(
                    id=Permission.modify_subtraction,
                    name="Modify Subtraction",
                    resource_type=ResourceType.app,
                    action=Action.modify,
                    description="Required for modifying a subtraction",
                ),
            ]
        )
        await session.commit()

    url = "/source/permissions"

    if resource:
        url += f"?resource_type={resource}"

    resp = await client.get(url)

    assert resp.status == status
    assert await resp.json() == snapshot
