from typing import Union, List, Optional

from aiohttp.web_exceptions import (
    HTTPBadGateway,
    HTTPBadRequest,
    HTTPConflict,
)
from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r202, r204, r400, r403, r404, r502
from virtool_core.models.enums import Permission
from virtool_core.models.otu import OTU

import virtool.history.db
import virtool.indexes.db
import virtool.mongo.utils
import virtool.otus.db
import virtool.references.db
import virtool.utils
from virtool.api.response import InsufficientRights

from virtool.api.response import NotFound, json_response
from virtool.data.errors import (
    ResourceNotFoundError,
    ResourceRemoteError,
    ResourceConflictError,
    ResourceError,
)
from virtool.data.utils import get_data_from_req
from virtool.http.policy import policy, PermissionsRoutePolicy
from virtool.http.routes import Routes
from virtool.indexes.oas import ListIndexesResponse

from virtool.otus.oas import CreateOTURequest

from virtool.otus.oas import GetOTUResponse
from virtool.references.oas import (
    CreateReferenceSchema,
    EditReferenceSchema,
    CreateReferenceGroupsSchema,
    ReferenceRightsSchema,
    CreateReferenceUsersSchema,
    CreateReferenceResponse,
    GetReferencesResponse,
    ReferenceResponse,
    ReferenceReleaseResponse,
    CreateReferenceUpdateResponse,
    GetReferenceUpdateResponse,
    CreateReferenceIndexesResponse,
    ReferenceGroupsResponse,
    CreateReferenceGroupResponse,
    ReferenceGroupResponse,
    ReferenceUsersSchema,
    ReferenceHistoryResponse,
)

routes = Routes()

RIGHTS_SCHEMA = {
    "build": {"type": "boolean"},
    "modify": {"type": "boolean"},
    "modify_otu": {"type": "boolean"},
    "remove": {"type": "boolean"},
}


@routes.view("/refs")
class ReferencesView(PydanticView):
    async def get(self, find: Optional[str]) -> r200[GetReferencesResponse]:
        """
        Find references.

        Status Codes:
            200: Successful operation
        """

        # Missing test

        search_result = get_data_from_req(self.request).references.find(
            find,
            self.request["client"].user_id,
            self.request["client"].administrator,
            self.request["client"].groups,
        )

        return json_response(search_result)

    @policy(PermissionsRoutePolicy(Permission.create_ref))
    async def post(
        self, data: CreateReferenceSchema
    ) -> Union[r200[CreateReferenceResponse], r400, r403, r502]:
        """
        Create a reference.

        Creates an empty reference.

        Status Codes:
            200: Successful operation
            400: Source reference does not exist
            403: Not permitted
            502: Could not reach GitHub
        """
        # Missing remote_from and cloned_from tests
        try:
            document = await get_data_from_req(self.request).references.create(
                data, self.request["client"].user_id
            )
        except ResourceNotFoundError as err:
            if "Source reference does not exist" in str(err):
                raise HTTPBadRequest(text=str(err))
            elif "File not found" in str(err):
                raise NotFound(str(err))
        except ResourceRemoteError as err:
            if "Could not reach GitHub" in str(err):
                raise HTTPBadGateway(text=str(err))
            elif "Could not retrieve latest GitHub release" in str(err):
                raise HTTPBadGateway(text=str(err))

        headers = {"Location": f"/refs/{document.id}"}

        return json_response(document, headers=headers, status=201)


