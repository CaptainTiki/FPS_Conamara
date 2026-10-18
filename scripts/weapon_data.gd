class_name WeaponData
extends Resource
## Content definition for a hitscan weapon.

@export var display_name := "Weapon"
@export var damage := 6.0
@export var pellets := 1
@export var spread_deg := 0.0
@export var fire_interval := 0.5
@export var max_range := 60.0
@export var ammo_per_shot := 1
@export var max_ammo := 50
@export var start_ammo := 25
@export var knockback := 4.0
@export var viewmodel: Mesh
@export var viewmodel_offset := Vector3(0.26, -0.27, -0.5)
@export var recoil_kick := 0.09
@export var recoil_pitch_deg := 7.0
@export var tracer_color := Color(0.4, 0.95, 1.0)
