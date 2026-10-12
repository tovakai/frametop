# Switch from upstream Frametop to the API-enabled fork

This is a **core-only source-installation switch**. The fork at [tovakai/frametop](https://github.com/tovakai/frametop) should remain as close as possible to [upstream Frametop](https://github.com/Frametop/frametop) and add **only generic extension API endpoints**.

No plugins, spatial features, extension registry, or legacy profile migration are installed or configured by this command.

## Prerequisites

- Existing **source-installed** upstream Frametop on the Steam Frame at `~/frametop` (the default location).
- Git and an interactive terminal on the Steam Frame. **SSH recommended**: do not swap the running desktop from a terminal that depends on it.
- Sufficient storage and the same build dependencies as Frametop's regular installer. If the original upstream install came from a prebuilt release image, this route currently stops rather than guessing at a conversion.
- This fork must contain the extension API. While [PR #5](https://github.com/tovakai/frametop/pull/5) is still unmerged, the code is on `rebuild/extension-api`, not `main`.

## Switch (on the Steam Frame)

```sh
git clone --single-branch --branch rebuild/extension-api \
  https://github.com/tovakai/frametop.git ~/frametop-api

cd ~/frametop-api
bash scripts/upgrade-from-upstream.sh plan
bash scripts/upgrade-from-upstream.sh apply
```

The script requires typing `SWITCH` before changes. It then backs up your Frametop configuration and current Desktop launcher under `~/.local/state/frametop/upgrade-backups/<timestamp>/` (private permissions) and invokes **this fork's unchanged official `install.sh`**.

The upstream checkout stays at `~/frametop`, with its history and code intact. The newly installed Desktop launcher points to `~/frametop-api/session/frametop-session.sh`. Frametop's own installer may build/reinstall its normal services and SteamVR pointer driver and offer a SteamVR restart. It is **not** a no-downtime hot swap.

The script does not edit user layouts or attempt profile-format conversion. The official Frametop installer runs its normal configuration migration logic; the backup is for recovery.

## Inspect or roll back

```sh
cd ~/frametop-api
bash scripts/upgrade-from-upstream.sh status
bash scripts/upgrade-from-upstream.sh rollback
```

`ROLLBACK` confirmation runs the original `~/frametop/install.sh` again, returning the launcher and installed core services to upstream. The fork checkout and backup are retained. The command does not automatically overwrite the current settings with backup copies, because those may contain changes made since switching. If a SteamVR restart is needed, the installer will ask.

To use a nonstandard original upstream path, set `FT_UPSTREAM_DIR`:

```sh
FT_UPSTREAM_DIR=/path/to/upstream bash scripts/upgrade-from-upstream.sh plan
```

For a normal existing source install, **do not run `git pull` or change Git remotes in `~/frametop`** to perform this migration. Keeping the source trees separate is the rollback mechanism.

## Development and verification

This is a new experimental control API, not a released platform. Run the offline migration checks with:

```sh
bash -n scripts/upgrade-from-upstream.sh
bash scripts/tests/test-upgrade-from-upstream.sh
```

Offline tests verify read-only planning, source-path checks and rejection of non-API checkouts. They **do not** build or install the compositor, touch SteamVR, or prove the switch succeeds on hardware. That needs an explicit Steam Frame smoke test.

## Responsibility boundary

- **Core fork:** upstream Frametop, generic versioned extension endpoints, and this core upgrade/rollback command.
- **Independent extensions repository:** any optional spatial features, their lifecycle, manifests, and their tests.
- **Legacy branch:** reference implementation only.

Updating the fork with new upstream revisions must preserve the smallest possible API delta and keep this migration path tested.
