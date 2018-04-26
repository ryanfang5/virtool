import React from "react";
import { Switch, Route } from "react-router-dom";
import { connect } from "react-redux";

import ReferenceList from "./List";
import ReferenceDetail from "./Detail/Detail";
import { LoadingPlaceholder } from "../../base";
import SourceTypes from "../../settings/components/General/SourceTypes";
import InternalControl from "../../settings/components/General/InternalControl";

const ReferenceSettings = () => (
    <div>
        <h3 className="view-header">
            <strong>
                Settings
            </strong>
        </h3>
        <SourceTypes />
        <InternalControl />
    </div>
);

const Viruses = (props) => {
    if (props.settings === null) {
        return <LoadingPlaceholder />;
    }

    return (
        <div className="container">
            <Switch>
                <Route path="/refs" component={ReferenceList} exact />
                <Route path="/viruses/settings" component={ReferenceSettings} />
                <Route path="/refs/:refId" component={ReferenceDetail} />
            </Switch>
        </div>
    );
};

const mapStateToProps = (state) => ({
    settings: state.settings.data
});

export default connect(mapStateToProps)(Viruses);
