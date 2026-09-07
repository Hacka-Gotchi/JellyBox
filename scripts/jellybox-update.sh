#!/usr/bin/env bash
# JellyBox self-updater. Runs inside jellybox-update@<tag>.service (as root),
# independent of jellybox.service, so restarting the app cannot kill this script
# mid-rollback. It checks out a validated release tag, sanity-checks it, restarts
# JellyBox, health-checks the result, and rolls back to the previous revision if
# the new version does not come up healthy.
set -uo pipefail

TAG="${1:-}"
REPO_DIR="__REPO_DIR__"
HEARTBEAT="/run/jellybox/heartbeat"

log() { echo "jellybox-update: $*"; }

# Re-validate the tag here; the systemd instance name (%i) is untrusted input.
if [[ ! "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    log "invalid tag: $TAG"; exit 2
fi
cd "$REPO_DIR" 2>/dev/null || { log "no repo at $REPO_DIR"; exit 2; }
[ -d .git ] || { log "not a git checkout"; exit 2; }

KNOWN_GOOD="$(git rev-parse HEAD)"
log "known-good revision = $KNOWN_GOOD"

git fetch --tags --quiet origin || { log "git fetch failed"; exit 1; }
if ! git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
    log "release tag not found: $TAG"; exit 2
fi

# Reinstall Python deps only when requirements actually changed for this release.
REQ_CHANGED=0
git diff --quiet "$KNOWN_GOOD" "refs/tags/$TAG" -- requirements-pi.txt || REQ_CHANGED=1

git checkout -q --force "refs/tags/$TAG" || { log "checkout failed"; exit 1; }

if [ "$REQ_CHANGED" = "1" ]; then
    log "requirements changed; installing"
    pip3 install --break-system-packages -r requirements-pi.txt || log "pip reported errors"
fi

rollback() {
    log "rolling back to $KNOWN_GOOD"
    git checkout -q --force "$KNOWN_GOOD"
    systemctl restart jellybox
}

# Sanity check: the new tree must at least compile.
if ! python3 -m compileall -q core hardware network system ui main.py; then
    log "compile check failed"; rollback; exit 1
fi

restarts_before="$(systemctl show -p NRestarts --value jellybox 2>/dev/null || echo 0)"
systemctl restart jellybox
sleep 8

healthy=1
systemctl is-active --quiet jellybox || healthy=0

restarts_after="$(systemctl show -p NRestarts --value jellybox 2>/dev/null || echo 0)"
if [ "$(( ${restarts_after:-0} - ${restarts_before:-0} ))" -gt 0 ]; then
    healthy=0  # systemd had to auto-restart it -> it crashed
fi

if [ -f "$HEARTBEAT" ]; then
    age=$(( $(date +%s) - $(stat -c %Y "$HEARTBEAT") ))
    [ "$age" -le 20 ] || healthy=0  # UI didn't refresh -> not really up
else
    healthy=0
fi

if [ "$healthy" != "1" ]; then
    log "unhealthy after update"; rollback; exit 1
fi

log "updated to $TAG successfully"
