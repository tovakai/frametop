# Switch upstream Frametop to the extension-API fork

This is a **core-only installation switch**. The [Frametop core fork](https://github.com/tovakai/frametop) remains upstream Frametop plus generic extension API endpoints, nothing more. It **does not** install the separate extensions repository, enable features or migrate spatial profiles.

## Supported upstream installations

The migration now detects the **actual Steam Desktop launcher**, not whichever Git checkout happens to be in `~/frametop`.

- **Prebuilt upstream release:** an installed Frametop release under `~/.local/share/frametop/releases/VERSION`, with valid `.frametop-release` metadata. This includes release 0.2.2.
- **Upstream source checkout:** the active launcher points into `~/frametop`, or another checkout specified by `FT_UPSTREAM_DIR`, with an official Frametop/frametop or original DeeJanuz/frametop Git remote.

For a prebuilt release, the exact release directory, its container image and metadata are preserved for rollback. A stale source checkout is **not** used as the rollback target. A release's image must still be available to its own `install.sh` when rolling back; the script does not redownload it.

Unknown launchers and incomplete/foreign release installations are **refused**, not overwritten.

## Upgrade on Steam Frame

Prefer a terminal over SSH; the core installer reinstalls services and may interrupt a running Frametop desktop.

```sh
# If you already cloned ~/frametop-api, update its migration script:
cd ~/frametop-api
git pull --ff-only

# Otherwise clone the extension-API core:
# git clone --single-branch --branch rebuild/extension-api \
#   https://github.com/tovakai/frametop.git ~/frametop-api
# cd ~/frametop-api

bash scripts/upgrade-from-upstream.sh plan
bash scripts/upgrade-from-upstream.sh apply
```

For a release installation with the existing launcher
`Exec=/home/steamos/.local/share/frametop/releases/0.2.2/session/frametop-session.sh`,
the plan should report:

```text
Active Steam Desktop launcher: upstream-release
Detected original installation: release
Rollback installer: /home/steamos/.local/share/frametop/releases/0.2.2/install.sh
Release version: 0.2.2
```

The script requires typing `SWITCH` before making changes.

It saves selected Frametop settings and a copy of the desktop launcher under
`~/.local/state/frametop/upgrade-backups/<UTC timestamp>/` with private
permissions. It records a **separate rollback-target marker before running**
the fork installer, so an interrupted installation still knows where to go back.

The script then calls the fork's regular `install.sh` to build/install core
components and reconfigure Frametop's services. It leaves the existing upstream
release files and rootless Podman image/container intact. The installer may
offer to restart SteamVR.

These settings backups are **not** a full disk snapshot, and upstream's regular
installer can run its usual configuration migration. The previous executable
and its installer are preserved for recovery, not an instant hot swap.

## Check and roll back

```sh
cd ~/frametop-api
bash scripts/upgrade-from-upstream.sh status
bash scripts/upgrade-from-upstream.sh rollback
```

`rollback` uses the **saved installation kind + exact path**. For release
0.2.2, that means running
`~/.local/share/frametop/releases/0.2.2/install.sh`, not `~/frametop/install.sh`.
It asks you to type `ROLLBACK` and then re-installs the previous upstream
core. It does **not** remove your fork checkout or silently revert settings
you changed after the switch. The rollback record is cleared only if the
upstream installer completes successfully.

Rollback requires the original release's Podman image and container to remain
available. Don't run the Frametop release cleanup/uninstaller or `podman prune`
between switching and rolling back.

## Development status

This is still an experimental API revision on `rebuild/extension-api`, not
an officially released fork. Offline checks run in GitHub Actions:

```sh
bash -n scripts/upgrade-from-upstream.sh
bash scripts/tests/test-upgrade-from-upstream.sh
```

They test release/source detection, read-only plan behavior, malformed metadata,
unknown installations and missing API files. They cannot replace a first real
Steam Frame installation/rollback smoke test.

## Repository responsibilities

- `tovakai/frametop`: tracked upstream + generic extension API endpoints and the core switch/rollback utility.
- `tovakai/frametop-extensions-by-tovakai`: all independently managed optional features, unrelated to this upgrade.
- `legacy`: old experimental code retained only as a reference.

Keep the fork's delta from upstream as small as possible.
