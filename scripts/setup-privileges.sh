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

SUDOERS=/etc/sudoers.d/jellybox
{
    echo "$USER_NAME ALL=(root) NOPASSWD: $IFACE_DEST"
    echo "$USER_NAME ALL=(root) NOPASSWD: $WG_DEST"
    echo "$USER_NAME ALL=(root) NOPASSWD: $SNIFF_DEST"
    echo "$USER_NAME ALL=(root) NOPASSWD: /usr/bin/systemctl reboot"
} > "$SUDOERS"
chmod 0440 "$SUDOERS"
if ! visudo -cf "$SUDOERS"; then
    rm -f "$SUDOERS"
    echo "sudoers validation failed; aborted" >&2
    exit 1
fi

echo "Installed helpers: $IFACE_DEST, $WG_DEST, $SNIFF_DEST"
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
