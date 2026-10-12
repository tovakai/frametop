#!/usr/bin/env bash
# Switch an existing source-installed upstream Frametop to this fork (upstream +
# generic extension API), without replacing the upstream checkout or user config.
# This script belongs to the Frametop core fork. NO extensions are installed.
set -euo pipefail
umask 077

CORE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
UPSTREAM_DIR=${FT_UPSTREAM_DIR:-"$HOME/frametop"}
BACKUP_ROOT=${FT_UPGRADE_BACKUP_ROOT:-"$HOME/.local/state/frametop/upgrade-backups"}
LAUNCHER="$HOME/.local/share/applications/deckard-nested-desktop.desktop"

fail() { printf 'Frametop upgrade: %s\n' "$*" >&2; exit 1; }
canonical() {
    python3 -c 'import os,sys; print(os.path.realpath(os.path.expanduser(sys.argv[1])))' "$1"
}
UPSTREAM_DIR=$(canonical "$UPSTREAM_DIR")
BACKUP_ROOT=$(canonical "$BACKUP_ROOT")
[[ "$CORE_DIR" != "$UPSTREAM_DIR" && "$UPSTREAM_DIR" != / && "$CORE_DIR" != / &&
   "$UPSTREAM_DIR" != "$HOME" && "$CORE_DIR" != "$HOME" ]] || fail 'unsafe checkout paths'

usage() {
    cat <<'TEXT'
Usage: bash scripts/upgrade-from-upstream.sh plan|apply|status|rollback

plan      Preview the switch without changing anything (works on a PC).
apply     Install the fork's API-capable Frametop core over an existing upstream
          source installation. Runs Frametop's own interactive installer.
status    Show which checkout currently owns the Steam Desktop launcher.
rollback  Re-run the original upstream installer to switch back.

Run apply/rollback on the Steam Frame from an interactive terminal (prefer SSH).
Defaults: upstream source in ~/frametop; this script's repository is the fork.
To use a different upstream checkout, set FT_UPSTREAM_DIR=/path/to/source.
No plugins/extensions are downloaded, installed, or enabled by this command.
TEXT
}

check_source() {
    command -v git >/dev/null || fail 'git is required'
    [[ -f "$UPSTREAM_DIR/install.sh" &&
       -f "$UPSTREAM_DIR/session/frametop-session.sh" &&
       -f "$UPSTREAM_DIR/scripts/_env.sh" &&
       ! -e "$UPSTREAM_DIR/.frametop-release" ]] ||
       fail "upstream source checkout missing at $UPSTREAM_DIR (release-image installs are not yet supported)"
    [[ $(git -C "$UPSTREAM_DIR" rev-parse --show-toplevel 2>/dev/null) == "$UPSTREAM_DIR" ]] ||
        fail 'upstream checkout is not a Git repository at the specified path'
}

check_core() {
    [[ -f "$CORE_DIR/install.sh" &&
       -f "$CORE_DIR/docs/extensions.md" &&
       -f "$CORE_DIR/screens/extension-motion.h" ]] ||
        fail 'this checkout lacks the extension API. Use the fork rebuild/extension-api branch (or a later release containing the API)'
    [[ $(git -C "$CORE_DIR" rev-parse --show-toplevel 2>/dev/null) == "$CORE_DIR" ]] ||
        fail 'the extension API core must be a Git checkout'
    local url
    url=$(git -C "$CORE_DIR" remote get-url origin 2>/dev/null || true)
    case "$url" in
        https://github.com/tovakai/frametop|https://github.com/tovakai/frametop.git|git@github.com:tovakai/frametop.git) ;;
        *) fail "expected tovakai/frametop core fork, got origin '$url'" ;;
    esac
}

check_frame() {
    [[ $(id -u) != 0 ]] || fail 'do not run as root'
    grep -qx 'ID=steamos' /etc/os-release 2>/dev/null &&
        grep -qE '^VARIANT_ID="?vr"?$' /etc/os-release ||
        fail 'apply/rollback must run on the Steam Frame (SteamOS VR)'
    [[ -t 0 && -t 1 ]] || fail 'apply/rollback require an interactive terminal'
}

launcher_owner() {
    local command
    command=$(grep -m 1 '^Exec=' "$LAUNCHER" 2>/dev/null || true)
    case "$command" in
        *"$CORE_DIR/session/frametop-session.sh"*) printf 'fork\n' ;;
        *"$UPSTREAM_DIR/session/frametop-session.sh"*) printf 'upstream\n' ;;
        '') printf 'none\n' ;;
        *) printf 'other\n' ;;
    esac
}

