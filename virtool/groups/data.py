from typing import List, TYPE_CHECKING

from pymongo.errors import DuplicateKeyError
from virtool_core.models.group import GroupMinimal, Group

from virtool.authorization.client import AuthorizationClient
from virtool.data.errors import (
    ResourceNotFoundError,
    ResourceConflictError,
)
from virtool.groups.db import (
    update_member_users,
    fetch_complete_group,
)
from virtool.groups.oas import UpdateGroupRequest
from virtool.groups.utils import (
    convert_permissions_dict_to_relationships,
)
from virtool.mongo.utils import get_one_field, id_exists
from virtool.users.utils import generate_base_permissions
from virtool.utils import base_processor

if TYPE_CHECKING:
    from virtool.mongo.core import DB


class GroupsData:
    def __init__(self, authorization_client: AuthorizationClient, db: "DB"):
        self._authorization_client = authorization_client
        self._db = db

    async def find(self) -> List[GroupMinimal]:
        """
        List all user groups.

        :return: a list of all user groups

        """
        return [
            GroupMinimal(**base_processor(document))
            async for document in self._db.groups.find()
        ]

    async def get(self, group_id: str) -> Group:
        """
        Get a single group by its ID.

        :param group_id: the group's ID
        :return: the group
        """
        group = await fetch_complete_group(self._db, group_id)

        if group:
            return group

        raise ResourceNotFoundError()

    async def create(self, name: str) -> Group:
        """
        Create new group given a group ID.

        :param name: the ID for the new group
        :return: the group
        """

        try:
            document = await self._db.groups.insert_one(
                {
                    "name": name,
                    "permissions": generate_base_permissions(),
                }
            )
        except DuplicateKeyError:
            raise ResourceConflictError("Group already exists")

        return Group(**base_processor(document), users=[])

    async def update(self, group_id: str, data: UpdateGroupRequest) -> Group:
        """
        Update the permissions for a group.

        :param group_id: the ID of the group to update
        :param data: updates to the current permissions and/or to the group name
        :return: the group
        """
        if not await id_exists(self._db.groups, group_id):
            raise ResourceNotFoundError

        data = data.dict(exclude_unset=True)

        update = {}

        adds = None
        removes = None

        if "name" in data:
            update["name"] = data["name"]

        if "permissions" in data:
            permissions = await get_one_field(
                self._db.groups, "permissions", {"_id": group_id}
            )

            update["permissions"] = {
                **permissions,
                **data["permissions"],
            }

            adds, removes = convert_permissions_dict_to_relationships(
                group_id, update["permissions"]
            )

        if update:
            async with self._db.create_session() as session:
                if adds:
                    await self._authorization_client.add(*adds)

                if removes:
                    await self._authorization_client.remove(*removes)

                await self._db.groups.update_one(
                    {"_id": group_id},
                    {"$set": update},
                    session=session,
                )

                await update_member_users(self._db, group_id, session=session)

        return await fetch_complete_group(self._db, group_id)

    async def delete(self, group_id: str):
        async with self._db.create_session() as session:
            await self._authorization_client.delete_group(group_id)

            delete_result = await self._db.groups.delete_one(
                {"_id": group_id}, session=session
            )

            if not delete_result.deleted_count:
                raise ResourceNotFoundError

            await update_member_users(self._db, group_id, remove=True, session=session)
