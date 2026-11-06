if status is-interactive
    # Commands to run in interactive sessions can go here
end

# -g: keep these out of fish_variables, which would store them with your full home path
fish_add_path -g ~/.local/bin ~/.cargo/bin

alias fuck="nvim"

alias swag="start-hyprland"

# BEGIN opam configuration
# This is useful if you're using opam as it adds:
#   - the correct directories to the PATH
#   - auto-completion for the opam binary
# This section can be safely removed at any time if needed.
test -r "$HOME/.opam/opam-init/init.fish" && source "$HOME/.opam/opam-init/init.fish" > /dev/null 2> /dev/null; or true
# END opam configuration