status() {
    printf 'Active Steam Desktop launcher: %s\n' "$(launcher_owner)"
    if [[ -f "$LAUNCHER" ]]; then
        grep -m 1 '^Exec=' "$LAUNCHER" || true
    fi
    printf 'Upstream checkout: %s\nAPI fork checkout: %s\n' "$UPSTREAM_DIR" "$CORE_DIR"
}

plan() {
    check_source
    check_core
    status
    printf '\nFork revision: '
    git -C "$CORE_DIR" rev-parse --short HEAD
    cat <<'TEXT'

The switch:
  1. Keeps the upstream checkout and its Git history untouched.
  2. Copies Frametop configuration + launcher entries to a private backup.
  3. Runs the fork's ORIGINAL Frametop install.sh, which builds and installs
     the core components, services and SteamVR pointer driver.
  4. Leaves SteamVR reboot/restart to the normal interactive installer prompt.

Rollback re-runs the original upstream install.sh. The fork is not deleted.
No plugin repository, features or spatial-profile migration is involved.
The extension API is experimental and requires Steam Frame validation.
TEXT
}

confirm() {
    local answer
    printf '\nType %s to confirm: ' "$1"
    read -r answer </dev/tty || fail 'confirmation unavailable'
    [[ "$answer" == "$1" ]] || fail 'cancelled'
}

backup_settings() {
    local stamp folder file
    stamp=$(date -u +%Y%m%dT%H%M%SZ)
    folder="$BACKUP_ROOT/$stamp"
    [[ ! -e "$folder" ]] || fail "backup directory already exists: $folder"
    mkdir -p -- "$folder"
    chmod 700 "$BACKUP_ROOT" "$folder"
    for file in frametop.conf frametop-layout.json frametop-layout-profiles.json \
                frametop-input.json frametoprc; do
        if [[ -e "$HOME/.config/$file" || -L "$HOME/.config/$file" ]]; then
            cp -a -- "$HOME/.config/$file" "$folder/$file"
        fi
    done
    if [[ -d "$HOME/.config/frametop" ]]; then
        cp -a -- "$HOME/.config/frametop" "$folder/frametop"
    fi
    if [[ -f "$LAUNCHER" ]]; then
        cp -a -- "$LAUNCHER" "$folder/desktop-launcher.desktop"
    fi
    {
        printf 'upstream_dir=%s\ncore_dir=%s\n' "$UPSTREAM_DIR" "$CORE_DIR"
        git -C "$UPSTREAM_DIR" rev-parse HEAD | sed 's/^/upstream_commit=/'
        git -C "$CORE_DIR" rev-parse HEAD | sed 's/^/core_commit=/'
    } > "$folder/sources.txt"
    printf 'Backup: %s\n' "$folder"
}

apply() {
    check_source
    check_core
    check_frame
    case "$(launcher_owner)" in
        upstream) ;;
        fork) fail 'already using the API fork; no upgrade necessary' ;;
        *) fail 'active launcher is not managed by the specified upstream checkout; refusing to replace an unknown installation' ;;
    esac
    plan
    printf '\nThis runs the fork core installer. Running desktops/services may be affected.\n'
    printf 'Prefer SSH so the installer does not terminate the terminal it runs in.\n'
    confirm SWITCH
    backup_settings
    if ! (cd "$CORE_DIR" && ./install.sh); then
        fail "fork installer failed or was interrupted; upstream code remains at $UPSTREAM_DIR.
To restore it, run: bash $CORE_DIR/scripts/upgrade-from-upstream.sh rollback"
    fi
    printf '\nAPI-enabled Frametop core installed. NO extensions installed.\n'
    status
}

rollback() {
    check_source
    check_frame
    case "$(launcher_owner)" in
        fork|upstream) ;;
        *) fail 'unexpected active launcher; refusing to modify unknown installation' ;;
    esac
    printf 'Re-install original upstream Frametop from %s\n' "$UPSTREAM_DIR"
    printf 'No plugin/extension operations or automatic configuration restoration.\n'
    confirm ROLLBACK
    (cd "$UPSTREAM_DIR" && ./install.sh)
    printf '\nUpstream installer completed. Follow any SteamVR restart instructions.\n'
    status
}

[[ $# == 1 ]] || { usage >&2; exit 2; }
case "$1" in
    plan) plan ;;
    apply) apply ;;
    status) status ;;
    rollback) rollback ;;
    -h|--help|help) usage ;;
    *) usage >&2; exit 2 ;;
esac
