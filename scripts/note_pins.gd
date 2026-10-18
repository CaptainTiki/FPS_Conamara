class_name NotePins
extends Node
## Playtest notes. Press Q (action "note") to drop a pin where you stand, type a note,
## Enter saves, Esc cancels. Pins are appended as JSON lines to
##   levels/notes/<level>.jsonl        (editor runs; falls back to user:// in exports)
## and shown in the world as a glowing post with a numbered label. Existing notes load
## on start. Each line: {"n", "note", "level", "pos" [x,y,z], "cell" [col,row], "yaw",
## "pitch", "ts"}. cell is the map-generator grid cell (col, row as in the automap png).

const CELL_M := 2.0
const PIN_COLOR := Color(0.62, 0.83, 1.0)

var level_name := ""
var map_rows := 72        # rows in the generator grid, for col/row conversion
var pins: Array[Dictionary] = []
var typing := false
var _ui: CanvasLayer
var _edit: LineEdit
var _where: Label
var _count: Label
var _pin_root: Node3D

func _ready() -> void:
	level_name = get_parent().scene_file_path.get_file().get_basename()
	_pin_root = Node3D.new(); _pin_root.name = "Pins"; add_child(_pin_root)
	_build_ui()
	_load()

func _notes_path() -> String:
	var dir := "res://levels/notes"
	if not OS.has_feature("editor"):
		dir = "user://notes"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	return dir.path_join(level_name + ".jsonl")

func _load() -> void:
	var f := FileAccess.open(_notes_path(), FileAccess.READ)
	if not f:
		return
	while not f.eof_reached():
		var line := f.get_line().strip_edges()
		if line.is_empty():
			continue
		var d = JSON.parse_string(line)
		if d is Dictionary:
			pins.append(d)
			_spawn_pin(d)
	_count.text = "notes: %d" % pins.size()

func _build_ui() -> void:
	_ui = CanvasLayer.new(); _ui.layer = 20; add_child(_ui)
	_count = Label.new()
	_count.text = "notes: 0"
	_count.position = Vector2(16, 16)
	_count.modulate = Color(PIN_COLOR, 0.7)
	_ui.add_child(_count)
	var box := VBoxContainer.new()
	box.name = "NoteBox"
	box.anchor_left = 0.2; box.anchor_right = 0.8; box.anchor_top = 0.62; box.anchor_bottom = 0.62
	box.offset_left = 0; box.offset_right = 0
	box.visible = false
	_ui.add_child(box)
	_where = Label.new()
	_where.modulate = Color(PIN_COLOR, 0.8)
	box.add_child(_where)
	_edit = LineEdit.new()
	_edit.placeholder_text = "what should change here?  (Enter saves, Esc cancels)"
	_edit.max_length = 240
	_edit.custom_minimum_size.y = 40
	_edit.text_submitted.connect(_on_submit)
	box.add_child(_edit)

func _input(e: InputEvent) -> void:
	if typing:
		if e is InputEventKey and e.pressed and e.keycode == KEY_ESCAPE:
			_close()
			get_viewport().set_input_as_handled()
		return
	if e.is_action_pressed("note") and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		_open()
		get_viewport().set_input_as_handled()

func _player_input() -> PlayerInput:
	var p := get_tree().get_first_node_in_group("player")
	return p.get_node_or_null("Intent") if p else null

func _open() -> void:
	typing = true
	var pi := _player_input()
	if pi:
		pi.bot = true          # stop reading WASD / fire while typing
		pi.move = Vector2.ZERO; pi.fire = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	var cell := _cell()
	_where.text = "%s  ·  cell %d,%d  ·  pin #%d" % [level_name, cell.x, cell.y, pins.size() + 1]
	_edit.text = ""
	_ui.get_node("NoteBox").visible = true
	_edit.grab_focus.call_deferred()

func _close() -> void:
	typing = false
	_ui.get_node("NoteBox").visible = false
	_edit.release_focus()
	var pi := _player_input()
	if pi:
		pi.bot = false
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _on_submit(text: String) -> void:
	text = text.strip_edges()
	if text.is_empty():
		_close(); return
	var cam := get_viewport().get_camera_3d()
	var p := get_tree().get_first_node_in_group("player") as Node3D
	var pos: Vector3 = p.global_position if p else (cam.global_position if cam else Vector3.ZERO)
	var cell := _cell()
	var d := {
		"n": pins.size() + 1, "note": text, "level": level_name,
		"pos": [snappedf(pos.x, 0.01), snappedf(pos.y, 0.01), snappedf(pos.z, 0.01)],
		"cell": [cell.x, cell.y],
		"yaw": snappedf(rad_to_deg(cam.global_rotation.y), 1) if cam else 0.0,
		"pitch": snappedf(rad_to_deg(cam.global_rotation.x), 1) if cam else 0.0,
		"ts": Time.get_datetime_string_from_system(true),
	}
	var f := FileAccess.open(_notes_path(), FileAccess.READ_WRITE)
	if not f:
		f = FileAccess.open(_notes_path(), FileAccess.WRITE)
	if f:
		f.seek_end()
		f.store_line(JSON.stringify(d))
		f.close()
	pins.append(d)
	_spawn_pin(d)
	_count.text = "notes: %d" % pins.size()
	print("note #%d saved: %s" % [d["n"], text])
	_close()

## generator grid cell of the player: FuncGodot maps quake (x, y) -> godot (z, x) / 32,
## and export_map.py flips rows (quake y = (rows - row) * 64)
func _cell() -> Vector2i:
	var p := get_tree().get_first_node_in_group("player") as Node3D
	if not p:
		return Vector2i(-1, -1)
	var col := int(floor(p.global_position.z / CELL_M))
	var row := map_rows - 1 - int(floor(p.global_position.x / CELL_M))
	return Vector2i(col, row)

func _spawn_pin(d: Dictionary) -> void:
	var pos := Vector3(d["pos"][0], d["pos"][1], d["pos"][2])
	var root := Node3D.new()
	root.position = pos
	var mat := StandardMaterial3D.new()
	mat.albedo_color = PIN_COLOR
	mat.emission_enabled = true
	mat.emission = PIN_COLOR
	mat.emission_energy_multiplier = 2.0
	var post := MeshInstance3D.new()
	var pm := BoxMesh.new(); pm.size = Vector3(0.08, 1.1, 0.08); post.mesh = pm
	post.position.y = 0.55; post.material_override = mat; root.add_child(post)
	var head := MeshInstance3D.new()
	var hm := BoxMesh.new(); hm.size = Vector3(0.3, 0.3, 0.3); head.mesh = hm
	head.position.y = 1.25; head.material_override = mat; root.add_child(head)
	var lbl := Label3D.new()
	lbl.text = "#%d  %s" % [d["n"], d["note"]]
	lbl.position.y = 1.65
	lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	lbl.no_depth_test = true
	lbl.font_size = 40; lbl.pixel_size = 0.004
	lbl.modulate = PIN_COLOR
	lbl.outline_size = 10
	root.add_child(lbl)
	_pin_root.add_child(root)
