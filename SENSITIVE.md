# Not included

Some things the configs rely on can't be shared, because they're licensed, private, or someone else's
work. Provide your own versions at these paths. `.gitignore` keeps fonts and token-like files out of the
repo.

| What | Put it at | Why it's not included | Used by |
| --- | --- | --- | --- |
| Helvetica Neue (and Helvetica) | `~/.local/share/fonts/Helvetica/` | Licensed font | waybar, rofi, dashboard, GRUB theme |
| `ScratchpadIcons.ttf` | `~/.local/share/fonts/` | Contains Anthropic's Clawd artwork. Build it with `waybar/.config/waybar/build-scratchpad-icons.py` | waybar scratchpad icons, dashboard |
| Background photo `mies.jpg` | `~/Pictures/` | Someone else's photo; any image works | dashboard, GRUB theme |
| SSH hosts | `~/.ssh/config` | Private addresses and user names | `cmdlib` |
| WireGuard configs | `/etc/wireguard/*.conf` | Contain private keys | `cmdlib`, `waybar-vpn` |
| Claude Code login | `~/.claude/.credentials.json` | Account credentials; created by running `claude` | dashboard usage rings |

The dashboard's usage rings read Anthropic's undocumented usage endpoint, so they may stop working
without notice.
