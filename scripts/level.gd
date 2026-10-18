class_name Level
extends Node3D
## Level root for TrenchBroom-built levels (levels/<name>.tscn, built by tools/build_tb_level.gd).
## Geometry, lights, doors, enemies, pickups, player start and screenshot markers all come
## from the .map via FuncGodot. This script adds what the gameplay scripts expect of a Level:
##   flow_dir()      grid flow field for enemies / the playtest bot (from levels/<name>.json)
##   doors_changed() re-plan when a door unlocks
##   power_on() / unlock()   hooks for breakers and switches (zones come later)
## Dev args:  -- --capture | --playtest | --movetest | --notetest   (see tools/)

const CELL := 2.0
const NDIRS := [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]

var level_name := ""
var rows := 72
var _cells := {}        # Vector2i(col, row) -> {t, f, c}
var _walk := {}         # Vector2i -> true
var _flows := {}
var power_zones: Array = []
var door_locks: Dictionary = {}

func _ready() -> void:
	level_name = scene_file_path.get_file().get_basename()
	_load_grid()
	if Engine.is_editor_hint():
		return
	var args := OS.get_cmdline_user_args()
	if "--capture" in args:
		_capture.call_deferred()
	elif "--playtest" in args:
		add_child(Playtest.new())
	elif "--movetest" in args:
		add_child(load("res://tools/movetest.gd").new())
	elif "--notetest" in args:
		var np := NotePins.new()
		add_child(np)
		await get_tree().process_frame
		await get_tree().process_frame
		np._open()
		np._on_submit("notetest pin from --notetest")
		print("pins now: ", np.pins.size(), " -> ", np._notes_path())
		get_tree().quit()
	else:
		add_child(NotePins.new())   # Q drops a note pin

# ------------------------------------------------------------- grid / flow ----
func _load_grid() -> void:
	var path := "res://levels/%s.json" % level_name
	if not FileAccess.file_exists(path):
		return
	var d = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not d:
		return
	rows = int(d["height"])
	for c in d["cells"]:
		_cells[Vector2i(int(c["x"]), int(c["y"]))] = c
	_build_walk()

func _build_walk() -> void:
	_walk.clear()
	_flows.clear()
	for k in _cells:
		var t := int(_cells[k]["t"])
		if t != 0 and t != 6:          # not void, not pit
			_walk[k] = true
	# locked doors are walls until they unlock
	for door in find_children("*", "Door", true, false):
		if door.get("lock") != "none":
			var c := cell_of(door.global_position)
			var w: float = float(door.get("slab_width"))
			_walk.erase(c)
			if w > 2.5:   # a two-cell door: block the neighbour across the slab too
				var side := Vector2i(0, 1) if abs(door.global_transform.basis.z.x) > 0.5 else Vector2i(1, 0)
				_walk.erase(c + side)
				_walk.erase(c - side)

## FuncGodot maps quake (x, y) -> godot (z, x); export_map.py flips rows: quake y = (rows - row) * 64
func cell_of(p: Vector3) -> Vector2i:
	return Vector2i(int(floor(p.z / CELL)), rows - 1 - int(floor(p.x / CELL)))

func cell_center(c: Vector2i) -> Vector3:
	var f := float(_cells[c]["f"]) if _cells.has(c) else 0.0
	return Vector3((rows - c.y - 0.5) * CELL, f, (c.x + 0.5) * CELL)

func is_walkable(c: Vector2i) -> bool:
	return _walk.has(c)

func _links(c: Vector2i) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	var f := int(_cells[c]["f"]) if _cells.has(c) else 0
	for d in NDIRS:
		var n: Vector2i = c + d
		if _walk.has(n) and abs(int(_cells[n]["f"]) - f) <= 1:
			out.append(n)
	return out

func _nearest_walkable(c: Vector2i) -> Vector2i:
	if _walk.has(c):
		return c
	for d in NDIRS:
		if _walk.has(c + d):
			return c + d
	return c

func distance_field(goal: Vector2i) -> Dictionary:
	goal = _nearest_walkable(goal)
	if _flows.has(goal):
		return _flows[goal]
	var dist := {goal: 0}
	var queue: Array[Vector2i] = [goal]
	var i := 0
	while i < queue.size():
		var c: Vector2i = queue[i]
		i += 1
		for n in _links(c):
			if not dist.has(n):
				dist[n] = dist[c] + 1
				queue.append(n)
	if _flows.size() > 8:
		_flows.clear()
	_flows[goal] = dist
	return dist

## Unit direction (XZ) from `from` toward the next cell on the way to `to`.
func flow_dir(from: Vector3, to: Vector3, _climb := false) -> Vector3:
	if _walk.is_empty():
		return Vector3.ZERO
	var field := distance_field(cell_of(to))
	var c := _nearest_walkable(cell_of(from))
	var best := c
	var best_d: int = field.get(c, 1 << 30)
	for n in _links(c):
		if field.has(n) and field[n] < best_d:
			best_d = field[n]
			best = n
	if best == c:
		return Vector3.ZERO
	var p := cell_center(best)
	return Vector3(p.x - from.x, 0, p.z - from.z).normalized()

# ---------------------------------------------------------------- hooks ----
func doors_changed() -> void:
	_build_walk()

func power_on(_index: int) -> void:
	pass   # power zones for TB levels come with the Admin level

func unlock(targets: Array) -> void:
	for door in find_children("*", "Door", true, false):
		if cell_of(door.global_position) in targets:
			door.lock = "none"
	doors_changed()

# -------------------------------------------------------------- capture ----
func _capture() -> void:
	var cam := Camera3D.new()
	cam.fov = 80
	add_child(cam)
	cam.make_current()
	var out_dir := ProjectSettings.globalize_path("res://shots")
	DirAccess.make_dir_recursive_absolute(out_dir)
	for m in get_tree().get_nodes_in_group("shots"):
		cam.global_transform = (m as Node3D).global_transform
		for i in 6:
			await get_tree().process_frame
		var img := get_viewport().get_texture().get_image()
		img.convert(Image.FORMAT_RGB8)
		var path := "%s/%s_%s.png" % [out_dir, level_name, m.name]
		img.save_png(path)
		print("captured ", path)
	get_tree().quit()
