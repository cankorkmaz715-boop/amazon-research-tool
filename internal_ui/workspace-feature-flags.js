/**
 * Step 225: Feature flags – safe rollout. Fetches flags from API; never crashes UI.
 * Fail closed: if flags not loaded or flag missing, isFeatureEnabled returns false for unknown flags.
 */
(function() {
  var FLAGS = {};
  var LOADED = false;
  var DEFAULTS = {
    demo_mode: true,
    walkthrough_enabled: true,
    onboarding_enabled: true,
    usage_analytics_enabled: true,
    alert_center_enabled: true,
    copilot_context_enabled: true
  };

  function getApiKey() {
    try {
      if (typeof window.__analyticsApiKey === "function") return window.__analyticsApiKey();
      return window.__analyticsApiKey || "";
    } catch (e) { return ""; }
  }

  function load() {
    try {
      var opts = { method: "GET", headers: { "Content-Type": "application/json" } };
      var key = getApiKey();
      if (key) opts.headers["X-API-Key"] = key;
      fetch("/api/feature-flags", opts)
        .then(function(r) { return r.ok ? r.json() : {}; })
        .then(function(body) {
          var data = (body && body.data) && typeof body.data === "object" ? body.data : {};
          FLAGS = data;
          LOADED = true;
        })
        .catch(function() { LOADED = true; });
    } catch (e) { LOADED = true; }
  }

  window.isFeatureEnabled = function(name) {
    if (!name || typeof name !== "string") return false;
    var key = name.trim();
    if (!key) return false;
    if (LOADED && Object.prototype.hasOwnProperty.call(FLAGS, key)) return !!FLAGS[key];
    return DEFAULTS[key] !== undefined ? !!DEFAULTS[key] : false;
  };
  window.getFeatureFlags = function() { return LOADED ? Object.assign({}, FLAGS) : Object.assign({}, DEFAULTS); };

  /* Step 226: User preferences (localStorage); override feature flags when set */
  var PREF_PREFIX = "workspace_pref_";
  window.getUserPreference = function(key) {
    try { return localStorage.getItem(PREF_PREFIX + (key || "")); } catch (e) { return null; }
  };
  window.setUserPreference = function(key, value) {
    try { if (key) localStorage.setItem(PREF_PREFIX + key, String(value)); } catch (e) {}
  };
  window.isSettingEnabled = function(name) {
    var pref = window.getUserPreference(name);
    if (pref !== null && pref !== undefined) return pref === "true";
    return window.isFeatureEnabled(name);
  };

  /* Step 227: Workspace-scoped preferences (localStorage per workspace); no cross-workspace leakage */
  var WORKSPACE_PREFS_PREFIX = "workspace_prefs_";
  window.getWorkspacePreferences = function(workspaceId) {
    if (workspaceId == null || workspaceId === "") return {};
    try {
      var raw = localStorage.getItem(WORKSPACE_PREFS_PREFIX + String(workspaceId));
      if (!raw) return {};
      var o = JSON.parse(raw);
      return typeof o === "object" && o !== null ? o : {};
    } catch (e) { return {}; }
  };
  window.getWorkspacePreference = function(workspaceId, key) {
    var o = window.getWorkspacePreferences(workspaceId);
    return Object.prototype.hasOwnProperty.call(o, key) ? o[key] : null;
  };
  window.setWorkspacePreference = function(workspaceId, key, value) {
    if (workspaceId == null || workspaceId === "" || !key) return;
    try {
      var o = window.getWorkspacePreferences(workspaceId);
      o[key] = value;
      localStorage.setItem(WORKSPACE_PREFS_PREFIX + String(workspaceId), JSON.stringify(o));
    } catch (e) {}
  };

  load();
})();
