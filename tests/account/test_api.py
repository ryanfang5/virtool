import pytest
from virtool.users.utils import PERMISSIONS, hash_password


async def test_get(snapshot, spawn_client, static_time):
    client = await spawn_client(authorize=True)

    resp = await client.get("/account")

    assert resp.status == 200
    assert await resp.json() == snapshot

    assert await resp.json() == {
        "groups": [],
        "handle": "bob",
        "id": "test",
        "administrator": False,
        "last_password_change": static_time.iso,
        "permissions": {p: False for p in PERMISSIONS},
        "primary_group": "technician",
        "settings": {
            "quick_analyze_workflow": "pathoscope_bowtie",
            "show_ids": True,
            "show_versions": True,
            "skip_quick_analyze_dialog": True,
        },
    }


@pytest.mark.parametrize(
    "error",
    [
        None,
        "email_error",
        "password_length_error",
        "missing_old_password",
        "credentials_error",
    ],
)
async def test_edit(error, snapshot, spawn_client, resp_is, static_time):
    client = await spawn_client(authorize=True)

    client.app["settings"].minimum_password_length = 8

    data = {
        "email": "dev-at-virtool.ca" if error == "email_error" else "dev@virtool.ca",
        "password": "foo" if error == "password_length_error" else "foo_bar_1",
    }

    if error != "missing_old_password":
        data["old_password"] = (
            "not_right" if error == "credentials_error" else "hello_world"
        )

    resp = await client.patch("/account", data)

    if error == "email_error":
        await resp_is.invalid_input(resp, {"email": ["Not a valid email"]})

    elif error == "password_length_error":
        await resp_is.bad_request(
            resp, f"Password does not meet minimum length requirement (8)"
        )

    elif error == "missing_old_password":
        await resp_is.invalid_input(
            resp, {"password": ["field 'old_password' is required"]}
        )

    elif error == "credentials_error":
        await resp_is.bad_request(resp, "Invalid credentials")

    else:
        assert resp.status == 200
        assert await resp.json() == snapshot

        assert await resp.json() == {
            "permissions": {
                "cancel_job": False,
                "create_ref": False,
                "create_sample": False,
                "modify_hmm": False,
                "modify_subtraction": False,
                "remove_file": False,
                "remove_job": False,
                "upload_file": False,
            },
            "groups": [],
            "handle": "bob",
            "administrator": False,
            "last_password_change": static_time.iso,
            "primary_group": "technician",
            "settings": {
                "skip_quick_analyze_dialog": True,
                "show_ids": True,
                "show_versions": True,
                "quick_analyze_workflow": "pathoscope_bowtie",
            },
            "email": "dev@virtool.ca",
            "id": "test",
        }


async def test_get_settings(spawn_client):
    """
    Test that a ``GET /account/settings`` returns the settings for the session user.

    """
    client = await spawn_client(authorize=True)

    resp = await client.get("/account/settings")

    assert resp.status == 200

    assert await resp.json() == {
        "skip_quick_analyze_dialog": True,
        "show_ids": True,
        "show_versions": True,
        "quick_analyze_workflow": "pathoscope_bowtie",
    }


@pytest.mark.parametrize("invalid_input", [False, True])
async def test_update_settings(invalid_input, spawn_client, resp_is):
    """
    Test that account settings can be updated at ``POST /account/settings`` and that requests to
    ``POST /account/settings`` return 422 for invalid JSON fields.

    """
    client = await spawn_client(authorize=True)

    data = {"show_ids": False}

    if invalid_input:
        data = {"foo_bar": True, "show_ids": "yes"}

    resp = await client.patch("/account/settings", data)

    if invalid_input:
        await resp_is.invalid_input(resp, {"show_ids": ["must be of boolean type"]})
    else:
        assert resp.status == 200

        assert await resp.json() == {
            "skip_quick_analyze_dialog": True,
            "show_ids": False,
            "show_versions": True,
            "quick_analyze_workflow": "pathoscope_bowtie",
        }


