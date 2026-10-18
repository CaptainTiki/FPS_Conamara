class_name Player
extends CharacterBody3D
## Boomer-shooter walker: brisk, not twitchy. All damage comes in via take_hit().

signal died

@export var speed := 7.0
@export var accel := 60.0
@export var max_health := 100.0
@export var crouch_speed := 3.5
@export var climb_speed := 4.5
@export var use_range := 2.6
## enough to get onto a 1.2 m crate, not onto a wall
@export var jump_height := 1.35

const STAND_H := 1.8
const CROUCH_H := 1.0
const EYE_STAND := 1.65
const EYE_CROUCH := 0.85
const MASK_USE := 1 | 16

@onready var intent: PlayerInput = $Intent
@onready var head: Node3D = $Head
@onready var camera: Camera3D = $Head/Camera
@onready var weapon: Weapon = $Head/Camera/Weapon
@onready var hud: Hud = $Hud
@onready var flashlight: SpotLight3D = $Head/Camera/Flashlight
@onready var body_shape: CollisionShape3D = $Shape

var crouching := false
var keys := {}                # keycards picked up (Door.key_id -> true)
var ladder: Node3D            # set by Ladder areas while inside
var shake := 0.0
var _look_target: Object

var health := 100.0
var dead := false

func _ready() -> void:
	add_to_group("player")
	health = max_health
	camera.make_current()
	if not intent.bot:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	hud.set_health(health, max_health)
	weapon.ammo_changed.connect(hud.set_ammo)
	weapon.switched.connect(hud.set_weapon)
	hud.set_weapon(weapon.data)
	weapon.fired.connect(func(): get_tree().call_group("enemies", "hear", global_position))
	hud.set_ammo(weapon.ammo, weapon.data.max_ammo)

func _physics_process(delta: float) -> void:
	if dead:
		velocity = velocity.move_toward(Vector3.ZERO, accel * delta)
		move_and_slide()
		return
	if intent.consume_flashlight():
		toggle_flashlight()
	var ws := intent.consume_weapon()
	if ws == -2:
		weapon.switch_to((weapon.slot + 1) % weapon.slots.size())
	elif ws == -3:
		weapon.switch_to((weapon.slot - 1 + weapon.slots.size()) % weapon.slots.size())
	elif ws >= 0:
		weapon.switch_to(ws)
	_update_use()
	_update_crouch(delta)
	var l := intent.consume_look()
	rotate_y(l.x)
	head.rotation.x = clampf(head.rotation.x + l.y, -1.4, 1.4)
	var dir := (transform.basis * Vector3(intent.move.x, 0, intent.move.y))
	if dir.length() > 1.0:
		dir = dir.normalized()
	var target := dir * (crouch_speed if crouching else speed)
	velocity.x = move_toward(velocity.x, target.x, accel * delta)
	velocity.z = move_toward(velocity.z, target.z, accel * delta)
	if _on_ladder():
		# on a ladder: forward climbs (descends while looking down), back descends,
		# nothing held = hang on. Near the top the climb stops so you can step off.
		var vdir := -intent.move.y * (-1.0 if head.rotation.x < -0.45 else 1.0)
		velocity.y = vdir * climb_speed
		if global_position.y > ladder.global_position.y + float(ladder.get("height")) + 0.3:
			velocity.y = minf(velocity.y, 0.0)
		velocity.x *= 0.5
		velocity.z *= 0.5
	elif not is_on_floor():
		velocity.y -= 20.0 * delta
	if intent.consume_jump() and is_on_floor() and not crouching and not _on_ladder():
		velocity.y = sqrt(2.0 * 20.0 * jump_height)
	move_and_slide()
	if shake > 0.0:
		shake = maxf(shake - delta * 2.5, 0.0)
		camera.h_offset = randf_range(-1, 1) * shake * 0.15
		camera.v_offset = randf_range(-1, 1) * shake * 0.15
	weapon.set_motion(Vector2(velocity.x, velocity.z).length() / speed, delta)
	if intent.fire:
		weapon.try_fire()

## Single damage chokepoint.
func take_hit(amount: float, _point: Vector3, dir: Vector3, _source: Node) -> void:
	if dead:
		return
	health = maxf(health - amount, 0.0)
	velocity += dir * 3.0
	hud.set_health(health, max_health)
	hud.flash_damage(clampf(amount / 25.0, 0.3, 1.0))
	if health <= 0.0:
		dead = true
		died.emit()
		var t := create_tween()
		t.tween_property(head, "position:y", 0.35, 0.6).set_trans(Tween.TRANS_QUAD)
		t.tween_interval(1.4)
		t.tween_callback(get_tree().reload_current_scene)

func _on_ladder() -> bool:
	if ladder == null or not is_instance_valid(ladder):
		return false
	if not is_on_floor():
		return true
	# standing: only start climbing from the bottom, by pushing forward
	return intent.move.y < -0.1 and global_position.y < ladder.global_position.y + 1.0

## Look at a usable thing (anything with interact(), or whose parent has it, e.g. a
## door's slab) and press use. Things with can_use() == false only show their prompt.
func _update_use() -> void:
	var cam_t := camera.global_transform
	var q := PhysicsRayQueryParameters3D.create(cam_t.origin, cam_t.origin - cam_t.basis.z * use_range, MASK_USE)
	q.exclude = [get_rid()]
	q.collide_with_areas = true
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	var pressed := intent.consume_use()
	var target: Object = null
	if hit:
		var c: Object = hit.collider
		if c.has_method("interact"):
			target = c
		elif c is Node and (c as Node).get_parent() and (c as Node).get_parent().has_method("interact"):
			target = (c as Node).get_parent()
	_look_target = target
	if target == null:
		hud.set_prompt("")
		return
	var usable: bool = target.can_use() if target.has_method("can_use") else true
	if pressed and usable:
		target.interact(self)
		usable = target.can_use() if target.has_method("can_use") else true
	hud.set_prompt(target.prompt() if target.has_method("prompt") else "", usable)

func _update_crouch(delta: float) -> void:
	var want := intent.crouch
	if not want and crouching:
		# only stand up if there is headroom
		if test_move(global_transform, Vector3(0, STAND_H - CROUCH_H + 0.05, 0)):
			want = true
	if want != crouching:
		crouching = want
		var cap := body_shape.shape as CapsuleShape3D
		cap.height = CROUCH_H if crouching else STAND_H
		body_shape.position.y = cap.height * 0.5
	head.position.y = move_toward(head.position.y, EYE_CROUCH if crouching else EYE_STAND, delta * 6.0)

func add_key(id: String) -> void:
	keys[id] = true
	hud.set_keys(keys.keys())

func has_key(id: String) -> bool:
	return keys.has(id)

func add_shake(amount: float) -> void:
	shake = maxf(shake, amount)

func toggle_flashlight() -> void:
	flashlight.visible = not flashlight.visible

func heal(amount: float) -> void:
	health = minf(health + amount, max_health)
	hud.set_health(health, max_health)
