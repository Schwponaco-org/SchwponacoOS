#!/bin/sh
# Warns once at 10% and once at 5% while on battery; each warning re-arms only after charging back above its level.
bat=${BATTERY:-/sys/class/power_supply/BAT0}
warned=100  # lowest level already warned about this discharge

while :; do
    cap=$(cat "$bat/capacity")
    [ "$cap" -gt 10 ] && warned=100
    [ "$cap" -gt 5 ] && [ "$warned" -lt 10 ] && warned=10
    if [ "$(cat "$bat/status")" = Discharging ]; then
        if [ "$cap" -le 5 ] && [ "$warned" -gt 5 ]; then
            notify-send -a battery -u critical -h string:x-dunst-stack-tag:battery "Battery critical" "$cap% left, plug in now"
            warned=5
        elif [ "$cap" -le 10 ] && [ "$warned" -gt 10 ]; then
            notify-send -a battery -u normal -h string:x-dunst-stack-tag:battery "Battery low" "$cap% left"
            warned=10
        fi
    fi
    sleep 30
done
