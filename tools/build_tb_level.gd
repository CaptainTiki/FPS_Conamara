extends SceneTree
## .map -> levels/<name>.tscn, headless. FuncGodot builds the geometry, lights and
## entity scenes; this wraps them in a level root with the shared environment and saves
## the result as a normal scene (fully editable; rebuild after changing the .map).
## Run: godot --headless --path . -s tools/build_tb_level.gd -- levels/seed1337.map

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	var map_path: String = args[0] if args.size() else "levels/seed1337.map"
	if not map_path.begins_with("res://"):
		map_path = "res://" + map_path
	var name := map_path.get_file().get_basename()

	var root := Node3D.new()
	root.name = name.capitalize().replace(" ", "")
	root.set_script(load("res://scripts/level.gd"))

	var env := WorldEnvironment.new()
	env.name = "WorldEnvironment"
	env.environment = load("res://art/env/level.tres")
	root.add_child(env)
	env.owner = root

	var fgm := FuncGodotMap.new()
	fgm.name = "Map"
	fgm.local_map_file = map_path
	fgm.map_settings = load("res://levels/map_settings.tres")
	root.add_child(fgm)
	fgm.owner = root
	get_root().add_child(root)

	print("building ", map_path)
	var t := Time.get_ticks_msec()
	fgm.build()
	print("build() returned")
	print("map built in %d ms" % (Time.get_ticks_msec() - t))

	# everything FuncGodot generated must be owned by the root to be saved
	_own(fgm, root)
	# lights: make them cast no shadow unless the map said so (Compatibility renderer budget)
	var packed := PackedScene.new()
	packed.pack(root)
	var out := "res://levels/%s.tscn" % name
	var err := ResourceSaver.save(packed, out)
	print("level saved: ", out, " (", error_string(err), ") nodes: ", _count(root))
	quit()

func _own(n: Node, owner: Node) -> void:
	for c in n.get_children():
		if c.owner == null or c.owner != owner:
			c.owner = owner
		_own(c, owner)

func _count(n: Node) -> int:
	var k := 1
	for c in n.get_children():
		k += _count(c)
	return k
