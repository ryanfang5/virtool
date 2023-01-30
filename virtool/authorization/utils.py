import sys
from logging import getLogger

import openfga_sdk
from aiohttp import ClientConnectorError
from aiohttp.web_request import Request
from openfga_sdk import (
    CreateStoreRequest,
    WriteAuthorizationModelRequest,
    TypeDefinition,
    Userset,
    OpenFgaApi,
)
from openfga_sdk.api import open_fga_api

from virtool.authorization.client import AuthorizationClient
from virtool.authorization.permissions import (
    AppPermission,
    SpacePermission,
)

logger = getLogger("authz")


def get_authorization_client_from_req(req: Request) -> AuthorizationClient:
    """
    Get the authorization client instance from a request object.
    """
    return req.app["auth_client"]


async def connect_openfga(openfga_host: str, openfga_scheme: str):
    """
    Connects to an OpenFGA server and configures the store id.
    Returns the application client instance.
    """
    configuration = openfga_sdk.Configuration(
        api_scheme=openfga_scheme, api_host=openfga_host
    )

    logger.info("Connecting to OpenFGA")

    try:
        api_instance = open_fga_api.OpenFgaApi(openfga_sdk.ApiClient(configuration))

        configuration.store_id = await get_or_create_openfga_store(api_instance)

        await write_openfga_authorization_model(api_instance)

    except ClientConnectorError:
        logger.fatal("Could not connect to OpenFGA")
        sys.exit(1)

    return api_instance


async def get_or_create_openfga_store(api_instance: OpenFgaApi):
    """
    Get the OpenFGA Store or create one if it does not exist.

    :return: the store id
    """
    response = await api_instance.list_stores()

    logger.info("Connected to OpenFGA")

    if response.stores:
        logger.info("Found existing OpenFGA store")
        return response.stores[0].id

    response = await api_instance.create_store(
        CreateStoreRequest(
            name="Virtool",
        )
    )

    logger.info("Created new OpenFGA store")

    return response.id


async def write_openfga_authorization_model(api_instance: OpenFgaApi):
    """
    Write the authorization model for the OpenFGA Store if it does not exist.
    """
    response = await api_instance.read_authorization_models()

    # The permission string for OpenFGA is the ``Permission.id`` value. Instances of
    # ``Permission`` are the values for the permission (eg. ``AppPermission``) enums.
    app_permissions_definition = TypeDefinition(
        type="app",
        relations={
            permission.value.id: Userset(this={}) for permission in AppPermission
        },
    )

    space_permissions_definition = TypeDefinition(
        type="space",
        relations={
            permission.value.id: Userset(this={}) for permission in SpacePermission
        },
    )

    group_membership_definition = TypeDefinition(
        type="group",
        relations={"member": Userset(this={})},
    )

    type_definitions = WriteAuthorizationModelRequest(
        type_definitions=[
            app_permissions_definition,
            group_membership_definition,
            space_permissions_definition,
        ],
    )

    if (
        response.authorization_models
        and response.authorization_models[0].type_definitions
        == type_definitions.type_definitions
    ):
        logger.info("OpenFGA authorization model is up-to-date.")
        return

    await api_instance.write_authorization_model(type_definitions)

    logger.info("Updated OpenFGA authorization model.")
