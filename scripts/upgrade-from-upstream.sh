#!/usr/bin/env bash
# Switch an installed upstream Frametop (source OR packaged release) to the
# Frametop fork with generic extension API endpoints. Never installs plugins.
set -euo pipefail
umask 077

CORE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
UPSTREAM_DIR=${FT_UPSTREAM_DIR:-"$HOME/frametop"}
BACKUP_ROOT=${FT_UPGRADE_BACKUP_ROOT:-"$HOME/.local/state/frametop/upgrade-backups"}
RELEASES_DIR="$HOME/.local/share/frametop/releases"
LAUNCHER="$HOME/.local/share/applications/deckard-nested-desktop.desktop"

fail() { printf 'Frametop upgrade: %s\n' "$*" >&2; exit 1; }
canonical() {
    python3 -c 'import os,sys; print(os.path.realpath(os.path.expanduser(sys.argv[1])))' "$1"
}
UPSTREAM_DIR=$(canonical "$UPSTREAM_DIR")
BACKUP_ROOT=$(canonical "$BACKUP_ROOT")
RELEASES_DIR=$(canonical "$RELEASES_DIR")
ROLLBACK_RECORD="$BACKUP_ROOT/rollback-target"
[[ "$CORE_DIR" != "$UPSTREAM_DIR" && "$UPSTREAM_DIR" != / && "$CORE_DIR" != / &&
   "$UPSTREAM_DIR" != "$HOME" && "$CORE_DIR" != "$HOME" &&
   "$CORE_DIR" != "$RELEASES_DIR" && "$CORE_DIR" != "$BACKUP_ROOT" ]] ||
    fail 'unsafe checkout paths'

usage() {
    cat <<'TEXT'
Usage: bash scripts/upgrade-from-upstream.sh plan|apply|status|rollback

plan      Preview the switch from the currently installed upstream version.
apply     Switch to this fork's extension-API core, using its normal installer.
status    Show the active desktop launcher and saved rollback target.
rollback  Reinstall the EXACT upstream release/source that was active before.

Run apply/rollback on the Steam Frame, in a terminal (SSH recommended).
Source installations and prebuilt releases are supported.
Optional FT_UPSTREAM_DIR points to a nonstandard upstream source checkout.
No extensions/plugins are downloaded, installed or activated.
TEXT
}

check_source() {
    command -v git >/dev/null || fail 'git is required'
    [[ -f "$UPSTREAM_DIR/install.sh" &&
       -f "$UPSTREAM_DIR/session/frametop-session.sh" &&
       -f "$UPSTREAM_DIR/scripts/_env.sh" &&
       ! -e "$UPSTREAM_DIR/.frametop-release" ]] ||
       fail "upstream source checkout missing at $UPSTREAM_DIR"
    [[ $(git -C "$UPSTREAM_DIR" rev-parse --show-toplevel 2>/dev/null) == "$UPSTREAM_DIR" ]] ||
        fail 'upstream checkout is not a Git repository at the specified path'
    local url
    url=$(git -C "$UPSTREAM_DIR" remote get-url origin 2>/dev/null || true)
    case "$url" in
        https://github.com/Frametop/frametop|https://github.com/Frametop/frametop.git|git@github.com:Frametop/frametop.git|\
https://github.com/DeeJanuz/frametop|https://github.com/DeeJanuz/frametop.git|git@github.com:DeeJanuz/frametop.git|\
https://github.com/AZumD/frametop|https://github.com/AZumD/frametop.git|git@github.com:AZumD/frametop.git) ;;
        *) fail "expected the upstream Frametop source remote, got origin '$url'" ;;
    esac
}

check_release() {
    local dir=$1 version
    version=$(basename -- "$dir")
    [[ "$dir" == "$RELEASES_DIR/$version" && "$version" != . && "$version" != .. ]] ||
        fail "release directory is outside $RELEASES_DIR: $dir"
    [[ -f "$dir/.frametop-release" &&
       -f "$dir/session/frametop-session.sh" &&
       -f "$dir/pack/release-box.sh" &&
       -x "$dir/install.sh" ]] ||
        fail "incomplete installed Frametop release in $dir"
    grep -qxF "VERSION=$version" "$dir/.frametop-release" ||
        fail "release metadata does not match directory $dir"
    grep -q '^IMAGE_ID=[0-9a-f]\{64\}$' "$dir/.frametop-release" ||
        fail "missing release image ID in $dir/.frametop-release"
    grep -q '^BOX=frametop-[A-Za-z0-9_.-]*$' "$dir/.frametop-release" ||
        fail "missing release container metadata in $dir/.frametop-release"
    grep -q '^IMAGE=localhost/frametop:' "$dir/.frametop-release" ||
        fail "missing release image reference in $dir/.frametop-release"
}