async def test_get_api_keys(spawn_client):
    client = await spawn_client(authorize=True)

    await client.db.keys.insert_many(
        [
            {
                "_id": "abc123",
                "id": "foobar_0",
                "name": "Foobar",
                "user": {"id": "test"},
            },
            {"_id": "xyz321", "id": "baz_1", "name": "Baz", "user": {"id": "test"}},
        ]
    )

    resp = await client.get("/account/keys")

    assert await resp.json() == [
        {"id": "foobar_0", "name": "Foobar"},
        {"id": "baz_1", "name": "Baz"},
    ]


class TestCreateAPIKey:
    @pytest.mark.parametrize("has_perm", [True, False])
    @pytest.mark.parametrize("req_perm", [True, False])
    async def test(
        self,
        has_perm,
        req_perm,
        mocker,
        snapshot,
        spawn_client,
        static_time,
        no_permissions,
    ):
        """
        Test that creation of an API key functions properly. Check that different permission inputs work.

        """
        mocker.patch(
            "virtool.utils.generate_key", return_value=("raw_key", "hashed_key")
        )

        client = await spawn_client(authorize=True)

        if has_perm:
            await client.db.users.update_one(
                {"_id": "test"},
                {"$set": {"permissions": {**no_permissions, "create_sample": True}}},
            )

        body = {"name": "Foobar"}

        if req_perm:
            body["permissions"] = {"create_sample": True}

        resp = await client.post("/account/keys", body)

        assert resp.status == 201
        assert await resp.json() == snapshot
        assert await client.db.keys.find_one() == snapshot

    async def test_naming(self, mocker, snapshot, spawn_client, static_time):
        """
        Test that uniqueness is ensured on the ``id`` field.

        """
        mocker.patch(
            "virtool.utils.generate_key", return_value=("raw_key", "hashed_key")
        )

        client = await spawn_client(authorize=True)

        await client.db.keys.insert_one(
            {"_id": "foobar", "id": "foobar_0", "name": "Foobar"}
        )

        body = {"name": "Foobar"}

        resp = await client.post("/account/keys", body)

        assert resp.status == 201
        assert await resp.json() == snapshot
        assert await client.db.keys.find_one({"id": "foobar_1"}) == snapshot


class TestUpdateAPIKey:
    @pytest.mark.parametrize("has_admin", [True, False])
    @pytest.mark.parametrize("has_perm", [True, False])
    async def test(self, has_admin, has_perm, snapshot, spawn_client, static_time):
        client = await spawn_client(authorize=True)

        await client.db.users.update_one(
            {"_id": "test"},
            {
                "$set": {
                    "administrator": has_admin,
                    "permissions.create_sample": True,
                    "permissions.modify_subtraction": has_perm,
                }
            },
        )

        await client.db.keys.insert_one(
            {
                "_id": "foobar",
                "id": "foobar_0",
                "name": "Foobar",
                "created_at": static_time.datetime,
                "user": {"id": "test"},
                "groups": [],
                "permissions": {p: False for p in PERMISSIONS},
            }
        )

        resp = await client.patch(
            "/account/keys/foobar_0",
            {"permissions": {"create_sample": True, "modify_subtraction": True}},
        )

        assert resp.status == 200
        assert await resp.json() == snapshot
        assert await client.db.keys.find_one() == snapshot

    async def test_not_found(self, spawn_client, resp_is):
        client = await spawn_client(authorize=True)

        resp = await client.patch(
            "/account/keys/foobar_0", {"permissions": {"create_sample": True}}
        )

        await resp_is.not_found(resp)


@pytest.mark.parametrize("error", [None, "404"])
async def test_remove_api_key(error, spawn_client, resp_is):
    client = await spawn_client(authorize=True)

    if not error:
        await client.db.keys.insert_one(
            {
                "_id": "foobar",
                "id": "foobar_0",
                "name": "Foobar",
                "user": {"id": "test"},
            }
        )

    resp = await client.delete("/account/keys/foobar_0")

    if error:
        await resp_is.not_found(resp)
        return

    await resp_is.no_content(resp)
    assert await client.db.keys.count_documents({}) == 0


