#!/bin/sh
# rofi script mode for typed prefixes. It lists no entries, so inside combi it only receives text
# that matched no app (ROFI_RETV=2):
#   !query  search the web in Zen
#   #name   open a GitHub repo in Zen, matched on the repo name only (not its owner), case-insensitive.
#           One match opens directly, several (or just "#")
#           open a second rofi list to pick from.
# Repo data: `gh repo list` for your account and every organisation you belong to (`gh api user/orgs`);
# needs github-cli logged in (`gh auth login`). Cached in ~/.cache/rofi-repos, refreshed hourly.
[ "$ROFI_RETV" = 2 ] || exit 0

open() { setsid -f zen-browser "$@" >/dev/null 2>&1; }

cache="${XDG_CACHE_HOME:-$HOME/.cache}/rofi-repos"
refresh() {  # "name<TAB>url" per line
  { gh repo list --limit 1000 --json name,url -q '.[] | "\(.name)\t\(.url)"'
    for org in $(gh api user/orgs -q '.[].login'); do
      gh repo list "$org" --limit 1000 --json name,url -q '.[] | "\(.name)\t\(.url)"'
    done; } | sort -f > "$cache.tmp" && [ -s "$cache.tmp" ] && mv "$cache.tmp" "$cache"
}

case $1 in
  !?*) open --search "${1#!}" ;;
  \#*)
    query=$(printf '%s' "${1#\#}" | tr '[:upper:]' '[:lower:]')
    if [ ! -s "$cache" ]; then refresh  # first use: wait for the list
    elif [ -n "$(find "$cache" -mmin +60)" ]; then (refresh &)
    fi
    # exact repo name first, else every repo whose name contains the text
    matches=$(awk -F'\t' -v q="$query" 'tolower($1) == q' "$cache")
    [ -n "$matches" ] || matches=$(awk -F'\t' -v q="$query" 'index(tolower($1), q)' "$cache")
    if [ "$(printf '%s\n' "$matches" | grep -c .)" = 1 ]; then
      open "$(printf '%s' "$matches" | cut -f2)"
    else
      # this rofi is still closing, so the picker starts a moment later
      list=${matches:-$(cat "$cache")}
      setsid -f sh -c 'sleep 0.15; url=$(printf "%s\n" "$1" | rofi -dmenu -i -p "#" -display-columns 1 -display-column-separator "\t" | cut -f2); [ -n "$url" ] && setsid -f zen-browser "$url"' _ "$list" >/dev/null 2>&1
    fi ;;
esac
