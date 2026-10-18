class_name Enemy
extends CharacterBody3D
## Flat sprite anomaly. Behaviour comes from EnemyData:
##   fly + ranged  (Drifter): hovers, keeps its preferred range, lobs slow orbs
##   ground + melee (Skitter): scuttles straight in, lunges, comes in packs
## Out of sight it follows the Level's grid flow field toward the player.
## Awareness: IDLE until it has had the player in clear sight long enough
## (instant up close, notice_time at wake_range), got shot, heard the gun
## nearby, or an ally it can see woke up. NOTICE is a short twitch before it
## moves. Lose sight for lose_time and it walks to where it last saw you,
## then goes dormant again.
## All damage arrives through take_hit().

enum State { IDLE, NOTICE, CHASE, WINDUP, PAIN, DEAD }

const MASK_WORLD := 1

@export var data: EnemyData

@onready var sprite: MeshInstance3D = $Sprite
@onready var eye: Marker3D = $Eye
@onready var glow: OmniLight3D = $Glow
@onready var shape: CollisionShape3D = $Shape

var state := State.IDLE
var health := 0.0
var target: Node3D
var level: Level
var state_t := 0.0
var attack_t := 0.0
var anim_t := 0.0
var flash := 0.0
var home_y := 0.0
## fliers keep this height above whatever floor is under them (stairs, lower decks)
var hover := 1.3
var _ground := 0.0
var _ground_t := 0.0
var rng := RandomNumberGenerator.new()
var mat: ShaderMaterial
var strafe_dir := 1.0
var sight_t := 0.0
var sees := false
var blocked_t := 0.0
var unstick_t := 0.0
var unstick_dir := Vector3.ZERO
var suspicion := 0.0
var last_seen := Vector3.ZERO
var unseen_t := 0.0

func _ready() -> void:
	add_to_group("enemies")
	health = data.max_health
	mat = sprite.get_active_material(0) as ShaderMaterial
	rng.randomize()
	attack_t = rng.randf_range(0.6, data.attack_interval)
	home_y = global_position.y
	anim_t = rng.randf() * 4.0
	strafe_dir = 1.0 if rng.randf() < 0.5 else -1.0
	level = owner as Level
	if level == null:
		level = get_tree().current_scene as Level

func _physics_process(delta: float) -> void:
	state_t += delta
	anim_t += delta
	flash = move_toward(flash, 0.0, delta * 8.0)
	if target == null:
		target = get_tree().get_first_node_in_group("player") as Node3D
		if target == null:
			return
	# line of sight is checked a few times a second, not every frame
	sight_t -= delta
	if sight_t <= 0.0 and state != State.DEAD:
		sight_t = 0.15
		sees = _can_see()
	var dist := _flat(target.global_position - global_position).length()
	match state:
		State.IDLE:
			_set_frame(_idle_frame())
			_gravity(delta)
			move_and_slide()
			# suspicion builds while the player is in clear sight, faster the closer they are
			if sees and dist < data.wake_range:
				var closeness := 1.0 - clampf(dist / data.wake_range, 0.0, 1.0)
				suspicion += delta * (1.0 / maxf(data.notice_time, 0.05)) * (1.0 + closeness * 6.0)
				if dist < 4.0:
					suspicion = 1.0
			else:
				suspicion = maxf(0.0, suspicion - delta * 0.5)
			if suspicion >= 1.0:
				wake()
		State.NOTICE:
			_set_frame(_idle_frame())
			velocity = velocity.move_toward(Vector3(0, velocity.y, 0), 20.0 * delta)
			_gravity(delta)
			move_and_slide()
			if state_t >= data.notice_delay:
				_enter(State.CHASE)
		State.CHASE:
			_set_frame(_idle_frame())
			if sees:
				last_seen = target.global_position
				unseen_t = 0.0
			else:
				unseen_t += delta
				if unseen_t > data.lose_time and _flat(last_seen - global_position).length() < 2.5:
					_go_dormant()
					return
			_steer(delta, dist)
			attack_t -= delta
			# melee needs the player in the open: no glass, door or floor in between
			var dy := absf(target.global_position.y - global_position.y)
			var in_reach := (dist < data.melee_range and sees and dy < 1.6) if data.attack == "melee" else sees
			if attack_t <= 0.0 and in_reach:
				_enter(State.WINDUP)
		State.WINDUP:
			_set_frame(data.frame_attack)
			if data.attack == "melee":
				_steer(delta, dist, 0.35)
			else:
				velocity = velocity.move_toward(Vector3(0, velocity.y, 0), 20.0 * delta)
				_gravity(delta)
				move_and_slide()
			if state_t >= data.attack_windup:
				if data.attack == "melee":
					_lunge(dist)
				else:
					_fire()
				attack_t = data.attack_interval * rng.randf_range(0.8, 1.2)
				_enter(State.CHASE)
		State.PAIN:
			_set_frame(data.frame_pain)
			velocity = velocity.move_toward(Vector3(0, velocity.y, 0), 10.0 * delta)
			_gravity(delta)
			move_and_slide()
			if state_t > 0.18:
				_enter(State.CHASE)
		State.DEAD:
			var f := int(state_t * 10.0)
			_set_frame(data.frames_death[mini(f, data.frames_death.size() - 1)])
			glow.light_energy = maxf(0.0, glow.light_energy - delta * 6.0)
			velocity = velocity.move_toward(Vector3(0, velocity.y, 0), 10.0 * delta)
			_gravity(delta)
			move_and_slide()
			if f >= data.frames_death.size() + 2:
				queue_free()
	if mat:
		mat.set_shader_parameter("flash", flash)

