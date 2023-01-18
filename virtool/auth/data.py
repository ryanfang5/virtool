from typing import List

from sqlalchemy.ext.asyncio import AsyncEngine

from virtool_core.models.auth import PermissionMinimal

from virtool.auth.permissions import AppPermission


class AuthData:
    def __init__(self, pg: AsyncEngine):
        self._pg = pg

    @staticmethod
    async def find(resource_type) -> List[PermissionMinimal]:
        """
        List all possible permissions.

        :return: a list of all permissions

        """
        app_permissions = [
            PermissionMinimal(
                id=permission.name,
                name=permission.value.name,
                resource_type=permission.value.resource_type,
                action=permission.value.action,
                description=permission.value.description,
            )
            for permission in AppPermission
        ]

        if not resource_type:
            return [*app_permissions]

        if resource_type.value == "app":
            return app_permissions
