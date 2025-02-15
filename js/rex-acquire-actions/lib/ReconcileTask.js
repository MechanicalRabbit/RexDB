/**
 * @copyright 2016, Prometheus Research, LLC
 */

import React from "react";

import { Reconciler } from "rex-forms";
import {
  showNotification,
  removeNotification,
  Notification
} from "rex-widget/ui";
import * as rexui from "rex-ui";
import { withFetch } from "rex-widget/data";

import ChannelChooser from "./ChannelChooser";
import I18NAction from "./I18NAction";
import TaskError from "./TaskError";
import Title from "./Title";

export default withFetch(
  class ReconcileTask extends React.Component {
    static defaultProps = {
      icon: "pencil"
    };

    static renderTitle({ title, entity }, context) {
      return <Title title={title} subtitle={context[entity.name].id} />;
    }

    constructor(props) {
      super(props);
      this.state = {
        currentChannel: props.initialChannel
      };
    }

    onChannelChange = channel => {
      this.setState({
        currentChannel: channel
      });
    };

    onReconcilerComplete = reconState => {
      let payload = JSON.stringify({
        task_id: this.props.context[this.props.entity.name].id,
        data: reconState.solution
      });

      let notification = showNotification(
        <Notification kind="info" text="Reconciling Task..." />
      );
      this.props.reconcileTask
        .data(payload)
        .produce()
        .then(
          data => {
            if (data.status === "SUCCESS") {
              let previousEntity = this.props.context[this.props.entity.name];
              this.props.data
                .produceEntity({ "*": previousEntity.id })
                .then(newEntity => {
                  removeNotification(notification);
                  showNotification(
                    <Notification
                      kind="success"
                      text="The Task has been reconciled."
                    />,
                    10000
                  );
                  this.props.onEntityUpdate(previousEntity, newEntity);
                });
            } else {
              removeNotification(notification);
              showNotification(
                <Notification kind="danger" text={data.details} />
              );
            }
          },

          err => {
            removeNotification(notification);
            showNotification(<Notification kind="danger" text={err} />);
          }
        );
    };

    render() {
      let { title, locale, i18nBaseUrl, widgetConfig } = this.props;
      let { displayData } = this.props.fetched;
      let { currentChannel } = this.state;

      if (displayData.updating) {
        return <rexui.PreloaderScreen />;
      }
      if (displayData.data.error) {
        let content;
        if (displayData.data.error === "NO_DISCREPANCIES") {
          content = <p>TODO</p>;
        } else {
          content = <TaskError errorCode={displayData.data.error} />;
        }
        return (
          <I18NAction title={title} locale={locale} i18nBaseUrl={i18nBaseUrl}>
            {content}
          </I18NAction>
        );
      }

      let { instrument, parameters, discrepancies, entries } = displayData.data;

      let initialChannel;
      let channels = this.props.channels.filter(channel => {
        if (channel.uid === this.props.initialChannel) {
          initialChannel = channel.uid;
        }
        return displayData.data.forms[channel.uid] !== undefined;
      });
      if (!initialChannel) {
        initialChannel = channels[0].uid;
      }
      currentChannel = currentChannel || initialChannel;

      let form = displayData.data.forms[currentChannel];
      let hasMultipleForms = Object.keys(displayData.data.forms).length > 0;

      return (
        <I18NAction title={title} locale={locale} i18nBaseUrl={i18nBaseUrl}>
          {hasMultipleForms && (
            <ChannelChooser
              channels={channels}
              initialChannel={initialChannel}
              onChange={this.onChannelChange}
            />
          )}
          <Reconciler
            widgetConfig={widgetConfig}
            key={currentChannel}
            instrument={instrument}
            form={form}
            parameters={parameters}
            discrepancies={discrepancies}
            entries={entries}
            onComplete={this.onReconcilerComplete}
            apiUrls={{
              resourcePrefix: this.props.resourcePrefixUrl,
              lookup: this.props.lookupField.path
            }}
          />
        </I18NAction>
      );
    }
  },
  function({ displayData, entity, context }) {
    displayData = displayData.params({
      task_id: context[entity.name].id
    });
    return { displayData };
  }
);
