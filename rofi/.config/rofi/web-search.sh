#!/bin/sh
# rofi script mode for the "!" web search. It lists no entries, so inside combi it only
# receives text that matched no app (ROFI_RETV=2); "!query" opens a search in Zen.
[ "$ROFI_RETV" = 2 ] || exit 0

case $1 in
    !?*) setsid -f zen-browser --search "${1#!}" >/dev/null 2>&1 ;;
esac