@routes.view("/refs/{ref_id}")
@routes.jobs_api.get("/refs/{ref_id}")
class ReferenceView(PydanticView):
    async def get(
        self, ref_id: Optional[str]
    ) -> Union[r200[ReferenceResponse], r403, r404]:
        """
        Get a reference.

        Retrieves the details of a reference.

        Status Codes:
            200: Successful operation
            403: Not permitted
            404: Not found

        """
        # Missing test
        try:
            document = get_data_from_req(self.request).references.get(ref_id)
        except ResourceNotFoundError:
            raise NotFound()

        return json_response(document)

    async def patch(
        self,
        ref_id: str,
        /,
        data: EditReferenceSchema,
    ) -> Union[r200[ReferenceResponse], r403, r404]:
        """
        Update a reference.

        Updates an existing reference.

        Status Codes:
            200: Successful operation
            403: Insufficient rights
            404: Not found

        """
        try:
            document = await get_data_from_req(self.request).references.update(
                ref_id, data, self.request
            )
        except ResourceNotFoundError:
            raise NotFound()
        except ResourceConflictError as err:
            raise HTTPBadRequest(text=str(err))

        return json_response(document)

    async def delete(self, ref_id: str, /) -> Union[r202, r403, r404]:
        """
        Delete a reference.

        Deletes a reference and its associated OTUs, history, and indexes. Deleting a
        reference does not break dependent analyses and other resources.

        Status Codes:
            202: Accepted
            403: Insufficient rights
            404: Not found

        """
        # Missing test
        try:
            task = await get_data_from_req(self.request).references.remove(
                ref_id, self.request["client"].user_id, self.request
            )
        except ResourceNotFoundError:
            raise NotFound()

        headers = {"Content-Location": f"/tasks/{task.id}"}

        return json_response(task, 202, headers)


@routes.view("/refs/{ref_id}/release")
class ReferenceReleaseView(PydanticView):
    async def get(self, ref_id: str, /) -> r200[ReferenceReleaseResponse]:
        """
        Get latest update.

        Retrieves the latest remote reference update from GitHub.

        Also updates the reference document. This is the only way of doing so without
        waiting for an automatic refresh every 10 minutes.

        Status Codes:
            200: Successful operation

        """
        try:
            release = await get_data_from_req(self.request).references.get_release(
                ref_id, self.request.app
            )
        except ResourceNotFoundError:
            raise NotFound()
        except ResourceConflictError as err:
            raise HTTPBadRequest(text=str(err))
        except ResourceRemoteError as err:
            if "Could not reach GitHub" in str(err):
                raise HTTPBadGateway(text=str(err))
            elif "Release repository does not exist on GitHub" in str(err):
                raise HTTPBadGateway(text=str(err))
        return json_response(release)


@routes.view("/refs/{ref_id}/updates")
class ReferenceUpdatesView(PydanticView):
    async def get(self, ref_id: str, /) -> r200[GetReferenceUpdateResponse]:
        """
        List updates.

        Lists all updates made to the reference.

        Status Codes:
            200: Successful operation
        """
        try:
            updates = await get_data_from_req(self.request).references.get_updates(
                ref_id
            )
        except ResourceNotFoundError:
            raise NotFound()

        return json_response(updates)

    async def post(
        self, ref_id: str, /
    ) -> Union[r201[CreateReferenceUpdateResponse], r403, r404]:
        """
        Update a reference.

        Updates the reference to the last version of the linked remote reference.

        Status Codes:
            201: Successful operation
            403: Insufficient rights
            404: Not found
        """
        try:
            sub_document = await get_data_from_req(
                self.request
            ).references.create_update(
                ref_id, self.request["client"].user_id, self.request
            )
        except ResourceNotFoundError:
            raise NotFound()
        except ResourceError as err:
            raise HTTPBadRequest(text=str(err))

        return json_response(sub_document, status=201)


@routes.view("/refs/{ref_id}/otus")
class ReferenceOTUsView(PydanticView):
    async def get(
        self,
        find: Optional[str],
        verified: Optional[bool],
        names: Optional[Union[bool, str]],
        ref_id: str,
        /,
    ) -> Union[r200[GetOTUResponse], r404]:
        """
        Find OTUs.

        Finds OTUs by name or abbreviation. Results are paginated.

        Status Codes:
            200: Successful operation
            404: Not found
        """
        # Missing test
        try:
            data = await get_data_from_req(self.request).references.get_otus(
                find, verified, names, ref_id, self.request.query
            )
        except ResourceNotFoundError:
            raise NotFound()
        return json_response(data)

    async def post(
        self, ref_id: str, /, data: CreateOTURequest
    ) -> Union[r201[OTU], r400, r403, r404]:
        """
        Create an OTU.

        """
        db = self.request.app["db"]

        reference = await db.references.find_one(ref_id, ["groups", "users"])

        if reference is None:
            raise NotFound()

        if not await virtool.references.db.check_right(
            self.request, reference, "modify_otu"
        ):
            raise InsufficientRights()

        # Check if either the name or abbreviation are already in use. Send a ``400`` if
        # they are.
        if message := await virtool.otus.db.check_name_and_abbreviation(
            db, ref_id, data.name, data.abbreviation
        ):
            raise HTTPBadRequest(text=message)

        otu = await get_data_from_req(self.request).otus.create(
            ref_id,
            data,
            user_id=self.request["client"].user_id,
        )

        return json_response(otu, status=201, headers={"Location": f"/otus/{otu.id}"})


