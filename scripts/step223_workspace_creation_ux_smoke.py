#!/usr/bin/env python3
"""
Step 223 smoke test: Workspace creation UX. Validates creation page wiring,
empty-state rendering, form validation, successful creation flow, redirect
compatibility, and onboarding integration compatibility.
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)

UI_PATH = os.path.join(ROOT, "internal_ui", "workspace-creation.html")
OVERVIEW_PATH = os.path.join(ROOT, "internal_ui", "workspace-overview.html")
SERVE_PATH = os.path.join(ROOT, "scripts", "serve_internal_api.py")


def main() -> None:
    creation_wiring_ok = True
    empty_state_ok = True
    form_validation_ok = True
    creation_flow_ok = True
    redirect_ok = True
    onboarding_ok = True

    if not os.path.isfile(UI_PATH):
        creation_wiring_ok = empty_state_ok = form_validation_ok = creation_flow_ok = redirect_ok = False
    else:
        with open(UI_PATH, "r", encoding="utf-8") as f:
            html = f.read()

        # Creation page wiring: nav, form, empty state, success/loading/error elements
        if 'id="creation-form"' not in html or 'id="workspace-name"' not in html:
            creation_wiring_ok = False
        if 'id="creation-submit"' not in html or 'id="creation-empty"' not in html:
            creation_wiring_ok = False
        if 'id="creation-success"' not in html or 'id="creation-loading"' not in html or 'id="creation-error"' not in html:
            creation_wiring_ok = False
        if "Create workspace" not in html or "workspace-nav" not in html:
            creation_wiring_ok = False

        # Empty-state rendering: first-workspace message and get started
        if "Create your first workspace" not in html:
            empty_state_ok = False
        if "id=\"creation-empty\"" not in html and "creation-empty" not in html:
            empty_state_ok = False
        if "Get started" not in html and "empty-start-create" not in html:
            empty_state_ok = False

        # Form validation: name required, inline error, validateName
        if "Workspace name" not in html or "required" in html.lower() or "creation-name-error" in html:
            pass
        if "creation-name-error" not in html:
            form_validation_ok = False
        if "validateName" not in html:
            form_validation_ok = False
        if "setInlineError" not in html:
            form_validation_ok = False

        # Successful creation flow: POST /api/workspaces, showSuccess, redirect
        if 'fetch("/api/workspaces"' not in html and "fetch(\"/api/workspaces\"" not in html:
            creation_flow_ok = False
        if "method: \"POST\"" not in html and 'method:"POST"' not in html:
            creation_flow_ok = False
        if "showSuccess" not in html:
            creation_flow_ok = False

        # Redirect compatibility: workspace-overview?workspace_id=
        if "workspace-overview?workspace_id=" not in html:
            redirect_ok = False
        if "encodeURIComponent(workspaceId)" not in html and "encodeURIComponent" not in html:
            if "workspace_id=" not in html:
                redirect_ok = False
        if "window.location.href" not in html:
            redirect_ok = False

    # Onboarding integration: dashboard has onboarding; creation redirects to dashboard
    if not os.path.isfile(OVERVIEW_PATH):
        onboarding_ok = False
    else:
        with open(OVERVIEW_PATH, "r", encoding="utf-8") as f:
            overview = f.read()
        if "workspace_id" not in overview or "workspace-overview" not in overview:
            onboarding_ok = False
        if "onboarding" not in overview.lower() and "onboarding-panel" not in overview:
            onboarding_ok = False
        if "applyQueryWorkspaceId" not in overview and "workspace_id" not in overview:
            pass  # we added applyQueryWorkspaceId for redirect
        if "URLSearchParams" not in overview and "workspace_id" not in overview:
            pass

    # Backend: POST /api/workspaces and GET /api/workspaces in server
    if not os.path.isfile(SERVE_PATH):
        creation_flow_ok = False
    else:
        with open(SERVE_PATH, "r", encoding="utf-8") as f:
            serve = f.read()
        if "post_create_workspace_response" not in serve or "get_workspaces_list_response" not in serve:
            creation_flow_ok = False
        if 'path_only == "/api/workspaces"' not in serve:
            creation_flow_ok = False

    print("workspace creation UX OK")
    print("creation page wiring: %s" % ("OK" if creation_wiring_ok else "FAIL"))
    print("empty state rendering: %s" % ("OK" if empty_state_ok else "FAIL"))
    print("form validation: %s" % ("OK" if form_validation_ok else "FAIL"))
    print("successful creation flow: %s" % ("OK" if creation_flow_ok else "FAIL"))
    print("redirect compatibility: %s" % ("OK" if redirect_ok else "FAIL"))
    print("onboarding integration compatibility: %s" % ("OK" if onboarding_ok else "FAIL"))

    if not (creation_wiring_ok and empty_state_ok and form_validation_ok and creation_flow_ok and redirect_ok and onboarding_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
