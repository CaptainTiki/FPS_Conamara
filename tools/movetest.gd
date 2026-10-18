extends Node
## Dev: -- --movetest  drives the player without a keyboard. Walks forward/right from the
## spawn, then teleports to the first stair cell and walks up it. Prints positions.

func _ready() -> void:
	await get_tree().create_timer(1.0).timeout
	var p := get_tree().get_first_node_in_group("player") as CharacterBody3D
	var intent = p.get_node("Intent")
	intent.bot = true
	print("start ", p.global_position, " on_floor=", p.is_on_floor())
	await _walk(p, intent, Vector2(0, -1), 60)
	print("after fwd ", p.global_position, " on_floor=", p.is_on_floor())
	await _walk(p, intent, Vector2(1, 0), 60)
	print("after right ", p.global_position)
	# stairs: find one in the level json, stand on the lower neighbour, walk toward the stair
	var lvl = JSON.parse_string(FileAccess.get_file_as_string("res://levels/%s.json" % get_parent().scene_file_path.get_file().get_basename()))
	if lvl:
		var cells := {}
		for cell in lvl["cells"]:
			cells[Vector2i(cell["x"], cell["y"])] = cell
		for cell in lvl["cells"]:
			if int(cell["t"]) != 4: continue
			for d in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
				var o = cells.get(Vector2i(cell["x"], cell["y"]) + d)
				if o and int(o["f"]) < int(cell["f"]):
					var rows: int = int(lvl["height"])
					# quake (x, y) = (col*64, (rows-row)*64) -> godot (y/32, ., x/32)
					var gx: float = (rows - (float(o["y"]) + 0.5)) * 2.0
					var gz: float = (float(o["x"]) + 0.5) * 2.0
					p.global_position = Vector3(gx, float(o["f"]) + 0.1, gz)
					var target := Vector3((rows - (float(cell["y"]) + 0.5)) * 2.0, float(cell["f"]), (float(cell["x"]) + 0.5) * 2.0)
					for i in 10: await get_tree().physics_frame
					var y0 := p.global_position.y
					var dirw := (target - p.global_position); dirw.y = 0; dirw = dirw.normalized()
					# convert world dir to intent (player local): intent = (strafe, forward-)
					var local := p.global_transform.basis.inverse() * dirw
					print("stairs: start ", p.global_position, " target ", target, " intent ", Vector2(local.x, local.z))
					for k in 4:
						await _walk(p, intent, Vector2(local.x, local.z), 30)
						print("  ", p.global_position, " floor=", p.is_on_floor())
					print("stairs: from y=%.2f to y=%.2f (cell floor %d -> %d), reached=%s" % [y0, p.global_position.y, int(o["f"]), int(cell["f"]), p.global_position.y > y0 + 0.8])
					get_tree().quit()
					return
	get_tree().quit()

func _walk(p: CharacterBody3D, intent, mv: Vector2, frames: int) -> void:
	intent.move = mv
	for i in frames:
		await get_tree().physics_frame
	intent.move = Vector2.ZERO
