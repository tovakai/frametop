#!/bin/sh
# Shown in a terminal when a desktop bind has no program in the container.
action=${1:-app}
shift || true
echo "frametop: no ${action} is installed in the Frame container."
echo "Looked for: $*"
echo
exec bash
