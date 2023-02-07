"""
Authorization clients.

"""
import asyncio
from abc import ABC, abstractmethod
from typing import Union, List, Tuple

from openfga_sdk import (
    OpenFgaApi,
    WriteRequest,
    TupleKeys,
    TupleKey,
    ApiException,
    ReadRequest,
    CheckRequest,
)
from virtool_core.models.enums import Permission

from virtool.authorization.permissions import (
    PermissionType,
    ResourceType,
)
from virtool.authorization.relationships import AbstractRelationship
from virtool.authorization.results import (
    RemoveRelationshipResult,
    AddRelationshipResult,
)
from virtool.authorization.roles import AdministratorRole, ReferenceRole


class AbstractAuthorizationClient(ABC):
    @abstractmethod
    async def check(
        self,
        user_id: str,
        permission: Permission,
        resource_type: ResourceType,
        resource_id: Union[str, int],
    ) -> bool:
        ...

    @abstractmethod
    async def list_administrators(self) -> List[dict]:
        ...

    @abstractmethod
    async def add(self, *relationships: AbstractRelationship):
        ...

    @abstractmethod
    async def remove(self, *relationships: AbstractRelationship):
        ...


class AuthorizationClient(AbstractAuthorizationClient):
    """
    An authorization client backed by OpenFGA.

    """

    def __init__(self, open_fga: OpenFgaApi):
        self.open_fga = open_fga

    async def check(
        self,
        user_id: str,
        permission: PermissionType,
        resource_type: ResourceType,
        resource_id: Union[str, int],
    ) -> bool:
        """
        Check whether a user has a permission on a resource.
        """

        response = await self.open_fga.check(
            CheckRequest(
                tuple_key=TupleKey(
                    user=f"user:{user_id}",
                    relation=permission.value.id,
                    object=f"{resource_type.value}:{resource_id}",
                ),
            )
        )

        return response.allowed

    async def get_space_roles(self, space_id: int) -> List[str]:
        """
        Return a list of roles for a space.

        :param space_id: the id of the space
        :return: a list of roles
        """
        response = await self.open_fga.read(
            ReadRequest(
                tuple_key=TupleKey(
                    user="user:", relation="base", object=f"group:{space_id}"
                )
            )
        )

        return sorted(
            [
                relation_tuple.key.user.split(":")[1]
                for relation_tuple in response.tuples
            ]
        )

    async def list_administrators(self) -> List[Tuple[str, AdministratorRole]]:
        """
        Return a list of user ids that are administrators and their roles.

        :return: a list of tuples containing user ids and their roles

        """
        responses = await asyncio.gather(
            *[
                self.open_fga.read(
                    ReadRequest(
                        tuple_key=TupleKey(
                            user="user:", relation=role.value, object="app:"
                        ),
                    )
                )
                for role in AdministratorRole
            ]
        )

        return sorted(
            [
                relation_tuple.key.user.split(":")[1]
                for response in responses
                for relation_tuple in response
            ]
        )

    async def list_user_spaces(self, user_id: str) -> List[int]:
        """
        Return a list of ids of spaces the user is a member of.

        :param user_id: the id of the user
        :return: a list of space ids
        """
        response = await self.open_fga.read(
            ReadRequest(
                tuple_key=TupleKey(
                    user=f"user:{user_id}", relation="member", object="group:"
                ),
            )
        )

        return sorted(
            [
                relation_tuple.key.object.split(":")[1]
                for relation_tuple in response.tuples
            ]
        )

    async def list_reference_users(
        self, ref_id: str
    ) -> List[Tuple[str, ReferenceRole]]:
        """
        List users and their roles for a reference.

        The returned list only includes users that have an explicit role defined on the
        reference. Space members that have access to the reference through the space
        base role are not included.

        :param ref_id: the id of the reference
        :return: a list of user ids and their roles
        """
        ...

    async def add(self, *relationships: AbstractRelationship):

        """
        Add one or more authorization relationships.

        :param relationships:
        """
        requests = [
            WriteRequest(
                writes=TupleKeys(
                    tuple_keys=[
                        TupleKey(
                            user=f"{relationship.user_type}:{relationship.user_id}",
                            relation=relationship.relation,
                            object=f"{relationship.object_type}:{relationship.object_id}",
                        )
                    ]
                )
            )
            for relationship in relationships
        ]

        done, _ = await asyncio.wait(
            [self.open_fga.write(request) for request in requests]
        )

        result = AddRelationshipResult(0, 0)

        for aw in done:
            try:
                await aw
            except ApiException:
                result.exists_count += 1

        result.removed_count = len(relationships) - result.exists_count

        return result

    async def remove(self, *relationships: AbstractRelationship):
        """
        Remove one or more authorization relationships.
        """
        requests = [
            WriteRequest(
                deletes=TupleKeys(
                    tuple_keys=[
                        TupleKey(
                            user=f"{relationship.user_type}:{relationship.user_id}",
                            relation=relationship.relation,
                            object=f"{relationship.object_type}:{relationship.object_id}",
                        )
                    ]
                )
            )
            for relationship in relationships
        ]

        done, _ = await asyncio.wait(
            [self.open_fga.write(request) for request in requests]
        )

        result = RemoveRelationshipResult(0, 0)

        for aw in done:
            try:
                await aw
            except ApiException:
                result.not_found_count += 1

        result.removed_count = len(relationships) - result.not_found_count

        return result


def raise_exception_if_not_default_space(
    resource_type: ResourceType, resource_id: Union[int, str]
):
    """
    Raise an exception if the described resource is not the default space (id=0).

    This will be removed once more resource types are supported.
    """
    if resource_type != ResourceType.SPACE or resource_id != 0:
        raise ValueError(
            "Only permissions on the default space are currently supported"
        )