@routes.view("/refs/{ref_id}/history")
class ReferenceHistoryView(PydanticView):
    async def get(
        self, unbuilt: Optional[str], ref_id: str, /
    ) -> Union[r200[ReferenceHistoryResponse], r404]:
        """
        List history.

        Retrieves a paginated list of changes made to OTUs in the reference.

        Status Codes:
            200: Successful operation
            404: Not found
        """
        # Missing test
        try:
            data = await get_data_from_req(self.request).references.get_history(
                ref_id, unbuilt, self.request.query
            )
        except ResourceNotFoundError:
            raise NotFound()
        return json_response(data)


@routes.view("/refs/{ref_id}/indexes")
class ReferenceIndexesView(PydanticView):
    async def get(self, ref_id: str, /) -> Union[r200[ListIndexesResponse], r404]:
        """
        List indexes.

        Retrieves a paginated list of indexes that have been created for the reference.

        Status Codes:
            200: Successful operation
            404: Not found
        """
        try:
            data = await get_data_from_req(self.request).references.find_indexes(
                ref_id, self.request.query
            )
        except ResourceNotFoundError:
            raise NotFound()

        return json_response(data)

    async def post(
        self, ref_id: str, /
    ) -> Union[r201[CreateReferenceIndexesResponse], r403, r404]:
        """
        Create an index.

        Starts a job to rebuild the otus Bowtie2 index on disk.

        Does a check to make sure there are no unverified OTUs in the collection
        and updates otu history to show the version and id of the new index.

        Status Codes:
            201: Successful operation
            403: Insufficient rights
            404: Not found

        """
        try:
            document = await get_data_from_req(self.request).references.create_index(
                ref_id, self.request, self.request["client"].user_id
            )
        except ResourceNotFoundError:
            raise NotFound()
        except ResourceConflictError as err:
            raise HTTPConflict(text=str(err))
        except ResourceError as err:
            if "There are unverified OTUs" in str(err):
                raise HTTPBadRequest(text=str(err))
            elif "There are no unbuilt changes" in str(err):
                raise HTTPBadRequest(text=str(err))

        headers = {"Location": f"/indexes/{document.id}"}

        return json_response(
            document,
            status=201,
            headers=headers,
        )


@routes.view("/refs/{ref_id}/groups")
class ReferenceGroupsView(PydanticView):
    async def get(self, ref_id: str, /) -> Union[r200[ReferenceGroupsResponse], r404]:
        """
        List groups.

        Lists all groups that have access to the reference.

        Status Codes:
            200: Successful operation
            404: Not found
        """
        # Missing test
        try:
            groups = get_data_from_req(self.request).references.find_groups(ref_id)
        except ResourceNotFoundError:
            raise NotFound()

        return json_response(groups)

    async def post(
        self, ref_id: str, /, data: CreateReferenceGroupsSchema
    ) -> Union[r201[CreateReferenceGroupResponse], r400, r403, r404]:
        """
        Add a group.

        Adds a group to the reference. Groups can view, use, and modify the reference.

        Status Codes:
            201: Successful operation
            400: Bad request
            403: Insufficient rights
            404: Not found
        """
        try:
            subdocument = await get_data_from_req(self.request).references.create_group(
                ref_id, data, self.request
            )
        except ResourceNotFoundError:
            raise NotFound()
        except ResourceConflictError as err:
            if "Group already exists" in str(err):
                raise HTTPBadRequest(text=str(err))
            elif "Group does not exist" in str(err):
                raise HTTPBadRequest(text=str(err))

        headers = {"Location": f"/refs/{ref_id}/groups/{subdocument.id}"}

        return json_response(subdocument, headers=headers, status=201)


