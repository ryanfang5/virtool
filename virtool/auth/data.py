from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from virtool.auth.models import SQLPermission
from virtool_core.models.auth import PermissionMinimal


class AuthData:
    def __init__(self, pg: AsyncEngine):
        self._pg = pg

    async def find(self, resource_type) -> List[PermissionMinimal]:
        """
        List all possible permissions.

        :return: a list of all permissions

        """
        statement = select(SQLPermission)

        if resource_type:
            statement = statement.filter_by(resource_type=resource_type)

        async with AsyncSession(self._pg) as session:
            result = await session.execute(statement)

        return [
            PermissionMinimal(**permission.to_dict()) for permission in result.scalars()
        ]
