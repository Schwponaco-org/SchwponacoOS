#!/bin/sh
# Installs the Helvetica GRUB theme. Run as your user; it asks for sudo for the /boot and /etc steps.
# The .pf2 fonts are built from your local Helvetica Neue so the licensed font never lands in this repo.
set -e

theme=$(dirname "$(readlink -f "$0")")/helvetica
fonts="$HOME/.local/share/fonts/Helvetica/Helvetica Neue"
dest=/boot/grub/themes/helvetica
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT

grub-mkfont -s 32 -o "$build/helvetica_bold_32.pf2" "$fonts/HelveticaNeue-Bold.otf"
grub-mkfont -s 18 -o "$build/helvetica_medium_18.pf2" "$fonts/HelveticaNeue-Medium.otf"

sudo install -d "$dest"
sudo install -m 644 "$theme/theme.txt" "$build"/*.pf2 "$dest/"
# GRUB's JPEG reader can't decode progressive JPEGs (the theme silently falls back to text), so re-save as baseline
magick "$HOME/Pictures/mies.jpg" -interlace none -quality 92 "$build/background.jpg"
sudo install -m 644 "$build/background.jpg" "$dest/background.jpg"
sudo rm -f "$dest/background.png"  # left over from the earlier kali background

# set GRUB_THEME, replacing an existing line if there is one
if grep -q '^GRUB_THEME=' /etc/default/grub; then
    sudo sed -i "s|^GRUB_THEME=.*|GRUB_THEME=\"$dest/theme.txt\"|" /etc/default/grub
else
    echo "GRUB_THEME=\"$dest/theme.txt\"" | sudo tee -a /etc/default/grub >/dev/null
fi

sudo grub-mkconfig -o /boot/grub/grub.cfg
