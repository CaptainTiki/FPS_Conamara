#!/bin/bash
# Run Godot from the project root. Headless for tool scripts; use render.sh for screenshots.
exec ${GODOT:-/home/claude/tools/godot47} --headless --audio-driver Dummy --quit-after 6000 --path $(cd "$(dirname "$0")/.." && pwd) "$@"
