# Frametop + Extension API

> **Tovakai's upstream-first Frametop fork.** The goal is to keep the excellent original Steam Frame desktop intact while adding a small, general-purpose control API for independently developed extensions.

**This is not a separate desktop rewrite, a bundled collection of spatial features, or an official Frametop release.** It is upstream Frametop with minimal integration hooks. Optional features live in another repository.

## The pieces

| Project | Responsibility |
| --- | --- |
| [Frametop (upstream)](https://github.com/Frametop/frametop) | The Steam Frame desktop itself: Plasma screens, floating windows, input, gaze, profiles, installation and ongoing core development. |
| **[tovakai/frametop](https://github.com/tovakai/frametop)** (this repository) | An upstream-based core with a small, versioned local extension API. It owns the compositor-side integration points, not individual extension behavior. |
| [Frametop Extensions by tovakai](https://github.com/tovakai/frametop-extensions-by-tovakai) | Independently installed features, extension SDK, and experimental extension manager. Features can evolve without filling the core fork with one-off changes. |

That separation is intentional: **upstream owns the desktop; this fork exposes generic controls; extensions use those controls.** It should remain practical to incorporate upstream improvements without repeatedly rebuilding a heavily modified compositor.

## Branches and development status

- **`main`: upstream baseline.** This is the repository's default branch, currently retaining the upstream implementation. **It does not contain the extension API.**
- **[`rebuild/extension-api`](https://github.com/tovakai/frametop/tree/rebuild/extension-api): active experimental core.** This is where the extension API, example client, tests, and upstream-to-fork switch/rollback tooling live.
- **[`legacy`](https://github.com/tovakai/frametop/tree/legacy): historical reference.** Earlier integrated experiments are kept for reference, not presented as the current architecture.

**Status:** API v1 is experimental. Its contract has offline tests, but this fork does not claim complete device validation, broad compatibility, or an officially supported plugin platform. Check the linked documentation and the extensions repository for each feature's actual status.

## What the core API adds

The first API slice uses Frametop's existing **local abstract Unix datagram control socket**, `@ft_screens`. It is **not an HTTP/REST API**, web server, plugin loader, or remote service.

| Command | Capability | Purpose |
| --- | --- | --- |
| `ext api` | Version discovery | Ask the running compositor which API version it supports. |
| `ext caps` | Capability discovery | Ask which operations are available instead of assuming a version implies every feature. |
| `ext status N` | `screen.status` | Read a desktop screen's extension state. |
| `ext opacity N ALPHA MS` | `screen.opacity` | Set/fade screen opacity, respecting normal visibility and game-pause rules. |
| `ext move N X Y Z YAW PITCH ROLL MS` | `screen.move` | Move an unpinned, undragged screen in standing-world space with optional animation. |

Screen numbers are 1-based. Opacity is from 0 to 1; transition durations are 0–10,000 ms. These operations affect **runtime state** and do not silently write Frametop's layout or profile files. An extension is responsible for its own persistence.

An included standard-library Python client makes the interface easier to explore **from the API branch with Frametop running**:

```sh
python3 extensions/ft_ext.py info
python3 extensions/ft_ext.py status 1
python3 extensions/ft_ext.py opacity 1 0.6 --ms 250
python3 extensions/ft_ext.py move 1 0 1.5 -1.0 0 0 0 --ms 450
```

Full protocol, constraints, and examples: **[Extension API v1 contract](https://github.com/tovakai/frametop/blob/rebuild/extension-api/docs/extensions.md)**.

### What it does not do

API v1 does **not** provide an event subscription system, raw gaze samples, built-in follow behavior, an extension installer, a toolbar system, or persistent screen profiles. Nor does it embed Spatial Profiles, Spatial Toolbar, Spatial Room, or other optional projects in Frametop core. Those features belong in the independent [extensions repository](https://github.com/tovakai/frametop-extensions-by-tovakai), with their own implementation and maturity levels.

The existing control socket is a **trusted local-user interface**, not a security sandbox. Only run extension code you trust.

## Installing or testing

**Want Frametop without the experimental API?** Use the [official upstream project and installation guide](https://github.com/Frametop/frametop#install-on-the-headset). Its install command installs upstream Frametop, **not** this API fork or its extensions.

**Already have upstream Frametop and want to evaluate the API-enabled core?** The experimental branch includes a guarded migration with a read-only plan, an explicit apply step and a recorded rollback target. On the Steam Frame:

```sh
git clone --single-branch --branch rebuild/extension-api \
  https://github.com/tovakai/frametop.git ~/frametop-api
cd ~/frametop-api
bash scripts/upgrade-from-upstream.sh plan
# Review the plan before deciding to proceed:
bash scripts/upgrade-from-upstream.sh apply
```

The script asks for confirmation, and installing the core may interrupt a running desktop or restart SteamVR. It does **not** install optional extensions. Consult **[Upgrade from upstream and rollback](https://github.com/tovakai/frametop/blob/rebuild/extension-api/docs/upgrade-from-upstream.md)** first, especially if you have a prebuilt upstream release.

Check the installed core or start rollback using the same script:

```sh
bash scripts/upgrade-from-upstream.sh status
bash scripts/upgrade-from-upstream.sh rollback
```

## For developers

The design rule is **small generic hooks, large independent extensions**. Do not move extension-specific state, UI or policies back into the compositor just to ship a feature more quickly. Preserve existing upstream behavior and check API capabilities before using them.

On the `rebuild/extension-api` branch, run the offline API checks:

```sh
python3 extensions/tests/test_ft_ext.py
g++ -std=c++17 -Wall -Wextra -Werror \
  screens/tests/extension-motion-test.cpp -o /tmp/ft-ext-motion-test
/tmp/ft-ext-motion-test
bash -n scripts/upgrade-from-upstream.sh
bash scripts/tests/test-upgrade-from-upstream.sh
```

Offline checks are not a substitute for testing the running compositor on a headset. For core development conventions, see upstream's [AGENTS.md](https://github.com/Frametop/frametop/blob/main/AGENTS.md).

## Upstream, credit and license

Frametop is developed by the contributors to **[Frametop/frametop](https://github.com/Frametop/frametop)**. Their repository is the right place for the original project's user documentation, releases, and upstream issues. This fork is independently maintained and is not affiliated with Valve or endorsed by the upstream maintainers.

Licensed under **MIT**, following the original project. See [LICENSE](LICENSE).
