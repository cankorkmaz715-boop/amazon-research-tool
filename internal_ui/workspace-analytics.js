/**
 * Step 224: Basic usage analytics – non-blocking page and action tracking.
 * Never throws; analytics failure must not break UI.
 */
(function() {
  function send(eventName, metadata, workspaceId) {
    try {
      var payload = { event_name: eventName, workspace_id: workspaceId != null ? workspaceId : null };
      if (metadata && typeof metadata === "object") payload.metadata = metadata;
      var apiKey = typeof window.__analyticsApiKey === "function" ? window.__analyticsApiKey() : (window.__analyticsApiKey || "");
      var opts = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        keepalive: true
      };
      if (apiKey) opts.headers["X-API-Key"] = apiKey;
      fetch("/api/analytics/events", opts).catch(function() {});
    } catch (e) {}
  }
  function getWorkspaceId() {
    try {
      if (typeof window.__workspaceIdForAnalytics === "function") return window.__workspaceIdForAnalytics();
      if (window.__workspaceIdForAnalytics != null) return window.__workspaceIdForAnalytics;
      var el = document.getElementById("workspace-id");
      return (el && el.value) ? parseInt(el.value, 10) : null;
    } catch (e) { return null; }
  }
  window.trackPageView = function(eventName) {
    send(eventName || "", null, getWorkspaceId());
  };
  window.trackEvent = function(eventName, metadata) {
    send(eventName || "", metadata || null, getWorkspaceId());
  };
})();
