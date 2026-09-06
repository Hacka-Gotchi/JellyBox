# Installing JellyBox

These steps target a fresh Raspberry Pi OS installation on a Raspberry Pi
Zero 2 W.

The steps below cover the complete process from flashing Raspberry Pi OS through
installation, verification, and troubleshooting.

## 1. Flash Raspberry Pi OS

Use **Raspberry Pi Imager** on your PC.

Choose:

1. **Device:** Raspberry Pi Zero 2 W
2. **Operating System:** Raspberry Pi OS (other) → **Raspberry Pi OS Lite (64-bit)**
3. Open **Edit Settings** before writing the image and configure:
   - Hostname, for example `jellybox`
   - Username `user`
   - A password
   - Wi-Fi SSID and password
   - Your Wi-Fi country/region
   - **Enable SSH**
   - Enable password authentication if you want to sign in using the password you set

Using the username `user` matches JellyBox's default service configuration and
paths. If you use another username, update the service configuration accordingly.

Write the image to the microSD card, insert it into the Pi Zero 2 W, and power
the device on.

After the first boot, connect over SSH:

```bash
ssh user@jellybox.local
```

If hostname resolution is unavailable, use the Pi's IP address instead:

```bash
ssh user@<ip-address>
```

## 2. Install Git and clone the project

Install Git:

```bash
sudo apt update
sudo apt install -y git
```

Then clone JellyBox:

```bash
git clone https://github.com/Hacka-Gotchi/JellyBox.git jellybox
cd jellybox
```

For the automated installation, run:

```bash
sudo bash scripts/install-pi.sh
```

The remaining steps document the equivalent setup manually.


## 3. Install Linux packages

These provide the external tools JellyBox uses:

```bash
sudo apt update
sudo apt install -y \
  python3-pip network-manager iw iputils-ping openssh-client \
  traceroute nmap tcpdump lldpd ethtool wireguard-tools
```

`network-manager` provides `nmcli` for Wi-Fi management,
`iputils-ping` provides `ping`, and `openssh-client` provides `ssh`.
`lldpd` and `tcpdump` support LLDP and VLAN detection.

## 4. Install Python packages

```bash
python3 -m pip install -r requirements-pi.txt --break-system-packages
```

## 5. Enable SPI

The Waveshare LCD uses SPI:

```bash
sudo raspi-config nonint do_spi 0
```

## 6. Configure the privileged helpers

```bash
sudo bash scripts/setup-privileges.sh
```

This installs the root-owned helpers:

- `jellybox-iface`
- `jellybox-sniff`
- `jellybox-wg`

It also grants the required passwordless `sudo` permissions, installs the
NetworkManager polkit rule used by JellyBox Wi-Fi features, and whitelists the
specific `systemctl reboot` command.

JellyBox itself continues to run as your normal user.

See [SECURITY.md](../SECURITY.md) for details about the privilege model.

## 7. Run JellyBox

```bash
python3 main.py
```

You should see the boot animation followed by the main menu.

Use the joystick and hardware keys to navigate. See
[CONTROLS.md](CONTROLS.md) for the control mapping.

## 8. Run on boot

`scripts/install-pi.sh` already installs and enables the JellyBox systemd
service automatically.

To configure it manually:

```bash
sudo cp jellybox.service /etc/systemd/system/jellybox.service
# Edit User= and the paths in the unit if your install directory or user differ.
sudo systemctl daemon-reload
sudo systemctl enable --now jellybox
```

View the JellyBox service log with:

```bash
sudo journalctl -u jellybox -f
```

## 9. Verify

Check that:

- The menu shows an Ethernet and/or Wi-Fi indicator when connected.
- **SYSTEM INFO** shows live CPU, temperature, memory, and storage information.
- **TOOLS → PING** can reach a known host.
- The display and hardware controls respond correctly.

## Troubleshooting

- **Cannot SSH to `jellybox.local`** — check your router for the Pi's IP address
  and connect with:

  ```bash
  ssh user@<ip-address>
  ```

- **Wi-Fi does not start** — make sure the correct Wi-Fi country/region was set
  in Raspberry Pi Imager before flashing.

- **Nothing appears on the display** — confirm SPI is enabled and the LCD HAT is
  fully seated on the GPIO header.

- **Image is shifted or has a coloured edge** — adjust `LCD_H_OFFSET` and
  `LCD_V_OFFSET` in `hardware/pi/pins.py`. Small values such as 1–3 may be
  required for some LCD panel batches. If red and blue are swapped, check
  `LCD_BGR`.

- **A tool reports "not found"** — install the corresponding Linux package from
  step 3. See [TOOLS.md](TOOLS.md) for tool-specific dependencies.

- **Wi-Fi, monitor mode, MAC changes, or VLAN detection fail with a permission
  error** — re-run:

  ```bash
  sudo bash scripts/setup-privileges.sh
  ```

- **`GPIO not allocated` when starting JellyBox manually** — the systemd service
  may already be using the GPIO pins. Stop it first:

  ```bash
  sudo systemctl stop jellybox
  ```

Do not run JellyBox itself with `sudo`. It is designed to run as an ordinary
user and elevate only the specific operations that require additional
privileges.
