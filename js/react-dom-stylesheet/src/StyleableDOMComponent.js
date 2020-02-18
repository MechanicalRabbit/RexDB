/**
 * @copyright 2015 Prometheus Research, LLC
 */

import React from 'react';
import PropTypes from 'prop-types';
import getComponentDisplayName from './getComponentDisplayName';

export default class StyleableDOMComponent extends React.Component {

  static Component = null;

  static stylesheet = null;

  static propTypes = {
    variant: PropTypes.object,
    className: PropTypes.string,
    Component: PropTypes.oneOfType([PropTypes.string, PropTypes.func]),
  };

  static style(spec) {
    let self = this;
    return class extends StyleableDOMComponent {
      static displayName = getComponentDisplayName(self);
      static Component = self.Component;
      static stylesheet = self.stylesheet.override(spec);
    };
  }

  render() {
    let {
      variant,
      className: extraClassName,
      Component = this.constructor.Component,
      ...props
    } = this.props;
    let className = this.constructor.stylesheet.asClassName(variant);
    if (extraClassName) {
      className = className + ' ' + extraClassName;
    }
    return (
      <Component
        {...props}
        className={className}
        />
    );
  }

  componentWillMount() {
    this.constructor.stylesheet.use();
  }

  componentWillUnmount() {
    this.constructor.stylesheet.dispose();
  }
}
