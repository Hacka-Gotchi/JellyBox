# JellyBox Tools

The main menu covers the top-level areas; the network tools live under **TOOLS**.

## Main menu

| Item        | Purpose                                                          |
| ----------- | --------------------------------------------------------------- |
| NETWORK INFO| Active interface, IPv4, gateway, MAC, and current Wi-Fi SSID/signal |
| SSH         | Shows how to reach this device over SSH (`user@ip`)             |
| SYSTEM INFO | CPU, temperature, memory, disk, uptime, load                    |
| HARDWARE    | Network interfaces and USB devices, with per-device actions     |
| TERMINAL    | On-device command console                                       |
| TOOLS       | Network tools (below)                                           |
| SETTINGS    | Theme, brightness, Wi-Fi, saved networks                        |
| REBOOT      | Reboot the device (with confirmation)                           |

## TOOLS submenu

Order: WIFI SCAN, PING, TRACEROUTE, NMAP, LLDP, VLAN, MAC SPOOF, WIREGUARD, RESULTS.

### Wi-Fi Scan / Connect
- **Dependency:** `nmcli` (NetworkManager)
- **Purpose:** scan nearby networks and connect to one. Secured networks prompt
  for a password via the on-screen keyboard.
- **Privilege:** connecting/forgetting networks needs NetworkManager control,
  granted by the polkit rule that `setup-privileges.sh` installs.
- **Notes:** connecting on the interface that carries your remote session (e.g.
  the onboard Wi-Fi over SSH) will drop that session. Select an external adapter
  in HARDWARE to work on a spare interface.

### Ping
- **Dependency:** `ping` (iputils-ping)
- **Purpose:** ping an editable target; replies stream in live and BACK cancels.

### Traceroute
- **Dependency:** `traceroute`
- **Purpose:** trace the path to a target; hops stream on-device. Uses the
  default (unprivileged) UDP mode. Results can be saved to RESULTS.

### Nmap
- **Dependency:** `nmap`
- **Purpose:** port scan an editable target with editable arguments (default
  `-Pn -F -T4`). Runs an unprivileged connect scan. Results can be saved.
- **Notes:** invalid arguments are reported as `ARG ERROR!`.

### LLDP Discovery
- **Dependency:** `lldpd` / `lldpctl`
- **Purpose:** show LLDP advertised by neighboring network infrastructure —
  device/system name, port, VLAN, and management address.
- **Limitations:** LLDP advertisements must actually be present on the interface,
  and lldpd may need a few seconds after link-up to collect them. Not all
  equipment advertises LLDP.

### VLAN Detection
- **Dependency:** `tcpdump`
- **Privilege:** uses the restricted `jellybox-sniff` helper.
- **Purpose:** observe 802.1Q-tagged frames on the selected interface and report
  the VLAN IDs seen.
- **Limitations:** tagged frames must actually reach JellyBox. An ordinary
  untagged access port exposes no VLAN tags; a trunk/tagged interface is needed.
  This reports only VLANs seen in captured traffic, not every VLAN configured on
  the network.

### MAC Spoof
- **Dependency:** `iproute2` (`ip`); `ethtool` for reading the permanent MAC
- **Privilege:** uses the restricted `jellybox-iface` helper.
- **Purpose:** set a random, custom, or the permanent MAC on the selected
  interface.
- **Notes:** changing the MAC on the interface carrying your session will drop
  it. RESET restores the permanent MAC via `ethtool`, falling back to the MAC
  seen when the page opened.

### WireGuard
- **Dependency:** `wireguard-tools` (`wg`, `wg-quick`), tunnels in `/etc/wireguard`
- **Privilege:** uses the restricted `jellybox-wg` helper.
- **Purpose:** list configured tunnels, show status, and bring one up/down.
- **Notes:** configs are created over SSH; JellyBox only controls them. A
  full-tunnel config routes all traffic through the VPN.

### Results
- **Purpose:** browse scan output saved from Nmap and Traceroute (stored under
  `data/scans/`).

## Hardware actions

The HARDWARE screen lists interfaces and USB devices. Selecting a Wi-Fi
interface offers actions including **USE FOR SCAN** (make it the working
interface) and **MONITOR MODE** on/off where the driver supports it (via the
`jellybox-iface` helper).
