import asyncio
from typing import Union

from openfga_sdk import ApiClient, TupleKey
from virtool_core.models.enums import Permission

from virtool.api.response import NotFound
from virtool.auth.mongo import (
    check_in_mongo,
    list_permissions_in_mongo,
    add_in_mongo,
    remove_in_mongo,
)
from virtool.auth.openfga import (
    check_in_open_fga,
    list_permissions_in_open_fga,
    add_in_open_fga, remove_in_open_fga,
)
from virtool.auth.relationships import GroupPermission, BaseRelationship
from virtool.data.layer import DataLayer

from virtool.mongo.core import DB


class AbstractAuthorizationClient:
    def __init__(self, mongo: DB, open_fga: ApiClient, data: DataLayer = None):
        self.mongo = mongo
        self.open_fga = open_fga
        self.data = data

    async def check(
        self,
        user_id: str,
        permission: Permission,
        object_type: str,
        object_id: Union[str, int],
    ) -> bool:
        """
        Check a permission in Mongo and OpenFGA.
        """

        mongo_result, open_fga_result = await asyncio.gather(
            *[
                check_in_mongo(self.mongo, user_id, permission),
                check_in_open_fga(
                    self.open_fga, user_id, permission, object_type, object_id
                ),
            ]
        )

        return mongo_result or open_fga_result

    async def list_permissions(
        self, user_id: str, object_type: str, object_id: Union[str, int]
    ) -> dict:
        """
        List permissions for a user.
        """
        try:
            return await list_permissions_in_mongo(self.mongo, user_id)
        except NotFound:
            return await list_permissions_in_open_fga(
                self.open_fga, user_id, object_type, object_id
            )

    async def add(self, relationship: BaseRelationship):
        """
        Add permissions for a group or user in mongo and OpenFGA.
        """

        if isinstance(relationship, GroupPermission):
            try:
                await add_in_mongo(
                    self.data, relationship.user_id, relationship.relation
                )
            except NotFound:
                pass

            relationship.user_id = f"{relationship.user_id}#member"

        for relation in relationship.relation:
            tuple_key = TupleKey(
                user=f"{relationship.user_type}:{relationship.user_id}",
                relation=relation,
                object=f"{relationship.object_type}:{relationship.object_name}",
            )

            await add_in_open_fga(self.open_fga, tuple_key)

    async def remove(self, relationship: BaseRelationship):

        if isinstance(relationship, GroupPermission):
            try:
                await remove_in_mongo(
                    self.data, relationship.user_id, relationship.relation
                )
            except NotFound:
                pass

            relationship.user_id = f"{relationship.user_id}#member"

        for relation in relationship.relation:
            tuple_key = TupleKey(
                user=f"{relationship.user_type}:{relationship.user_id}",
                relation=relation,
                object=f"{relationship.object_type}:{relationship.object_name}",
            )

            await remove_in_open_fga(self.open_fga, tuple_key)
