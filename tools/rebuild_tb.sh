#!/bin/bash
# TrenchBroom pipeline: layout -> dressing rules -> .map -> FuncGodot scene -> screenshots
#   tools/rebuild_tb.sh test01                 rebuild levels/test01.map (hand-edited or generated) + shoot
#   tools/rebuild_tb.sh test02 42 56           generate a new layout: seed 42, 56x56 cells, then build + shoot
#   THEME=kit tools/rebuild_tb.sh test01       dressing theme for export (quake | kit); default quake
set -e
cd $(cd "$(dirname "$0")/.." && pwd)
NAME=${1:?level name}
if [ -n "$2" ]; then
  SIZE=${3:-56}
  python3 tools/mapgen.py "$2" "$SIZE" "$SIZE" levels
  mv -f levels/seed$2.json levels/$NAME.json; mv -f levels/seed$2_automap.png levels/${NAME}_automap.png
fi
if [ -f levels/$NAME.json ] && [ -n "$2" -o ! -f levels/$NAME.map ]; then
  python3 tools/export_map.py levels/$NAME.json ${THEME:-quake}
fi
python3 tools/gen_tb_textures.py | tail -1
timeout 600 tools/godot.sh --import >/dev/null 2>&1 || true
timeout 200 tools/godot.sh -s tools/build_tb_config.gd 2>&1 | grep -E "saved|SCRIPT" || true
timeout 300 tools/godot.sh -s tools/build_tb_level.gd -- levels/$NAME.map 2>&1 | grep -E "saved|built|SCRIPT" || true
rm -f shots/${NAME}_*.png
QUIT_AFTER=3000 timeout 300 tools/render.sh --resolution 960x540 res://levels/$NAME.tscn -- --capture 2>&1 | grep -c captured || true
python3 - "$NAME" <<'PY'
import sys, glob
from PIL import Image
lv = sys.argv[1]
fs = sorted(glob.glob(f"shots/{lv}_*.png"))
if fs:
    ims = [Image.open(f) for f in fs]; W, H = ims[0].size; cols = 2; rows = (len(ims) + 1) // 2
    s = Image.new("RGB", (W * cols, H * rows))
    for i, im in enumerate(ims): s.paste(im, ((i % cols) * W, (i // cols) * H))
    s.save(f"shots/contact_{lv}.png"); print("contact:", len(ims))
PY
