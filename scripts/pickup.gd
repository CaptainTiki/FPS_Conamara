class_name Pickup
extends Area3D
## Health or energy cells. Only taken when it would actually help.

@export_enum("health", "cells", "keycard") var kind := "health"
@export var amount := 25
## keycard only: which doors it opens (Door.key_id)
@export var key_id := "crew"

@onready var mesh: Node3D = $Mesh
var t := 0.0

func _ready() -> void:
	body_entered.connect(_on_body)
	t = position.x * 1.3 + position.z * 0.7

func _process(delta: float) -> void:
	t += delta
	mesh.rotation.y = t * 1.6
	mesh.position.y = 0.25 + sin(t * 2.5) * 0.08

func _on_body(b: Node) -> void:
	var p := b as Player
	if p == null or p.dead:
		return
	if kind == "keycard":
		p.add_key(key_id)
		p.hud.toast("%s KEYCARD" % key_id.to_upper(), Color(1, 0.85, 0.3))
	elif kind == "health":
		if p.health >= p.max_health:
			return
		p.heal(amount)
		p.hud.toast("+%d HULL" % amount, Color(1, 0.45, 0.4))
	else:
		if p.weapon.ammo >= p.weapon.data.max_ammo:
			return
		p.weapon.add_ammo(amount)
		p.hud.toast("+%d CELLS" % amount, Color(0.5, 0.95, 1))
	queue_free()
