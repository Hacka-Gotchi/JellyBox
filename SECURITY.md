# Security & Responsible Use

## Intended use

JellyBox is a tool for network administration, diagnostics, authorized security
testing, red-team operations, and education — for use systems you own or are
explicitly authorized to assess.

Some features can be used in offensive-security workflows, including network
discovery, wireless analysis, monitor mode, MAC changes, VLAN inspection, and
the terminal. Use JellyBox only within the scope of your authorization and
follow the rules of engagement for the environment you are testing.

## Privilege model

JellyBox runs as an ordinary user. Operations that require elevated privileges
are handled by small, root-owned helper scripts installed by
`scripts/setup-privileges.sh`:

- `jellybox-iface` — switch supported interfaces between managed/monitor mode
  and change MAC addresses
- `jellybox-sniff` — run the restricted packet capture used for VLAN detection
- `jellybox-wg` — list WireGuard tunnels and bring configured tunnels up/down

The helpers validate user-controlled names and pass arguments directly without
shell concatenation. Reboot is separately whitelisted as the specific
`systemctl reboot` command.

Wi-Fi operations use NetworkManager. `setup-privileges.sh` installs a polkit
rule granting the JellyBox user NetworkManager control so Wi-Fi operations work
when JellyBox runs unattended or as a system service. Because NetworkManager
authorization requirements vary across Raspberry Pi OS and NetworkManager
versions, this permission is broader than the individual Wi-Fi actions JellyBox
currently uses. Review the privilege setup script before installation.

## Reporting a vulnerability

Please report security vulnerabilities privately using GitHub Security
Advisories rather than opening a public issue. This allows the issue to be
investigated and fixed before public disclosure.