check_core() {
    command -v git >/dev/null || fail 'git is required'
    [[ -f "$CORE_DIR/install.sh" &&
       -f "$CORE_DIR/docs/extensions.md" &&
       -f "$CORE_DIR/screens/extension-motion.h" ]] ||
        fail 'this checkout lacks the extension API. Use rebuild/extension-api or a later API-bearing fork revision'
    [[ $(git -C "$CORE_DIR" rev-parse --show-toplevel 2>/dev/null) == "$CORE_DIR" ]] ||
        fail 'extension API core must be a Git checkout'
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

launcher_command() {
    sed -n '/^Exec=/{s/^Exec=//;p;q;}' "$LAUNCHER" 2>/dev/null || true
}

# An installed release is recognized ONLY from its actual, exact Steam launcher
# path, never from the presence of an unrelated ~/frametop source checkout.
active_release_dir() {
    local command candidate target
    command=$(launcher_command)
    case "$command" in
        "$RELEASES_DIR"/*/session/frametop-session.sh) ;;
        *) return 1 ;;
    esac
    candidate=${command%/session/frametop-session.sh}
    target=$(canonical "$candidate")
    [[ "$(dirname "$target")" == "$RELEASES_DIR" ]] || return 1
    printf '%s\n' "$target"
}

launcher_owner() {
    local command
    command=$(launcher_command)
    if [[ "$command" == "$CORE_DIR/session/frametop-session.sh" ]]; then
        printf 'fork\n'
    elif [[ "$command" == "$UPSTREAM_DIR/session/frametop-session.sh" ]]; then
        printf 'upstream-source\n'
    elif active_release_dir >/dev/null; then
        printf 'upstream-release\n'
    elif [[ -z "$command" ]]; then
        printf 'none\n'
    else
        printf 'other\n'
    fi
}

status() {
    printf 'Active Steam Desktop launcher: %s\n' "$(launcher_owner)"
    [[ ! -f "$LAUNCHER" ]] || grep -m 1 '^Exec=' "$LAUNCHER"
    printf 'Upstream source: %s\nAPI fork: %s\n' "$UPSTREAM_DIR" "$CORE_DIR"
    if [[ -f "$ROLLBACK_RECORD" ]]; then
        local kind directory
        IFS=$'\t' read -r kind directory < "$ROLLBACK_RECORD"
        printf 'Saved rollback target: %s (%s)\n' "$directory" "$kind"
    fi
}

previous_target() {
    local kind path
    case "$(launcher_owner)" in
        upstream-source)
            check_source
            printf 'source\t%s\n' "$UPSTREAM_DIR" ;;
        upstream-release)
            path=$(active_release_dir)
            check_release "$path"
            printf 'release\t%s\n' "$path" ;;
        fork) fail 'API fork is already active; use status or rollback' ;;
        *) fail 'launcher does not point to a recognized upstream Frametop installation; refusing to replace it' ;;
    esac
}

plan() {
    check_core
    local kind previous
    IFS=$'\t' read -r kind previous < <(previous_target)
    status
    printf '\nDetected original installation: %s\nRollback installer: %s/install.sh\n' "$kind" "$previous"
    if [[ "$kind" == release ]]; then
        printf 'Release version: %s\n' "$(basename "$previous")"
        printf 'Release image: %s\n' "$(sed -n 's/^IMAGE=//p' "$previous/.frametop-release" | head -1)"
    fi
    printf 'API fork revision: '
    git -C "$CORE_DIR" rev-parse --short HEAD
    cat <<'TEXT'

Apply will:
  1. Keep the current upstream source/release and its image/container intact.
  2. Back up Frametop settings, Desktop launcher and rollback target privately.
  3. Run the fork's standard interactive install.sh to install upstream + API.
  4. Let you decide whether to restart SteamVR in the official installer.

Rollback uses the SAVED installer from the exact previous upstream release
(or source checkout). It does not choose ~/frametop just because it exists.
No plugin repository, plugin features or spatial-profile migration is involved.
NOTE: The API core is still experimental and unverified on Steam Frame.
TEXT
}

confirm() {
    local answer
    printf '\nType %s to confirm: ' "$1"
    read -r answer </dev/tty || fail 'confirmation unavailable'
    [[ "$answer" == "$1" ]] || fail 'cancelled'
}

backup_settings() {
    local kind=$1 previous=$2 stamp folder file temporary
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
    [[ ! -d "$HOME/.config/frametop" ]] ||
        cp -a -- "$HOME/.config/frametop" "$folder/frametop"
    [[ ! -f "$LAUNCHER" ]] ||
        cp -a -- "$LAUNCHER" "$folder/desktop-launcher.desktop"
    {
        printf 'previous_kind=%s\nprevious_installer=%s/install.sh\ncore_dir=%s\n' "$kind" "$previous" "$CORE_DIR"
        if [[ "$kind" == release ]]; then
            cat "$previous/.frametop-release"
        else
            git -C "$previous" rev-parse HEAD | sed 's/^/upstream_commit=/'
        fi
        git -C "$CORE_DIR" rev-parse HEAD | sed 's/^/core_commit=/'
    } > "$folder/sources.txt"
    # The marker is written BEFORE running the installer, so a partially
    # completed install still has an unambiguous path back.
    [[ ! -e "$ROLLBACK_RECORD" && ! -L "$ROLLBACK_RECORD" ]] ||
        fail "previous migration marker exists at $ROLLBACK_RECORD; resolve it before retrying"
    temporary="$BACKUP_ROOT/.rollback-target.$$"
    [[ ! -e "$temporary" ]] || fail 'migration temporary file already exists'
    printf '%s\t%s\n' "$kind" "$previous" > "$temporary"
    chmod 600 "$temporary"
    mv -- "$temporary" "$ROLLBACK_RECORD"
    printf 'Local settings backup: %s\nRollback installer recorded: %s/install.sh\n' "$folder" "$previous"
}

apply() {
    check_frame
    check_core
    [[ ! -e "$ROLLBACK_RECORD" && ! -L "$ROLLBACK_RECORD" ]] ||
        fail "a previous switch is still recorded at $ROLLBACK_RECORD; use rollback/status before applying again"
    local kind previous
    IFS=$'\t' read -r kind previous < <(previous_target)
    plan
    printf '\nThis will reinstall core services and the SteamVR pointer driver.\n'
    printf 'SSH is recommended: changing the active VR desktop can disconnect its terminal.\n'
    confirm SWITCH
    backup_settings "$kind" "$previous"
    if ! (cd "$CORE_DIR" && ./install.sh); then
        fail "API-core installation failed/interrupted. Original upstream is preserved.
Use 'bash $CORE_DIR/scripts/upgrade-from-upstream.sh rollback' to restore it."
    fi
    printf '\nAPI-enabled Frametop installed. No extensions installed or enabled.\n'
    status
}

rollback() {
    check_frame
    [[ -f "$ROLLBACK_RECORD" && ! -L "$ROLLBACK_RECORD" ]] ||
        fail "no saved migration target at $ROLLBACK_RECORD; refusing to guess a rollback version"
    local kind previous current
    IFS=$'\t' read -r kind previous < "$ROLLBACK_RECORD"
    previous=$(canonical "$previous")
    case "$kind" in
        source)
            [[ "$previous" == "$UPSTREAM_DIR" ]] ||
                fail 'recorded source path differs from configured upstream checkout'
            check_source ;;
        release) check_release "$previous" ;;
        *) fail 'saved migration target has an unknown installation type' ;;
    esac
    current=$(launcher_owner)
    case "$current" in
        fork) ;;
        upstream-source)
            [[ "$kind" == source ]] || fail 'unexpected source installation is active' ;;
        upstream-release)
            [[ "$kind" == release && "$(active_release_dir)" == "$previous" ]] ||
                fail 'a different release is currently active' ;;
        *) fail 'active desktop launcher changed to an unknown installation; refusing rollback' ;;
    esac
    printf 'Restoring the exact previous upstream %s: %s\n' "$kind" "$previous"
    printf 'No extensions involved. Current settings will not be automatically overwritten.\n'
    confirm ROLLBACK
    if ! (cd "$previous" && ./install.sh); then
        fail "upstream reinstall failed. Rollback target is still saved in $ROLLBACK_RECORD"
    fi
    rm -- "$ROLLBACK_RECORD"
    printf '\nOriginal upstream installer completed. Follow its SteamVR restart prompt.\n'
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
