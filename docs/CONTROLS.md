# JellyBox Controls

JellyBox is operated entirely from the Waveshare HAT's joystick and three keys.
GPIO pins are listed in [HARDWARE.md](HARDWARE.md).

## Navigation

| Control        | Action                                                        |
| -------------- | ------------------------------------------------------------- |
| Joystick Up    | Move up / previous item                                       |
| Joystick Down  | Move down / next item                                         |
| Joystick Left  | Left; on editors, move the cursor / decrease a value          |
| Joystick Right | Right; on editors, move the cursor / increase a value         |
| Joystick Press | Select / OK / confirm                                         |
| KEY1           | Back (leave the current screen)                               |

A long press of Joystick Press on the main menu cycles the theme.

## Text and address entry

Some tools take a typed value — a Wi-Fi password, an SSH username, Nmap
arguments, a MAC address, or a terminal command. Two input methods are used:

**On-screen keyboard** (text fields). The joystick moves around the key grid and
Press types the highlighted key. On the keyboard the aux keys are shortcuts:

| Control | Action                    |
| ------- | ------------------------- |
| KEY2    | Insert a space            |
| KEY3    | Delete (backspace)        |

The keyboard also has on-grid `SPC`, `DEL`, `SHIFT`, and `OK` keys.

**Octet editor** (IP targets, e.g. Ping/Nmap). Left/Right selects an octet and
Up/Down changes it; Press confirms.

## Output screens

On scrolling output (Nmap results, Traceroute, Terminal, saved Results),
Up/Down scroll and a `^` / `v` marker shows there is more above or below.
