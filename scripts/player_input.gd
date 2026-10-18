class_name PlayerInput
extends Node
## Intent component: the only place that reads devices. Player consumes the
## intent fields; a bot (playtest) can drive them instead by setting bot = true.

@export var mouse_sensitivity := 0.0022
var bot := false
var move := Vector2.ZERO       # x = strafe, y = forward(-)/back(+)
var look := Vector2.ZERO       # radians this frame (yaw, pitch)
var fire := false
var flashlight := false   # true for one frame when toggled
var weapon_slot := -1     # slot asked for this frame (-1 none); -2 next, -3 previous
var use := false          # true for one frame when pressed
var crouch := false       # held
var jump := false         # true for one frame when pressed

func _unhandled_input(e: InputEvent) -> void:
	if bot:
		return
	if e is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		look += Vector2(-e.relative.x, -e.relative.y) * mouse_sensitivity
	elif e is InputEventKey and e.pressed and e.keycode == KEY_ESCAPE:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif e is InputEventMouseButton and e.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		get_viewport().set_input_as_handled()

func _process(_d: float) -> void:
	if bot:
		return
	move = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	fire = Input.is_action_pressed("fire") and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED
	if Input.is_action_just_pressed("flashlight"):
		flashlight = true
	if Input.is_action_just_pressed("use"):
		use = true
	crouch = Input.is_action_pressed("crouch")
	if Input.is_action_just_pressed("jump"):
		jump = true
	if Input.is_action_just_pressed("weapon_1"):
		weapon_slot = 0
	elif Input.is_action_just_pressed("weapon_2"):
		weapon_slot = 1
	elif Input.is_action_just_pressed("weapon_next"):
		weapon_slot = -2
	elif Input.is_action_just_pressed("weapon_prev"):
		weapon_slot = -3

func consume_look() -> Vector2:
	var l := look
	look = Vector2.ZERO
	return l

func consume_flashlight() -> bool:
	var f := flashlight
	flashlight = false
	return f

func consume_use() -> bool:
	var u := use
	use = false
	return u

func consume_weapon() -> int:
	var w := weapon_slot
	weapon_slot = -1
	return w

func consume_jump() -> bool:
	var j := jump
	jump = false
	return j
