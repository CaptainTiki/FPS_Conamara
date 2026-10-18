#!/bin/bash
# Run Godot with a real (software) GL context under a virtual X display.
export LIBGL_ALWAYS_SOFTWARE=1
exec xvfb-run -a -s "-screen 0 1920x1080x24" ${GODOT:-/home/claude/tools/godot47} --audio-driver Dummy --rendering-driver opengl3 --quit-after ${QUIT_AFTER:-40000} --path $(cd "$(dirname "$0")/.." && pwd) "$@"
