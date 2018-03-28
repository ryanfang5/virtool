/**
 * @license
 * The MIT License (MIT)
 * Copyright 2015 Government of Canada
 *
 * @author
 * Ian Boyes
 *
 * @exports IsolateAdd
 */
import React from "react";
import { connect } from "react-redux";
import { Modal } from "react-bootstrap";

import { editIsolate, hideVirusModal } from "../../actions";
import { Button } from "../../../base";
import IsolateForm from "./IsolateForm";

const getInitialState = props => ({
    sourceType: props.sourceType || (props.restrictSourceTypes ? "unknown" : ""),
    sourceName: props.sourceName || ""
});

class EditIsolate extends React.Component {

    constructor (props) {
        super(props);
        this.state = getInitialState(this.props);
    }

    componentWillReceiveProps (nextProps) {
        this.setState(getInitialState(nextProps));
    }

    handleChange = (update) => {
        this.setState(update);
    };

    handleSubmit = () => {
        this.props.onSave(
            this.props.virusId,
            this.props.isolateId,
            this.state.sourceType,
            this.state.sourceName
        );
    };

    render () {
        return (
            <Modal bsStyle="warning" show={this.props.show} onEntered={this.modalEntered} onHide={this.props.onHide}>
                <Modal.Header onHide={this.props.onHide} closeButton>
                    Edit Isolate
                </Modal.Header>
                <Modal.Body>
                    <IsolateForm
                        sourceType={this.state.sourceType}
                        sourceName={this.state.sourceName}
                        allowedSourceTypes={this.props.allowedSourceTypes}
                        restrictSourceTypes={this.props.restrictSourceTypes}
                        onChange={this.handleChange}
                        onSubmit={this.handleSubmit}
                    />
                </Modal.Body>
                <Modal.Footer>
                    <Button bsStyle="primary" icon="floppy" onClick={this.handleSubmit}>
                        Save
                    </Button>
                </Modal.Footer>
            </Modal>
        );
    }
}

const mapStateToProps = state => ({
    show: state.viruses.editIsolate,
    allowedSourceTypes: state.settings.data.allowed_source_types,
    restrictSourceTypes: state.settings.data.restrict_source_types
});

const mapDispatchToProps = dispatch => ({

    onHide: () => {
        dispatch(hideVirusModal());
    },

    onSave: (virusId, isolateId, sourceType, sourceName) => {
        dispatch(editIsolate(virusId, isolateId, sourceType, sourceName));
    }

});

export default connect(mapStateToProps, mapDispatchToProps)(EditIsolate);
