from typing import List

from virtool_core.models.auth import PermissionMinimal

from virtool.authorization.permissions import AppPermission, SpacePermission


class AuthorizationData:
    @staticmethod
    async def find() -> List[PermissionMinimal]:
        """
        List all possible permissions.

        :return: a list of all permissions

        """
        return [
            *[
                PermissionMinimal(
                    id=permission.name,
                    name=permission.value.name,
                    resource_type=permission.value.resource_type.value,
                    action=permission.value.action.value,
                    description=permission.value.description,
                )
                for permission in [
                    *list(AppPermission),
                    *list(SpacePermission),
                ]
            ]
        ]
