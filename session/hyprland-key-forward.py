#!/usr/bin/env python3
"""Forward desktop keys from the installed input relay to this compositor.

The relay addresses @ft_screens. The experimental session listens on its own
control name, so while Plasma's ft-screens is not running this process holds
@ft_screens and passes key, click, and chord messages on. Layout commands
are dropped.
"""
import socket
import sys

ALLOWED_PREFIXES = (b"key ", b"click ", b"vrkeyboard ", b"chord-click ")
ALLOWED_EXACT = (b"up",)


def allowed(data):
    return data in ALLOWED_EXACT or data.startswith(ALLOWED_PREFIXES)


def main(argv):
    target_name = argv[1] if len(argv) > 1 else "ft_hyprland"
    listen = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        listen.bind("\0ft_screens")
    except OSError as exc:
        print(f"frametop: @ft_screens is in use ({exc}); keyboard forwarder stayed off", file=sys.stderr)
        return 0
    out = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    out.bind("")
    target = b"\0" + target_name.encode()
    print(f"frametop: forwarding desktop keys @ft_screens -> @{target_name}", flush=True)
    while True:
        data, _addr = listen.recvfrom(2048)
        if not allowed(data):
            continue
        try:
            out.sendto(data, target)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