func _idle_frame() -> int:
	var fps := data.anim_fps * (3.0 if data.movement == "ground" and state == State.CHASE else 1.0)
	return data.frames_idle[int(anim_t * fps) % data.frames_idle.size()]

func _enter(s: State) -> void:
	state = s
	state_t = 0.0

## Wake up (noticed the player, got shot, heard the gun, or an ally it can see woke).
## `instant` skips the notice twitch (being shot does that).
func wake(alert_others := true, instant := false) -> void:
	if state != State.IDLE:
		return
	suspicion = 1.0
	attack_t = maxf(attack_t, data.notice_delay)
	flash = 0.35
	last_seen = target.global_position if target else global_position
	unseen_t = 0.0
	_enter(State.CHASE if instant else State.NOTICE)
	if alert_others:
		for n in get_tree().get_nodes_in_group("enemies"):
			var e := n as Enemy
			if e and e != self and e.state == State.IDLE and e.global_position.distance_to(global_position) < data.alert_radius and _can_see_point(e.eye.global_position):
				e.wake(false)

## Heard a gunshot at `at` (Player calls this through the "enemies" group).
func hear(at: Vector3) -> void:
	if state == State.IDLE and at.distance_to(global_position) < data.hear_radius:
		wake(false)

func _go_dormant() -> void:
	suspicion = 0.0
	velocity = Vector3(0, velocity.y, 0)
	_enter(State.IDLE)

func _can_see_point(p: Vector3) -> bool:
	var q := PhysicsRayQueryParameters3D.create(eye.global_position, p, MASK_WORLD)
	return get_world_3d().direct_space_state.intersect_ray(q).is_empty()

func _set_frame(f: int) -> void:
	if mat:
		mat.set_shader_parameter("frame", f)

func _flat(v: Vector3) -> Vector3:
	return Vector3(v.x, 0, v.z)

func _gravity(delta: float) -> void:
	if data.movement == "ground" and not is_on_floor():
		velocity.y -= 20.0 * delta

func _ground_y() -> float:
	_ground_t -= get_physics_process_delta_time()
	if _ground_t <= 0.0:
		_ground_t = 0.2
		var q := PhysicsRayQueryParameters3D.create(global_position, global_position + Vector3(0, -12, 0), MASK_WORLD)
		var hit := get_world_3d().direct_space_state.intersect_ray(q)
		_ground = hit.position.y if hit else home_y - hover
	return _ground

func _can_see() -> bool:
	var q := PhysicsRayQueryParameters3D.create(eye.global_position, target.global_position + Vector3(0, 1.5, 0), MASK_WORLD)
	return get_world_3d().direct_space_state.intersect_ray(q).is_empty()

