import { push } from "react-router-redux";

import { apiCall, setPending } from "../sagaUtils";
import { FIND_USERS, GET_USER, CREATE_USER, EDIT_USER, REMOVE_USER } from "../actionTypes";
import * as usersAPI from "./api";
import { takeEvery, takeLatest, throttle, put } from "redux-saga/effects";

function* findUsers(action) {
    yield apiCall(usersAPI.find, action, FIND_USERS);
}

function* getUser(action) {
    yield apiCall(usersAPI.get, action, GET_USER);
}

function* createUser(action) {
    const extraFunc = {
        closeModal: put(
            push(`/administration/users/${action.userId}`, {
                state: { createUser: false }
            })
        )
    };

    yield setPending(apiCall(usersAPI.create, action, CREATE_USER, {}, extraFunc));
}

function* editUser(action) {
    yield setPending(apiCall(usersAPI.edit, action, EDIT_USER));
}

function* removeUser(action) {
    const extraFunc = {
        goBack: put(push("/administration/users"))
    };
    yield setPending(apiCall(usersAPI.remove, action, REMOVE_USER, {}, extraFunc));
}

export function* watchUsers() {
    yield takeLatest(FIND_USERS.REQUESTED, findUsers);
    yield takeEvery(GET_USER.REQUESTED, getUser);
    yield throttle(200, CREATE_USER.REQUESTED, createUser);
    yield takeEvery(EDIT_USER.REQUESTED, editUser);
    yield takeEvery(REMOVE_USER.REQUESTED, removeUser);
}
