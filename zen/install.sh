#!/bin/sh
# Sets up Zen from this folder:
#   - links user.js into Zen's default profile (its folder name is random, so it's looked up)
#   - installs policies.json system-wide (asks for sudo): installs uBlock Origin and Tridactyl (beta)
#     on first start and turns off telemetry and studies. /etc, not Zen's own folder, so updates keep it.
# Start Zen once before running this, so the profile exists.
set -e

here=$(dirname "$(readlink -f "$0")")
zen="$HOME/.config/zen"

# the profile Zen actually starts with: the Default= under [Install…] in profiles.ini
profile=$(awk -F= '/^\[Install/ { inst = 1; next } /^\[/ { inst = 0 } inst && $1 == "Default" { print $2; exit }' "$zen/profiles.ini")
[ -n "$profile" ] && [ -d "$zen/$profile" ] || { echo "No Zen profile found; start Zen once first." >&2; exit 1; }

target="$zen/$profile/user.js"
[ -e "$target" ] && [ ! -L "$target" ] && mv "$target" "$target.bak" && echo "Kept the old user.js as user.js.bak"
ln -sfn "$here/user.js" "$target"
echo "Linked user.js into $profile"

sudo install -Dm644 "$here/policies.json" /etc/zen/policies/policies.json
echo "Installed /etc/zen/policies/policies.json; restart Zen and check about:policies"
