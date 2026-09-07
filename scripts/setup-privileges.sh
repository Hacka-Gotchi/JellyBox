#!/usr/bin/env bash
# One-time setup so JellyBox can run its few privileged actions (monitor mode,
# MAC change, VLAN sniff, WireGuard control, reboot) without running the whole
# app as root. Installs
# the helpers root-owned and grants ONLY those commands passwordless sudo for the
# app user. Run once:  sudo bash scripts/setup-privileges.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="${SUDO_USER:-$(id -un)}"
IFACE_DEST=/usr/local/sbin/jellybox-iface
WG_DEST=/usr/local/sbin/jellybox-wg
SNIFF_DEST=/usr/local/sbin/jellybox-sniff

install -o root -g root -m 0755 "$APP_DIR/scripts/jellybox-iface" "$IFACE_DEST"
install -o root -g root -m 0755 "$APP_DIR/scripts/jellybox-wg" "$WG_DEST"
install -o root -g root -m 0755 "$APP_DIR/scripts/jellybox-sniff" "$SNIFF_DEST"

# Self-updater: a root-owned script plus an independent systemd unit. The unit
# runs outside jellybox.service so restarting the app during an update cannot
# kill the updater mid-rollback.
UPDATE_DEST=/usr/local/sbin/jellybox-update
sed "s#__REPO_DIR__#$APP_DIR#g" "$APP_DIR/scripts/jellybox-update.sh" > "$UPDATE_DEST"
chown root:root "$UPDATE_DEST"; chmod 0755 "$UPDATE_DEST"
install -o root -g root -m 0644 "$APP_DIR/jellybox-update@.service" /etc/systemd/system/jellybox-update@.service
systemctl daemon-reload 2>/dev/null || true

# Per-device config lives outside the source tree so updates never touch it.
install -d -m 0755 /etc/jellybox
if [ ! -f /etc/jellybox/device.json ]; then
    cat > /etc/jellybox/device.json <<'JSON'
{
  "display": { "x_offset": 0, "y_offset": 0, "rotate": 0 }
}
JSON
fi

SUDOERS=/etc/sudoers.d/jellybox
{
    echo "$USER_NAME ALL=(root) NOPASSWD: $IFACE_DEST"
    echo "$USER_NAME ALL=(root) NOPASSWD: $WG_DEST"
    echo "$USER_NAME ALL=(root) NOPASSWD: $SNIFF_DEST"
    echo "$USER_NAME ALL=(root) NOPASSWD: /usr/bin/systemctl reboot"
    echo "$USER_NAME ALL=(root) NOPASSWD: /usr/bin/systemctl start jellybox-update@*"
} > "$SUDOERS"
chmod 0440 "$SUDOERS"
if ! visudo -cf "$SUDOERS"; then
    rm -f "$SUDOERS"
    echo "sudoers validation failed; aborted" >&2
    exit 1
fi

echo "Installed helpers: $IFACE_DEST, $WG_DEST, $SNIFF_DEST, $UPDATE_DEST"
echo "Granted passwordless sudo for '$USER_NAME' to run only those helpers."

# Allow the app user to control NetworkManager (needed to connect to Wi-Fi from
# a non-local session, e.g. over SSH or as the service). Without this, nmcli
# returns "Not authorized to control networking".
POLKIT=/etc/polkit-1/rules.d/50-jellybox-nm.rules
cat > "$POLKIT" <<POLKIT_EOF
polkit.addRule(function(action, subject) {
  if (action.id.indexOf("org.freedesktop.NetworkManager.") == 0 &&
      subject.user == "$USER_NAME") {
    return polkit.Result.YES;
  }
});
POLKIT_EOF
systemctl restart polkit 2>/dev/null || true
echo "Granted '$USER_NAME' NetworkManager control (Wi-Fi connect)."

echo "Monitor mode, MAC spoof, WireGuard control, reboot, and Wi-Fi connect will now work on-device."
