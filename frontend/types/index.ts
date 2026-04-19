export type ConnectionDetails = {
  serverUrl: string;
  participantToken: string;
  roomName: string;
  participantIdentity: string;
};

export type ScenarioDetails = {
  title: string;
  description: string;
  highlights: string[];
};

export type LiveWidgetStatus = "info" | "success" | "warning";

export type LiveWidgetField = {
  label: string;
  value: string;
};

export type LiveWidget = {
  id: string;
  type: string;
  title: string;
  status: LiveWidgetStatus;
  description: string;
  data: LiveWidgetField[];
  highlights: string[];
};

export type LiveWidgetRpcPayload =
  | {
      action: "clear";
    }
  | {
      action: "replace";
      widgets: LiveWidget[];
    }
  | {
      action: "upsert";
      widget: LiveWidget;
    };