async def test_remove_all_api_keys(spawn_client, resp_is):
    client = await spawn_client(authorize=True)

    await client.db.keys.insert_many(
        [
            {"_id": "hello_world", "id": "hello_world_0", "user": {"id": "test"}},
            {"_id": "foobar", "id": "foobar_0", "user": {"id": "test"}},
            {"_id": "baz", "id": "baz_0", "user": {"id": "fred"}},
        ]
    )

    resp = await client.delete("/account/keys")

    await resp_is.no_content(resp)

    assert await client.db.keys.find().to_list(None) == [
        {"_id": "baz", "id": "baz_0", "user": {"id": "fred"}}
    ]


async def test_logout(spawn_client):
    """
    Test that calling the logout endpoint results in the current session being removed and the user being logged
    out.

    """
    client = await spawn_client(authorize=True)

    # Make sure the session is authorized
    resp = await client.get("/account")
    assert resp.status == 200

    # Logout
    resp = await client.get("/account/logout")
    assert resp.status == 200

    # Make sure that the session is no longer authorized
    resp = await client.get("/account")
    assert resp.status == 401


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/account"),
        ("PATCH", "/account"),
        ("GET", "/account/settings"),
        ("PATCH", "/account/settings"),
        ("PATCH", "/account/settings"),
        ("GET", "/account/keys"),
        ("POST", "/account/keys"),
        ("PATCH", "/account/keys/foobar"),
        ("DELETE", "/account/keys/foobar"),
        ("DELETE", "/account/keys"),
    ],
)
async def test_requires_authorization(method, path, spawn_client):
    """
    Test that a requires authorization 401 response is sent when the session is not authenticated.

    """
    client = await spawn_client()

    if method == "GET":
        resp = await client.get(path)
    elif method == "POST":
        resp = await client.post(path, {})
    elif method == "PATCH":
        resp = await client.patch(path, {})
    else:
        resp = await client.delete(path)

    assert await resp.json() == {
        "id": "unauthorized",
        "message": "Requires authorization",
    }

    assert resp.status == 401


@pytest.mark.parametrize("value", ["valid_permissions", "invalid_permissions"])
async def test_is_permission_dict(value, spawn_client, resp_is):
    """
    Tests that when an invalid permission is used, validators.is_permission_dict raises a 422 error.
    """
    client = await spawn_client(authorize=True)

    permissions = {
        "cancel_job": True,
        "create_ref": True,
        "create_sample": True,
        "modify_hmm": True,
    }

    if value == "invalid_permissions":
        permissions["foo"] = True

    data = {"permissions": permissions}

    resp = await client.patch("/account/keys/foo", data=data)

    if value == "valid_permissions":
        await resp_is.not_found(resp)
    else:
        await resp_is.invalid_input(
            resp, {"permissions": ["keys must be valid permissions"]}
        )


@pytest.mark.parametrize("value", ["valid_email", "invalid_email"])
async def test_is_valid_email(value, spawn_client, resp_is):
    """
    Tests that when an invalid email is used, validators.is_valid_email raises a 422 error.
    """
    client = await spawn_client(authorize=True)

    data = {
        "email": "valid@email.ca" if value == "valid_email" else "-foo-bar-@baz!.ca",
        "old_password": "old_password",
        "password": "password",
    }

    resp = await client.patch("/account", data=data)

    if value == "valid_email":
        await resp_is.bad_request(resp, "Invalid credentials")
    else:
        await resp_is.invalid_input(resp, {"email": ["Not a valid email"]})


@pytest.mark.parametrize("error", [None, "wrong_handle", "wrong_password"])
async def test_login(spawn_client, create_user, resp_is, error, mocker):
    client = await spawn_client()

    await client.db.users.insert_one(
        {
            "user_id": "abc123",
            "handle": "foobar",
            "password": hash_password("p@ssword123"),
        }
    )

    data = {"username": "foobar", "password": "p@ssword123", "remember": False}

    if error == "wrong_password":
        data["password"] = "wr0ngp@ssword"

    if error == "wrong_handle":
        data["username"] = "oops"

    mocker.patch(
        "virtool.users.sessions.replace_session", return_value=[{"_id": None}, None]
    )

    resp = await client.post("/account/login", data=data)

    if error == "wrong_handle" or error == "wrong_password":
        await resp_is.bad_request(resp, "Invalid username or password")
        return

    assert resp.status == 201
    assert await resp.json() == {"reset": False}
