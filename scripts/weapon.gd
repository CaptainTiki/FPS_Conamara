class_name Weapon
extends Node3D
## Hitscan weapon held by the camera. Data comes from a WeaponData resource.

signal ammo_changed(ammo: int, max_ammo: int)
signal fired
signal switched(data: WeaponData)

const MASK_WORLD := 1
const MASK_ENEMY := 4

@export var data: WeaponData
## every weapon carried; slot 0 is `data` at start. Ammo is kept per weapon.
@export var slots: Array[WeaponData] = []
@export var impact_fx: PackedScene
@export var tracer_fx: PackedScene

@onready var viewmodel: MeshInstance3D = $Viewmodel
@onready var muzzle: Marker3D = $Viewmodel/Muzzle
@onready var flash_light: OmniLight3D = $Viewmodel/Muzzle/FlashLight
@onready var flash_mesh: MeshInstance3D = $Viewmodel/Muzzle/FlashMesh

var ammo := 0
var cooldown := 0.0
var recoil := 0.0
var bob_t := 0.0
var bob_amount := 0.0
var rng := RandomNumberGenerator.new()
var flash_t := 0.0
var flash_frames := 0
var slot := 0
var _ammo_of := {}
var swap_t := 0.0        # >0 while the viewmodel dips during a swap
var _pending := -1

func _ready() -> void:
	if slots.is_empty():
		slots = [data]
	data = slots[0]
	for d in slots:
		_ammo_of[d] = d.start_ammo
	ammo = _ammo_of[data]
	viewmodel.mesh = data.viewmodel
	viewmodel.position = data.viewmodel_offset
	flash_light.visible = false
	flash_mesh.visible = false

## Switch to slot i (dips the viewmodel, swaps at the bottom). No-op if already held.
func switch_to(i: int) -> void:
	if i < 0 or i >= slots.size() or i == slot or _pending >= 0:
		return
	_pending = i
	swap_t = 0.28

func _apply_switch() -> void:
	_ammo_of[data] = ammo
	slot = _pending
	_pending = -1
	data = slots[slot]
	ammo = _ammo_of[data]
	viewmodel.mesh = data.viewmodel
	cooldown = maxf(cooldown, 0.12)
	ammo_changed.emit(ammo, data.max_ammo)
	switched.emit(data)

func _process(delta: float) -> void:
	cooldown = maxf(cooldown - delta, 0.0)
	recoil = move_toward(recoil, 0.0, delta * 5.0)
	var r := ease(recoil, 0.6)
	bob_t += delta * 9.0 * bob_amount
	var bob := Vector3(cos(bob_t) * 0.012, absf(sin(bob_t)) * 0.016, 0) * bob_amount
	var dip := 0.0
	if swap_t > 0.0:
		swap_t -= delta
		dip = sin(clampf(1.0 - swap_t / 0.28, 0.0, 1.0) * PI) * 0.35
		if _pending >= 0 and swap_t <= 0.14:
			_apply_switch()
	viewmodel.position = data.viewmodel_offset + bob + Vector3(0, 0.01, data.recoil_kick) * r + Vector3(0, -dip, 0)
	viewmodel.rotation.x = deg_to_rad(data.recoil_pitch_deg) * r
	if flash_light.visible:
		flash_t -= delta
		flash_frames += 1
		if flash_t <= 0.0 and flash_frames > 2:
			flash_light.visible = false
			flash_mesh.visible = false

func set_motion(amount: float, delta: float) -> void:
	bob_amount = move_toward(bob_amount, clampf(amount, 0.0, 1.0), delta * 6.0)

## Cells go to the first weapon that uses ammo (the scattergun), whichever is held.
func add_ammo(n: int) -> void:
	for d in slots:
		if d.ammo_per_shot > 0:
			if d == data:
				ammo = mini(ammo + n, d.max_ammo)
				ammo_changed.emit(ammo, data.max_ammo)
			else:
				_ammo_of[d] = mini(int(_ammo_of[d]) + n, d.max_ammo)
			return

func try_fire() -> bool:
	if cooldown > 0.0 or ammo < data.ammo_per_shot or _pending >= 0:
		return false
	cooldown = data.fire_interval
	ammo -= data.ammo_per_shot
	ammo_changed.emit(ammo, data.max_ammo)
	recoil = 1.0
	flash_light.visible = true
	flash_mesh.visible = true
	flash_t = 0.05
	flash_frames = 0
	flash_mesh.rotation.z = rng.randf() * TAU
	_shoot()
	fired.emit()
	return true

func _shoot() -> void:
	var cam := get_parent() as Node3D
	var origin := cam.global_position
	var basis := cam.global_basis
	var space := get_world_3d().direct_space_state
	var shooter := owner as CollisionObject3D
	var hits := {}
	for i in data.pellets:
		var a := rng.randf() * TAU
		var r := sqrt(rng.randf()) * deg_to_rad(data.spread_deg)
		var dir := (basis * Vector3(cos(a) * tan(r), sin(a) * tan(r), -1.0)).normalized()
		var q := PhysicsRayQueryParameters3D.create(origin, origin + dir * data.max_range, MASK_WORLD | MASK_ENEMY)
		if shooter:
			q.exclude = [shooter.get_rid()]
		var res := space.intersect_ray(q)
		var end: Vector3 = origin + dir * data.max_range
		if res:
			end = res.position
			var col: Object = res.collider
			if col.has_method("take_hit"):
				hits[col] = hits.get(col, 0.0) + data.damage
				col.take_hit(data.damage, res.position, dir * data.knockback / data.pellets, owner)
			elif impact_fx:
				_spawn(impact_fx, res.position, res.normal)
		if tracer_fx:
			var t: Tracer = tracer_fx.instantiate()
			get_tree().current_scene.add_child(t)
			t.setup(muzzle.global_position, end, data.tracer_color)

func _spawn(scene: PackedScene, pos: Vector3, normal: Vector3) -> void:
	var fx: Node3D = scene.instantiate()
	get_tree().current_scene.add_child(fx)
	fx.global_position = pos + normal * 0.05
	if normal.cross(Vector3.UP).length() > 0.01:
		fx.look_at(pos + normal, Vector3.UP)
