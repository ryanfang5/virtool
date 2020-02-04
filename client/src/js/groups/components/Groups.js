import { push } from "connected-react-router";
import { find, get, includes, map, sortBy } from "lodash-es";
import React from "react";
import { InputGroup } from "react-bootstrap";

import { connect } from "react-redux";
import styled from "styled-components";
import {
    BoxGroup,
    Button,
    InputError,
    LoadingPlaceholder,
    Icon,
    DialogBody,
    ModalDialog,
    DialogHeader
} from "../../base";
import { clearError } from "../../errors/actions";
import { routerLocationHasState } from "../../utils/utils";

import { createGroup, removeGroup, setGroupPermission } from "../actions";
import { GroupDetail } from "./Detail";
import Group from "./Group";

const GroupsModalBody = styled(DialogBody)`
    display: grid;
    grid-template-columns: 2fr 3fr;
    grid-column-gap: 15px;
`;

class Groups extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            createGroupId: "",
            spaceError: false,
            submitted: false,
            error: "",
            open: false
        };
    }

    handleModalExited = () => {
        this.setState({
            createGroupId: "",
            spaceError: false,
            submitted: false,
            error: ""
        });

        if (this.props.error) {
            this.props.onClearError("CREATE_GROUP_ERROR");
        }
    };

    handleHide = () => {
        this.props.onHide();
    };

    handleOpen = () => {
        return this.state.open;
    };

    handleChange = e => {
        this.setState({
            createGroupId: e.target.value,
            spaceError: this.state.spaceError && includes(e.target.value, " "),
            submitted: false,
            error: ""
        });

        if (this.props.error) {
            this.props.onClearError("CREATE_GROUP_ERROR");
        }
    };

    handleSubmit = e => {
        e.preventDefault();

        if (this.state.createGroupId === "") {
            this.setState({
                error: "Group id missing"
            });
        } else if (includes(this.state.createGroupId, " ")) {
            this.setState({
                spaceError: true
            });
        } else {
            this.setState(
                {
                    spaceError: false,
                    submitted: true,
                    error: ""
                },
                () => this.props.onCreate(this.state.createGroupId)
            );
        }
    };

    render() {
        if (this.props.groups === null || this.props.users === null) {
            return <LoadingPlaceholder margin="130px" />;
        }

        const groupComponents = map(sortBy(this.props.groups, "id"), group => <Group key={group.id} {...group} />);

        const activeGroup = find(this.props.groups, { id: this.props.activeId });

        let error;

        if (this.state.submitted && this.props.error) {
            error = this.props.error;
        }

        if (this.state.spaceError) {
            error = "Group names may not contain spaces";
        }

        return (
            <ModalDialog
                label="group"
                size="lg"
                show={this.props.show}
                onHide={this.handleHide}
                onExited={this.handleModalExited}
            >
                <DialogHeader>
                    Groups
                    <Icon name="times" onClick={this.handleHide} style={{ color: "grey" }} />
                </DialogHeader>

                <GroupsModalBody>
                    <div>
                        <InputGroup>
                            <InputError
                                type="text"
                                value={this.state.createGroupId}
                                onChange={this.handleChange}
                                placeholder="Group name"
                                error={error || this.state.error}
                            />
                            <InputGroup.Button style={{ verticalAlign: "top", zIndex: "0" }}>
                                <Button type="button" icon="plus-square" bsStyle="primary" onClick={this.handleSubmit}>
                                    &nbsp;Add
                                </Button>
                            </InputGroup.Button>
                        </InputGroup>
                        <br />
                        <BoxGroup>{groupComponents}</BoxGroup>
                    </div>
                    <GroupDetail
                        group={activeGroup}
                        pending={this.props.pending}
                        users={this.props.users}
                        onRemove={this.props.onRemove}
                        onSetPermission={this.props.onSetPermission}
                    />
                </GroupsModalBody>
            </ModalDialog>
        );
    }
}

const mapStateToProps = state => {
    return {
        show: routerLocationHasState(state, "groups"),
        users: state.users.documents,
        groups: state.groups.documents,
        pending: state.groups.pending,
        activeId: state.groups.activeId,
        error: get(state, "errors.CREATE_GROUP_ERROR.message", "")
    };
};

const mapDispatchToProps = dispatch => ({
    onCreate: groupId => {
        dispatch(createGroup(groupId));
    },

    onHide: () => {
        dispatch(push({ ...window.location, state: { groups: false } }));
    },

    onRemove: groupId => {
        dispatch(removeGroup(groupId));
    },

    onSetPermission: (groupId, permission, value) => {
        dispatch(setGroupPermission(groupId, permission, value));
    },

    onClearError: error => {
        dispatch(clearError(error));
    }
});

export default connect(mapStateToProps, mapDispatchToProps)(Groups);