## Direction toward the player: straight at them when visible, otherwise along
## the Level's grid flow field (goes round corners and through doors).
func _seek_dir() -> Vector3:
	var to := _flat(target.global_position - global_position)
	if sees or level == null:
		return to.normalized()
	var d := level.flow_dir(global_position, last_seen)
	return d if d != Vector3.ZERO else _flat(last_seen - global_position).normalized()

func _steer(delta: float, dist: float, speed_scale := 1.0) -> void:
	var fwd := _seek_dir()
	if not sees and _flat(last_seen - global_position).length() < 1.5:
		fwd = Vector3.ZERO   # reached where it last saw the player: wait and listen
	var want := Vector3.ZERO
	if data.attack == "melee":
		want = fwd * data.move_speed
		if sees and dist < 6.0:   # weave a little on the final approach
			want += Vector3(-fwd.z, 0, fwd.x) * strafe_dir * sin(anim_t * 5.0) * 2.0
	else:
		var side := Vector3(-fwd.z, 0, fwd.x) * strafe_dir
		if rng.randf() < delta * 0.4:
			strafe_dir = -strafe_dir
		var push := 1.0
		if sees:
			push = 0.0
			if dist > data.preferred_range + 1.5:
				push = 1.0
			elif dist < data.preferred_range - 2.0:
				push = -0.7
		want = (fwd * push + side * (0.45 if sees else 0.0)).normalized() * data.move_speed
	want *= speed_scale
	# unstick: pushing hard but barely moving -> sidestep for a moment
	if unstick_t > 0.0:
		unstick_t -= delta
		want = unstick_dir * data.move_speed
	elif want.length() > 1.0 and _flat(get_real_velocity()).length() < want.length() * 0.2:
		blocked_t += delta
		if blocked_t > 0.4:
			blocked_t = 0.0
			unstick_t = 0.5
			var f := want.normalized()
			unstick_dir = (Vector3(-f.z, 0, f.x) * (1.0 if rng.randf() < 0.5 else -1.0) - f * 0.5).normalized()
	else:
		blocked_t = 0.0
	if data.movement == "fly":
		var bob := sin(anim_t * 2.2) * 0.25
		want.y = (_ground_y() + hover + bob - global_position.y) * 3.0
		velocity = velocity.move_toward(want, 10.0 * delta)
	else:
		var vy := velocity.y
		velocity = velocity.move_toward(Vector3(want.x, 0, want.z), 30.0 * delta)
		velocity.y = vy
		_gravity(delta)
	move_and_slide()

func _lunge(dist: float) -> void:
	var dir := _flat(target.global_position - global_position).normalized()
	velocity = dir * data.lunge_speed + Vector3(0, 2.5, 0)
	if dist < data.melee_range + 0.5 and _can_see() and absf(target.global_position.y - global_position.y) < 1.6 and target.has_method("take_hit"):
		target.take_hit(data.melee_damage, global_position, dir, self)

func _fire() -> void:
	if data.projectile == null or target == null:
		return
	var p: Projectile = data.projectile.instantiate()
	get_tree().current_scene.add_child(p)
	var aim := target.global_position + Vector3(0, 1.3, 0)
	p.launch(eye.global_position, (aim - eye.global_position).normalized() * data.projectile_speed, data.projectile_damage, self)

## Single damage chokepoint.
func take_hit(amount: float, _point: Vector3, dir: Vector3, _source: Node) -> void:
	if state == State.DEAD:
		return
	health -= amount
	flash = 1.0
	velocity += dir
	if health <= 0.0:
		_die()
		return
	if state == State.IDLE or state == State.NOTICE:
		state = State.IDLE
		wake(true, true)
	elif state != State.WINDUP and rng.randf() < data.pain_chance:
		_enter(State.PAIN)

func _die() -> void:
	_enter(State.DEAD)
	shape.set_deferred("disabled", true)
	collision_layer = 0
	collision_mask = 1
	if data.death_fx:
		var fx: Node3D = data.death_fx.instantiate()
		get_tree().current_scene.add_child(fx)
		fx.global_position = global_position + Vector3(0, 0.4 if data.movement == "ground" else 0.0, 0)
