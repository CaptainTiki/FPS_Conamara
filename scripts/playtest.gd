class_name Playtest
extends Node
## Automated playtest bot (dev tooling, enabled with `-- --playtest`).
## Drives the Player through its PlayerInput intent: walks toward the nearest
## live enemy, aims, fires when lined up. Captures screenshots at key moments
## to res://shots/play_*.png and prints a combat log, then quits.

const MAX_TIME := 180.0
const MAX_SHOTS := 14

var player: Player
var t := 0.0
var shots_taken := 0
var log_lines: PackedStringArray = []
var shots_fired := 0
var kills := 0
var capture_queue: Array[Array] = []   # [delay, tag]
var known_dead := {}
var out_dir := ""

func _ready() -> void:
	out_dir = ProjectSettings.globalize_path("res://shots")
	for f in DirAccess.get_files_at(out_dir):
		if f.begins_with("play_"):
			DirAccess.remove_absolute(out_dir + "/" + f)
	await get_tree().physics_frame
	player = get_tree().get_first_node_in_group("player") as Player
	player.intent.bot = true
	player.weapon.fired.connect(_on_fired)
	var old_hit := player.health
	player.died.connect(func(): _log("PLAYER DIED"); _queue(0.3, "player_dead"))
	_queue(0.2, "start")

func _log(s: String) -> void:
	var line := "[%5.2f] %s" % [t, s]
	log_lines.append(line)
	print(line)

func _queue(delay: float, tag: String) -> void:
	capture_queue.append([t + delay, tag])

func _on_fired() -> void:
	shots_fired += 1
	if shots_fired <= 2 or shots_fired % 4 == 0:
		_queue(0.02, "fire%02d" % shots_fired)

func _enemies() -> Array[Enemy]:
	var out: Array[Enemy] = []
	for n in get_tree().get_nodes_in_group("enemies"):
		out.append(n as Enemy)
	if out.is_empty():
		for n in get_tree().current_scene.get_node("Enemies").get_children():
			if n is Enemy:
				out.append(n)
	return out

