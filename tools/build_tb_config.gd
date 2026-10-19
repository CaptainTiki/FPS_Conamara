extends SceneTree
## Builds the FuncGodot side of the TrenchBroom pipeline, headless:
##   levels/conamara_fgd.tres      entity definitions (what TrenchBroom can place)
##   levels/map_settings.tres      scale, texture folder, material template
##   levels/trenchbroom/Conamara/  GameConfig.cfg + Collider.fgd + icon -> copy (or symlink)
##                                    this folder into TrenchBroom's games directory, then set
##                                    the game path to this repo root so textures resolve.
## Run: godot --headless --path . -s tools/build_tb_config.gd

const OUT := "res://levels/"

func _point(classname: String, desc: String, scene: String = "", node_class: String = "",
		props: Dictionary = {}, groups: Array[String] = [], auto_apply := false, size := Vector3(32, 32, 64)) -> FuncGodotFGDPointClass:
	var c := FuncGodotFGDPointClass.new()
	c.classname = classname
	c.description = desc
	if scene != "":
		c.scene_file = load(scene)
	if node_class != "":
		c.node_class = node_class
	var cp: Dictionary[String, Variant] = {}
	for k in props: cp[k] = props[k]
	c.class_properties = cp
	c.node_groups = groups
	c.auto_apply_to_matching_node_properties = auto_apply
	var mp: Dictionary[String, Variant] = {"size": AABB(-size / 2.0, size / 2.0), "color": Color(0.6, 0.85, 1.0)}
	c.meta_properties = mp
	return c

func _init() -> void:
	var fgd := FuncGodotFGDFile.new()
	fgd.fgd_name = "Conamara"
	fgd.base_fgd_files = [preload("res://addons/func_godot/fgd/func_godot_fgd.tres")]
	var defs: Array[Resource] = []

	# player start -> the real player scene
	defs.append(_point("info_player_start", "Player spawn. Faces 'angle'.", "res://scenes/actors/player.tscn", "",
		{"angle": 0.0}, [], false, Vector3(32, 32, 56)))

	# light -> OmniLight3D; property names are Godot's so FuncGodot applies them directly
	var light := _point("light", "Omni light. light_color 'r g b', light_energy, omni_range (metres).", "", "OmniLight3D",
		{"light_color": Color(1.0, 0.9, 0.76), "light_energy": 2.0, "omni_range": 8.0, "shadow_enabled": false}, [], true, Vector3(16, 16, 16))
	light.meta_properties["color"] = Color(1.0, 0.85, 0.4)
	defs.append(light)

	# door -> scenes/props/door.tscn (slab 1.5 m x 3.25 m; frame it with brushes). lock: none/jammed/inside/lockdown/seal/keycard
	defs.append(_point("prop_door", "Door scene. 'angle' 0 = slab across X (corridor runs E-W), 90 = across Y.",
		"res://scenes/props/door.tscn", "", {"angle": 0.0, "lock": "none", "slab_width": 1.5, "texture": "tb/door"}, [], true, Vector3(48, 8, 104)))

	# ladder -> scenes/props/ladder.tscn; height = metres to the landing. Wall on the ladder's -Z:
	# angle 0 wall west, 180 east, 90 south, 270 north (quake axes).
	defs.append(_point("prop_ladder", "Ladder. 'height' metres to the landing; the wall is on the ladder's back.",
		"res://scenes/props/ladder.tscn", "", {"angle": 0.0, "height": 4.0}, [], true, Vector3(40, 24, 128)))

	# screenshot marker: a Marker3D in group 'shots', named from shot_name
	var shot := _point("shot", "Screenshot marker for -- --capture (camera at origin, facing angle).", "", "Marker3D",
		{"angle": 0.0, "shot_name": "shot"}, ["shots"], false, Vector3(8, 8, 8))
	shot.name_property = "shot_name"
	shot.meta_properties["color"] = Color(1.0, 0.4, 0.4)
	defs.append(shot)

	# existing free-placed props, as point entities so TrenchBroom shows their footprint
	for p in [
			["prop_crate", "res://scenes/props/crate.tscn", Vector3(32, 32, 32)],
			["prop_crate_stack", "res://scenes/props/crate_stack.tscn", Vector3(32, 32, 64)],
			["prop_canister", "res://scenes/props/explosive.tscn", Vector3(16, 16, 32)],
			["prop_console", "res://scenes/props/switch_console.tscn", Vector3(40, 24, 40)],
			["prop_breaker", "res://scenes/props/breaker.tscn", Vector3(24, 8, 48)],
			["item_health", "res://scenes/props/pickup_health.tscn", Vector3(12, 12, 12)],
			["item_cells", "res://scenes/props/pickup_cells.tscn", Vector3(12, 12, 12)],
			["monster_drifter", "res://scenes/actors/drifter.tscn", Vector3(32, 32, 56)],
			["monster_skitter", "res://scenes/actors/skitter.tscn", Vector3(24, 24, 20)],
			["trigger_exit", "res://scenes/props/exit.tscn", Vector3(32, 32, 64)]]:
		defs.append(_point(p[0], "Collider scene " + p[1], p[1], "", {"angle": 0.0}, [], false, p[2]))

	fgd.entity_definitions = defs
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT))
	ResourceSaver.save(fgd, OUT + "conamara_fgd.tres")

	# map settings
	var ms := FuncGodotMapSettings.new()
	ms.inverse_scale_factor = 32.0
	ms.entity_fgd = fgd
	ms.use_groups_hierarchy = true         # TrenchBroom layers become child nodes (floor / walls / beams ...)
	ms.base_texture_dir = "res://art/textures"
	ms.base_material_dir = "res://art/textures/materials"
	ms.default_material = load("res://art/textures/tb/_template.tres")
	ms.save_generated_materials = true
	ms.albedo_map_pattern = "%s"
	ms.uv_unwrap_texel_size = 2.0
	ResourceSaver.save(ms, OUT + "map_settings.tres")

	# TrenchBroom game config (written straight to the repo; no editor settings needed)
	var cfg := TrenchBroomGameConfig.new()
	cfg.game_name = "Conamara"
	cfg.fgd_file = fgd
	cfg.textures_root_folder = "art/textures"
	cfg.entity_scale = "32"
	var dir := ProjectSettings.globalize_path(OUT + "trenchbroom/Conamara")
	DirAccess.make_dir_recursive_absolute(dir)
	var f := FileAccess.open(dir + "/GameConfig.cfg", FileAccess.WRITE)
	f.store_string(cfg._build_class_text())
	f.close()
	fgd.do_export_file(FuncGodotFGDFile.FuncGodotTargetMapEditors.TRENCHBROOM, dir)
	var icon: Image = cfg.icon.get_image()
	icon.resize(32, 32)
	icon.save_png(dir + "/icon.png")
	print("tb config saved: ", OUT, "conamara_fgd.tres, map_settings.tres, trenchbroom/Conamara/")
	quit()
