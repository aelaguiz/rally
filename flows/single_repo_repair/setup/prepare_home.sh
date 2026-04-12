#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
FLOW_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)
FIXTURE_ROOT="${FLOW_ROOT}/fixtures/tiny_issue_service"

: "${RALLY_FLOW_HOME:?RALLY_FLOW_HOME must be set}"
: "${RALLY_ISSUE_PATH:?RALLY_ISSUE_PATH must be set}"

mkdir -p "${RALLY_FLOW_HOME}/repos" "${RALLY_FLOW_HOME}/artifacts"
rm -rf "${RALLY_FLOW_HOME}/repos/tiny_issue_service"
cp -R "${FIXTURE_ROOT}" "${RALLY_FLOW_HOME}/repos/tiny_issue_service"

cat >> "${RALLY_ISSUE_PATH}" <<'EOF'

## Setup Notes

- Prepared `home/repos/tiny_issue_service` from the flow fixture repo.
- This fixture carries a deterministic pagination bug where page 1 skips the first item.
- Write the repair plan to `home/artifacts/repair_plan.md`.
- Write the verification record to `home/artifacts/verification.md`.
EOF
