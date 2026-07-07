/**
 * Injected as an inline <script> into every executable artifact before it runs.
 * Runs inside the sandboxed iframe (allow-scripts, no allow-same-origin), so
 * event.origin from window.parent's perspective is the literal string "null" —
 * the parent identifies this frame by window reference, not origin.
 */
export const BRIDGE_CLIENT_SOURCE = `
(function () {
  "use strict";

  var pending = Object.create(null);
  var subscribers = Object.create(null);
  var reqCounter = 0;

  function nextId() {
    reqCounter += 1;
    return "req-" + Date.now() + "-" + reqCounter;
  }

  function request(module, method, params) {
    return new Promise(function (resolve, reject) {
      var id = nextId();
      pending[id] = { resolve: resolve, reject: reject };
      window.parent.postMessage(
        { type: "bridge_request", id: id, module: module, method: method, params: params || {} },
        "*"
      );
    });
  }

  window.addEventListener("message", function (event) {
    var msg = event.data;
    if (!msg || typeof msg !== "object") return;

    if (msg.type === "bridge_response") {
      var entry = pending[msg.id];
      if (!entry) return;
      delete pending[msg.id];
      if (msg.status === "success") entry.resolve(msg.data);
      else entry.reject(new Error((msg.error && msg.error.message) || "Bridge request failed"));
      return;
    }

    if (msg.type === "bridge_event") {
      var handlers = subscribers[msg.event] || [];
      handlers.forEach(function (handler) {
        try {
          handler(msg.data);
        } catch (e) {
          /* one subscriber's error must not affect others */
        }
      });
    }
  });

  window.bridge = {
    dataset: {
      get: function (datasetId) {
        return request("dataset", "get", { dataset_id: datasetId });
      },
    },
    widget: {
      execute: function (widgetId) {
        return request("widget", "execute", { widget_id: widgetId });
      },
    },
    artifact: {
      save: function (content) {
        return request("artifact", "save", { content: content });
      },
    },
    workspace: {
      emit: function (event, data) {
        return request("workspace", "emit", { event: event, data: data });
      },
    },
    events: {
      subscribe: function (event, handler) {
        if (!subscribers[event]) subscribers[event] = [];
        subscribers[event].push(handler);
        return function unsubscribe() {
          subscribers[event] = (subscribers[event] || []).filter(function (h) {
            return h !== handler;
          });
        };
      },
    },
  };

  // ---- Error reporting: surfaces JS errors to the parent's Error Boundary
  // instead of leaving a silently broken iframe. ----
  window.addEventListener("error", function (event) {
    window.parent.postMessage(
      { type: "canvas_error", message: String(event.message || "Unknown error"), source: "error" },
      "*"
    );
  });
  window.addEventListener("unhandledrejection", function (event) {
    var reason = event.reason;
    var message = (reason && reason.message) || reason || "Unhandled promise rejection";
    window.parent.postMessage(
      { type: "canvas_error", message: String(message), source: "unhandledrejection" },
      "*"
    );
  });

  // ---- Resource limits ----
  var MAX_DOM_NODES = 10000;
  var HEARTBEAT_INTERVAL_MS = 2000;

  setInterval(function () {
    var nodeCount = document.getElementsByTagName("*").length;
    window.parent.postMessage({ type: "canvas_heartbeat", domNodeCount: nodeCount }, "*");
    if (nodeCount > MAX_DOM_NODES) {
      window.parent.postMessage(
        {
          type: "canvas_error",
          message: "DOM node limit exceeded (" + nodeCount + " > " + MAX_DOM_NODES + ")",
          source: "dom_limit",
        },
        "*"
      );
    }
  }, HEARTBEAT_INTERVAL_MS);

  // A true synchronous infinite loop blocks this thread entirely, so the
  // heartbeat above simply stops firing — the parent's absence-of-heartbeat
  // timeout is what actually kills those. This guards the more common case of
  // a runaway animation loop that keeps the thread free but re-renders wildly.
  var rafCallsThisSecond = 0;
  var rafWindowStart = Date.now();
  var MAX_RAF_PER_SECOND = 500;
  var nativeRAF = window.requestAnimationFrame ? window.requestAnimationFrame.bind(window) : null;
  if (nativeRAF) {
    window.requestAnimationFrame = function (callback) {
      var now = Date.now();
      if (now - rafWindowStart > 1000) {
        rafWindowStart = now;
        rafCallsThisSecond = 0;
      }
      rafCallsThisSecond += 1;
      if (rafCallsThisSecond > MAX_RAF_PER_SECOND) {
        window.parent.postMessage(
          {
            type: "canvas_error",
            message: "requestAnimationFrame call rate exceeded (" + MAX_RAF_PER_SECOND + "/s)",
            source: "render_limit",
          },
          "*"
        );
        return 0;
      }
      return nativeRAF(callback);
    };
  }

  window.parent.postMessage({ type: "canvas_ready" }, "*");
})();
`;
