#!/bin/sh
# Warms or cools the screen by 100K (hyprsunset) and shows the new temperature in a dunst popup.
# Starts hyprsunset if it isn't running, stepping from neutral (6500K). Usage: sunset.sh up|down
case $1 in
    up)   step=+100 ;;
    down) step=-100 ;;
    *)    exit 1 ;;
esac

if hyprctl hyprsunset temperature >/dev/null 2>&1; then
    hyprctl hyprsunset temperature "$step" >/dev/null
else
    setsid -f hyprsunset -t $((6500 $step)) >/dev/null 2>&1
    sleep 0.3  # let it open its socket before asking for the value
fi

notify-send -a sunset -u low -t 1500 -h string:x-dunst-stack-tag:sunset "Screen $(hyprctl hyprsunset temperature)K"
