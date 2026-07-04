#!/usr/bin/env bash
# Deploy pyarchinit-mini to Adarte (ganesh@10.0.1.13).
# Uses sshpass with password auth (publickey is disabled because local
# ed25519 key has a passphrase and there's no ssh-askpass in this env).
#
# Usage:
#   ./adarte_deploy.sh                # deploys VERSION below
#   VERSION=2.7.2 ./adarte_deploy.sh  # override
set -euo pipefail

# Secrets are NOT hardcoded here (this repo is public). Put them in a local,
# gitignored .adarte_secrets.sh next to this script (copy .adarte_secrets.sh.example):
#   export ADARTE_SSH_PASS='...'      # ganesh@10.0.1.13 password
#   export ADARTE_DB='postgresql://admin_pyarchinit:...@10.0.1.6:5432/pyarchinit_v2'
SECRETS_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.adarte_secrets.sh"
# shellcheck source=/dev/null
[ -f "$SECRETS_FILE" ] && source "$SECRETS_FILE"

VERSION="${VERSION:-3.4.0}"
HOST="ganesh@10.0.1.13"
PASS="${ADARTE_SSH_PASS:?set ADARTE_SSH_PASS (see .adarte_secrets.sh / .example)}"
VENV="/home/ganesh/pyarchinit_env"
SCREEN_NAME="pmini"
# Start on the production Postgres (pyarchinit_v2, ~1915 sites) and with the
# Werkzeug debugger OFF. Without DATABASE_URL the app falls back to the default
# SQLite (only 3 demo sites); without PYARCHINIT_WEB_DEBUG=false it runs the
# interactive debugger (RCE risk). No quotes around the DSN so it stays safe
# inside the `bash -c '...'` wrapper below.
ADARTE_DB="${ADARTE_DB:?set ADARTE_DB (see .adarte_secrets.sh / .example)}"
# Include the storage-backend encryption key if configured (put it in
# .adarte_secrets.sh: export PYARCHINIT_SECRET_KEY='...'). Without it the
# /settings/storage UI is read-only; media behaviour stays local either way.
KEY_EXPORT=""
[ -n "${PYARCHINIT_SECRET_KEY:-}" ] && KEY_EXPORT="export PYARCHINIT_SECRET_KEY=${PYARCHINIT_SECRET_KEY} && "
SCREEN_CMD="source ${VENV}/bin/activate && export DATABASE_URL=${ADARTE_DB} && export PYARCHINIT_WEB_DEBUG=false && ${KEY_EXPORT}pyarchinit-mini-web"

# Reuse ONE SSH connection for all steps (ControlMaster) so we authenticate
# once. Repeated per-step logins were intermittently rejected
# (ssh_askpass/publickey) right after the long pip-install connection;
# multiplexing avoids that. NumberOfPasswordPrompts=1 prevents retry-storms.
SSH_CTL="/tmp/adarte-deploy-ctl-%h-%p"
SSH_OPTS=(
  -o ConnectTimeout=10
  -o StrictHostKeyChecking=no
  -o PreferredAuthentications=password
  -o PubkeyAuthentication=no
  -o NumberOfPasswordPrompts=1
  -o ServerAliveInterval=5
  -o ServerAliveCountMax=3
  -o ControlMaster=auto
  -o "ControlPath=${SSH_CTL}"
  -o ControlPersist=120
)

remote() {
  local i
  for i in 1 2 3; do
    if sshpass -p "${PASS}" ssh "${SSH_OPTS[@]}" "${HOST}" "$@"; then
      return 0
    fi
    printf '\033[1;33m! ssh attempt %s/3 failed; retrying in 2s\033[0m\n' "$i" >&2
    sleep 2
  done
  return 1
}

# Close the shared master connection on exit (ControlPersist also times out).
_close_master() { sshpass -p "${PASS}" ssh "${SSH_OPTS[@]}" -O exit "${HOST}" 2>/dev/null || true; }
trap _close_master EXIT

step() { printf "\n\033[1;34m=== %s ===\033[0m\n" "$*"; }
ok()   { printf "\033[1;32m✔\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m!\033[0m %s\n" "$*"; }
die()  { printf "\033[1;31m✘ %s\033[0m\n" "$*" >&2; exit 1; }

command -v sshpass >/dev/null || die "sshpass not installed (brew install sshpass)"

step "1/6 Probe current state"
remote "
  echo '--- Venv python: '\$(${VENV}/bin/python --version)
  echo '--- Installed version:'
  ${VENV}/bin/pip show pyarchinit-mini 2>/dev/null | grep -E '^(Name|Version|Location)' || echo 'NOT INSTALLED'
  echo '--- Screens:'
  screen -ls 2>/dev/null || echo '(no screens)'
  echo '--- Web process:'
  pgrep -af 'pyarchinit-mini-web' || echo '(not running)'
"

step "2/6 Quit existing screen '${SCREEN_NAME}' (if any)"
remote "screen -X -S ${SCREEN_NAME} quit 2>/dev/null || true; sleep 1; screen -ls | grep -q ${SCREEN_NAME} && echo 'STILL ALIVE' || echo 'gone'"

step "3/6 Force-reinstall pyarchinit-mini==${VERSION} into venv"
remote "${VENV}/bin/pip install --force-reinstall --no-cache-dir --no-deps -i https://pypi.org/simple/ pyarchinit-mini==${VERSION}" \
  || die "pip install failed"
ok "pip install completed"

step "4/6 Verify installed version"
INSTALLED=$(remote "${VENV}/bin/pip show pyarchinit-mini | awk '/^Version:/ {print \$2}'")
echo "Installed: ${INSTALLED}"
[ "${INSTALLED}" = "${VERSION}" ] || die "Version mismatch: expected ${VERSION}, got '${INSTALLED}'"
ok "Version ${VERSION} confirmed on server"

step "5/6 Restart screen '${SCREEN_NAME}'"
remote "screen -dmS ${SCREEN_NAME} bash -c '${SCREEN_CMD}'"
ok "screen launched"

step "6/6 Wait 6s, verify process + screen"
remote "sleep 6; echo '--- Screens:'; screen -ls; echo; echo '--- Web process:'; pgrep -af 'pyarchinit-mini-web' || echo '(NOT RUNNING - check screen log)'"

step "Done"
ok "Adarte updated to pyarchinit-mini ${VERSION}"
echo "Web UI: http://10.0.1.13:5000  (or whatever default port pyarchinit-mini-web uses)"
echo "To inspect screen output:  ssh ${HOST}  →  screen -r ${SCREEN_NAME}  (Ctrl-A D to detach)"