func _physics_process(delta: float) -> void:
	if player == null:
		return
	t += delta
	var last_hp := player.health
	var live: Array[Enemy] = []
	for e in _enemies():
		if not is_instance_valid(e):
			continue
		if e.state == Enemy.State.DEAD:
			if not known_dead.has(e):
				known_dead[e] = true
				kills += 1
				_log("kill #%d" % kills)
				_queue(0.05, "kill%d_a" % kills)
				_queue(0.35, "kill%d_b" % kills)
		else:
			live.append(e)
	var exit_done := false
	var ex := get_tree().current_scene.find_child("Exit", true, false) as ExitTrigger
	if ex:
		exit_done = ex.done
	if (live.is_empty() and ex == null) or exit_done or player.dead or t > MAX_TIME:
		if not _end_shot:
			_end_shot = true
			shots_taken = mini(shots_taken, MAX_SHOTS - 1)
			_queue(0.4, "end")
		if capture_queue.is_empty():
			_finish(live.size())
		player.intent.fire = false
		player.intent.move = Vector2.ZERO
		return
	_log_t += delta
	if _log_t > 5.0:
		_log_t = 0.0
		var lv := get_tree().current_scene as Level
		var cc := lv.cell_of(player.global_position) if lv else Vector2i.ZERO
		_log("pos cell %d,%d  live %d" % [cc.x, cc.y, live.size()])
	_stuck_t += delta
	if _stuck_t > 4.0:
		if player.global_position.distance_to(_stuck_pos) < 1.0:
			_log("stuck at %s, sidestepping" % str(player.global_position))
			_unstick = 0.8
			_unstick_side = -_unstick_side
		_stuck_pos = player.global_position
		_stuck_t = 0.0
	if _unstick > 0.0:
		_unstick -= delta
		player.intent.move = Vector2(_unstick_side, 0.6)
		player.intent.fire = false
		return
	# target: nearest live enemy we can actually see (within 22m)
	var head := player.head.global_position
	var level := get_tree().current_scene as Level
	var space := player.get_world_3d().direct_space_state
	var best: Enemy = null
	var best_d := 22.0
	for e in live:
		var dd := e.global_position.distance_to(head)
		if dd < best_d:
			var q := PhysicsRayQueryParameters3D.create(head, e.global_position + Vector3(0, 0.35, 0), 1)
			if space.intersect_ray(q).is_empty():
				best = e
				best_d = dd
	var exit := get_tree().current_scene.find_child("Exit", true, false) as Node3D
	var goal: Node3D = exit if exit else (live[0] if not live.is_empty() else null)
	# power first: walk to any breaker not yet thrown and throw it
	for b in get_tree().current_scene.find_children("*", "Breaker", true, false):
		if not (b as Breaker).thrown:
			goal = b
			if player.global_position.distance_to(b.global_position) < 2.2:
				_log("throwing breaker")
				(b as Breaker).interact(player)
				_queue(0.6, "power_on")
			break
	var move_dir := Vector3.ZERO
	if best == null:
		# nothing in view: walk the level toward the exit (or the nearest enemy)
		if goal and level:
			move_dir = level.flow_dir(player.global_position, goal.global_position, true)
			if move_dir == Vector3.ZERO:
				move_dir = (goal.global_position - player.global_position) * Vector3(1, 0, 1)
		if move_dir.length() > 0.01:
			var yaw_w := atan2(-move_dir.x, -move_dir.z)
			player.rotation.y = lerp_angle(player.rotation.y, yaw_w, 0.15)
			player.head.rotation.x = lerpf(player.head.rotation.x, 0.0, 0.2)
		player.intent.move = Vector2(0, -1)
		player.intent.fire = false
		return
	var aim := best.global_position + Vector3(0, 0.35, 0)
	var d := aim - head
	var yaw := atan2(-d.x, -d.z)
	var pitch := atan2(d.y, Vector2(d.x, d.z).length())
	player.rotation.y = lerp_angle(player.rotation.y, yaw, 0.3)
	player.head.rotation.x = lerpf(player.head.rotation.x, pitch, 0.3)
	var err := absf(angle_difference(player.rotation.y, yaw)) + absf(player.head.rotation.x - pitch)
	var close_melee := best.data.attack == "melee" and best_d < 4.5
	if close_melee:
		player.intent.move = Vector2(0.4 * sin(t * 2.0), 1.0)   # back-pedal while firing
	elif best_d > 12.0:
		player.intent.move = Vector2(0, -1)
	else:
		player.intent.move = Vector2(sin(t * 1.3), 0)          # strafe
	player.intent.fire = err < 0.08

func _process(_d: float) -> void:
	if player and player.health < _prev_hp:
		_log("player hit -> %d" % int(player.health))
		if shots_taken < MAX_SHOTS:
			_queue(0.0, "hurt%d" % int(player.health))
	if player:
		_prev_hp = player.health
	if capture_queue.is_empty():
		return
	capture_queue.sort_custom(func(a, b): return a[0] < b[0])
	if capture_queue[0][0] <= t:
		var item: Array = capture_queue.pop_front()
		if shots_taken < MAX_SHOTS:
			_capture(item[1])

var _prev_hp := 100.0
var _stuck_pos := Vector3.ZERO
var _stuck_t := 0.0
var _log_t := 0.0
var _unstick := 0.0
var _end_shot := false
var _unstick_side := 1.0
var _busy := false

func _capture(tag: String) -> void:
	if _busy:
		return
	_busy = true
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.convert(Image.FORMAT_RGB8)
	shots_taken += 1
	img.save_png("%s/play_%02d_%s.png" % [out_dir, shots_taken, tag])
	_busy = false

func _finish(remaining: int) -> void:
	_log("DONE  time=%.1fs shots=%d kills=%d remaining=%d hp=%d" % [t, shots_fired, kills, remaining, int(player.health)])
	var f := FileAccess.open(out_dir + "/play_log.txt", FileAccess.WRITE)
	f.store_string("\n".join(log_lines))
	set_physics_process(false)
	set_process(false)
	await get_tree().create_timer(0.1).timeout
	get_tree().quit()
