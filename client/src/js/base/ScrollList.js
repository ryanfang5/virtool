import React from "react";
import { map } from "lodash-es";
import { LoadingPlaceholder } from "./index";

const getScrollRatio = (innerHeight, scrollY, scrollHeight) => {
    return ((innerHeight + scrollY) / scrollHeight).toFixed(1);
};

export class ScrollList extends React.Component {
    constructor (props) {
        super(props);
        this.scrollList = React.createRef();
    }

    componentDidMount () {
        this.scrollList.current.addEventListener("scroll", this.onScroll);
        window.addEventListener("scroll", this.onScroll, false);
    }

    componentWillUnmount () {
        this.scrollList.current.removeEventListener("scroll", this.onScroll);
        window.removeEventListener("scroll", this.onScroll, false);
    }

    onScroll = () => {
        // Scroll bar reaches the bottom of page when ratio = 1
        // Want to load available page when scroll bar nears the bottom
        
        //const ratio = ((window.innerHeight + window.scrollY) / document.body.scrollHeight).toFixed(1);

        let ratio;

        if (this.props.isElement) {
            ratio = getScrollRatio(
                this.scrollList.current.clientHeight,
                this.scrollList.current.scrollTop,
                this.scrollList.current.scrollHeight
            );
        } else {
            ratio = getScrollRatio(
                window.innerHeight,
                window.scrollY,
                document.body.scrollHeight
            );
        }

        if (this.props.list.length
            && this.props.hasNextPage
            && !this.props.isNextPageLoading
            && (ratio > 0.8)
        ) {
            this.props.loadNextPage(this.props.page + 1);
        }
    };

    render () {
        const { list, rowRenderer, isNextPageLoading, hasNextPage } = this.props;

        return (
            <div ref={this.scrollList} style={this.props.style}>
                {map(list, (item, index) => rowRenderer(index))}
                {(isNextPageLoading && hasNextPage) ? <LoadingPlaceholder margin="20px" /> : null}
            </div>
        );
    }
}