@routes.view("/refs/{ref_id}/groups/{group_id}")
class ReferenceGroupView(PydanticView):
    async def get(
        self, ref_id: str, group_id: str, /
    ) -> Union[r200[ReferenceGroupResponse], r404]:
        """
        Get a group.

        Retrieves the details of a group that has access to the reference.

        Status Codes:
            200: Successful operation
            404: Not found
        """
        # Missing test
        try:
            group = await get_data_from_req(self.request).references.get_group(
                ref_id, group_id
            )
        except ResourceNotFoundError:
            raise NotFound()

        return json_response(group)

    async def patch(
        self,
        ref_id: str,
        group_id: str,
        /,
        data: ReferenceRightsSchema,
    ) -> Union[r200[ReferenceGroupResponse], r403, r404]:
        """
        Update a group.

        Updates the access rights a group has on the reference.

        Status Codes:
            200: Successful operation
            403: Insufficient rights
            404: Not found
        """
        try:
            subdocument = await get_data_from_req(self.request).references.update_group(
                data, ref_id, group_id, self.request
            )
        except ResourceNotFoundError:
            raise NotFound()

        return json_response(subdocument)

    async def delete(self, ref_id: str, group_id: str, /) -> Union[r204, r403, r404]:
        """
        Remove a group.

        Removes a group from the reference.

        Status Codes:
            204: No content
            403: Insufficient rights
            404: Not found
        """
        try:
            await get_data_from_req(self.request).references.delete_group(
                ref_id, group_id, self.request
            )
        except ResourceNotFoundError:
            raise NotFound()


@routes.view("/refs/{ref_id}/users")
class ReferenceUsersView(PydanticView):
    async def post(
        self, ref_id: str, /, data: CreateReferenceUsersSchema
    ) -> Union[r201[List[ReferenceUsersSchema]], r400, r403, r404]:
        """
        Add a user.

        Adds a user to the reference. Users can view, use, and modify the reference.

        Status Codes:
            201: Successful operation
            400: Bad request
            403: Insufficient rights
            404: Not found
        """
        try:
            subdocument = await get_data_from_req(self.request).references.add_user(
                data, ref_id, self.request
            )
        except ResourceNotFoundError:
            raise NotFound()
        except ResourceConflictError as err:
            if "User already exists" in str(err):
                raise HTTPBadRequest(text=str(err))
            elif "User does not exist" in str(err):
                raise HTTPBadRequest(text=str(err))
        headers = {"Location": f"/refs/{ref_id}/users/{subdocument.id}"}

        return json_response(subdocument, headers=headers, status=201)


@routes.view("/refs/{ref_id}/users/{user_id}")
class ReferenceUserView(PydanticView):
    async def patch(
        self, ref_id: str, user_id: str, /, data: ReferenceRightsSchema
    ) -> Union[r200[ReferenceGroupResponse], r403, r404]:
        """
        Update a user.

        Updates the access rights a user has on the reference.

        Status Codes:
            200: Successful operation
            403: Insufficient rights
            404: Not found
        """
        try:
            subdocument = await get_data_from_req(self.request).references.edit_user(
                data, ref_id, user_id, self.request
            )
        except ResourceNotFoundError:
            raise NotFound()

        return json_response(subdocument)

    async def delete(self, ref_id: str, user_id: str, /) -> Union[r204, r403, r404]:
        """
        Remove a user.

        Removes a user from the reference.

        Status Codes:
            204: No content
            403: Insufficient rights
            404: Not found
        """
        try:
            await get_data_from_req(self.request).references.remove_user(
                ref_id, user_id, self.request
            )
        except ResourceNotFoundError:
            raise NotFound()
