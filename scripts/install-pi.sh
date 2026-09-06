#!/usr/bin/env bash
# Install JellyBox on a Raspberry Pi: system packages, Python packages, SPI,
# privileged helpers, and the systemd service. Run from the project root:
#   sudo bash scripts/install-pi.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_USER="${SUDO_USER:-$(id -un)}"

echo "Installing JellyBox from ${APP_DIR} for user ${SERVICE_USER}"

# 1. System packages used by the tools. network-manager provides nmcli;
#    iputils-ping provides ping; openssh-client provides ssh.
apt-get update
apt-get install -y \
    python3-pip \
    network-manager \
    iw \
    iputils-ping \
    openssh-client \
    traceroute \
    nmap \
    tcpdump \
    lldpd \
    ethtool \
    wireguard-tools

# 2. Python packages
sudo -u "${SERVICE_USER}" pip3 install --break-system-packages -r "${APP_DIR}/requirements-pi.txt"

# 3. Enable SPI for the LCD
raspi-config nonint do_spi 0 || echo "enable SPI manually via raspi-config"

# 4. Privileged helpers (monitor mode, MAC change, VLAN sniff, WireGuard, reboot)
bash "${APP_DIR}/scripts/setup-privileges.sh"

# 5. systemd service
sed -e "s#/home/pi/jellybox#${APP_DIR}#g" \
    -e "s#^User=pi#User=${SERVICE_USER}#" \
    "${APP_DIR}/jellybox.service" > /etc/systemd/system/jellybox.service
systemctl daemon-reload
systemctl enable jellybox.service

echo
echo "Done. Start now with:   sudo systemctl start jellybox"
echo "Follow logs with:       journalctl -u jellybox -f"
