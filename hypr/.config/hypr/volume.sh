#!/bin/sh
# Changes the volume and shows it as a dunst progress popup that replaces the previous one.
# Data: wpctl (wireplumber) on the default PipeWire sink.
case $1 in
    up)   wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+ ;;
    down) wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%- ;;
    mute) wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle ;;
esac

out=$(wpctl get-volume @DEFAULT_AUDIO_SINK@)  # "Volume: 0.45" or "Volume: 0.45 [MUTED]"
vol=$(echo "$out" | awk '{ printf "%d", $2 * 100 + 0.5 }')
case $out in
    *MUTED*) label="Muted" ;;
    *)       label="Volume $vol%" ;;
esac

notify-send -a volume -u low -t 1500 -h string:x-dunst-stack-tag:volume -h "int:value:$vol" "$label"
