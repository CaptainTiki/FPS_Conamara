class_name Door
extends Node3D
## Sliding door. Baked into levels by Level for each door / door_half cell.
## A door can be locked for a reason; the lamp over it and the prompt you get by
## looking at it say which. Switches and breakers unlock doors through Level.

## lock reason -> [prompt, lamp colour, lamp energy]
const LOCKS := {
	"none": ["", Color(0.35, 0.9, 1.0), 0.4],
	"power": ["No power", Color(0.0, 0.0, 0.0), 0.0],
	"jammed": ["Jammed", Color(1.0, 0.6, 0.15), 1.1],
	"inside": ["Locked from the inside", Color(1.0, 0.15, 0.1), 0.9],
	"lockdown": ["Lockdown", Color(0.95, 0.25, 0.9), 1.0],
	"seal": ["Pressure seal", Color(0.65, 0.85, 1.0), 0.9],
	"oneway": ["Opens from the other side", Color(0.35, 0.9, 1.0), 0.25],
	"keycard": ["Keycard required", Color(1.0, 0.82, 0.25), 0.9],
}

@export var slab_mesh: Mesh
## local offset when fully open (default: slide up into the header)
@export var open_offset := Vector3(0, 3.1, 0)
@export var slab_width := 1.5
@export var texture := "tb/door"   # map-placed doors: texture path under art/textures/
@export var slab_center_x := 0.0
@export var open_distance := 4.5
@export var speed := 1.4
## why the door won't open ("none" = it opens when you walk up)
@export_enum("none", "power", "jammed", "inside", "lockdown", "seal", "oneway", "keycard") var lock := "none":
	set(v):
		lock = v
		if is_node_ready():
			_update_lamp()
## oneway: the side (door-local Z sign, +1 or -1) the door opens from; once opened
## from that side it stays unlocked (a shortcut back)
@export var open_side := 1
## keycard: which card opens it (Pickup.key_id)
@export var key_id := "crew"
## compatibility: true = locked for lack of power
var locked: bool:
	get:
		return lock != "none"
	set(v):
		lock = "power" if v else "none"

@onready var body: AnimatableBody3D = $Body
@onready var mesh_instance: MeshInstance3D = $Body/Mesh
@onready var shape: CollisionShape3D = $Body/Shape
@onready var lamp: OmniLight3D = $Lamp
@onready var sparks: CPUParticles3D = $Sparks
@onready var lamp_glow: MeshInstance3D = $LampGlow

var open_amount := 0.0
var player: Node3D
var _t := 0.0

func _ready() -> void:
	if slab_mesh == null:   # placed from a .map (no kit slab): build a slab to slab_width from `texture`
		var bm := BoxMesh.new()
		bm.size = Vector3(slab_width, 3.25, 0.16)
		var base := "res://art/textures/" + texture
		var mat: StandardMaterial3D = load("res://art/textures/tb/_template.tres").duplicate()
		mat.albedo_texture = load(base + ".png")
		if ResourceLoader.exists(base + "_normal.png"):
			mat.normal_enabled = true; mat.normal_texture = load(base + "_normal.png")
		if ResourceLoader.exists(base + "_roughness.png"):
			mat.roughness_texture = load(base + "_roughness.png")
		if ResourceLoader.exists(base + "_emission.png"):
			mat.emission_enabled = true; mat.emission_texture = load(base + "_emission.png")
		var tex_m: float = mat.albedo_texture.get_width() / 32.0 if mat.albedo_texture else 2.0   # texture width in metres at 32 u/m
		mat.uv1_scale = Vector3(slab_width / tex_m, 3.25 / tex_m, 1.0)
		bm.material = mat
		mesh_instance.mesh = bm
		mesh_instance.position = Vector3(slab_center_x, 1.625, 0)
	else:
		mesh_instance.mesh = slab_mesh
	var box := BoxShape3D.new()
	box.size = Vector3(slab_width, 3.25, 0.16)
	shape.shape = box
	shape.position = Vector3(slab_center_x, 1.625, 0)
	_update_lamp()
	if Engine.is_editor_hint():
		set_physics_process(false)

func _update_lamp() -> void:
	var d: Array = LOCKS.get(lock, LOCKS["none"])
	lamp.light_color = d[1]
	lamp.light_energy = d[2]
	lamp.visible = d[2] > 0.0
	sparks.emitting = lock == "jammed"
	var m := (lamp_glow.mesh as BoxMesh).material as ShaderMaterial
	m.set_shader_parameter("color", d[1] if d[2] > 0.0 else Color(0.08, 0.08, 0.09))
	m.set_shader_parameter("energy", 2.5 if d[2] > 0.0 else 1.0)

## Looking at a door: nothing to do, but a locked one says why.
func interact(_p: Node) -> void:
	pass

func can_use() -> bool:
	return false

func prompt() -> String:
	if lock == "keycard":
		return "%s keycard required" % key_id.capitalize()
	return LOCKS.get(lock, LOCKS["none"])[0]

func _unlock_self() -> void:
	lock = "none"
	var level := owner as Level
	if level:
		level.doors_changed()

func _physics_process(delta: float) -> void:
	_t += delta
	if player == null:
		player = get_tree().get_first_node_in_group("player") as Node3D
	var target := 0.0
	var near: bool = player != null and player.global_position.distance_to(global_position) < open_distance
	if near and lock == "oneway" and signf(to_local(player.global_position).z) == float(open_side):
		_unlock_self()
	elif near and lock == "keycard" and player.has_method("has_key") and player.has_key(key_id):
		_unlock_self()
		if player.get("hud"):
			player.hud.toast("%s KEYCARD ACCEPTED" % key_id.to_upper(), Color(1, 0.85, 0.3))
	if lock == "none" and near:
		target = 1.0
	open_amount = move_toward(open_amount, target, delta * speed)
	body.position = open_offset * smoothstep(0.0, 1.0, open_amount)
	# jammed: the slab shudders and the lamp stutters; lockdown: the lamp pulses
	if lock == "jammed":
		body.position.x = sin(_t * 31.0) * 0.012 * (1.0 if fmod(_t, 2.3) < 0.4 else 0.0)
		lamp.light_energy = 1.1 if fmod(_t * 7.3, 1.0) > 0.15 else 0.2
	elif lock == "lockdown":
		lamp.light_energy = 0.5 + 0.5 * absf(sin(_t * 3.0))
