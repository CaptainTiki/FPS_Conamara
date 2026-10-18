class_name Switch
extends StaticBody3D
## Usable switch that unlocks doors by grid cell: a door release beside a door
## that's locked from one side, a lockdown console, a seal release. One use.
## Set up by tools/build_level.gd ([links]) or by hand in the inspector.

## door cells this switch unlocks (both halves of a double door)
@export var targets: Array[Vector3i] = []
@export var action := "Release door"
@onready var lamp: OmniLight3D = $Lamp
var used := false

func _ready() -> void:
	_update_lamp()

func interact(_p: Node) -> void:
	if used:
		return
	used = true
	_update_lamp()
	var level := owner as Level
	if level == null:
		level = get_tree().current_scene as Level
	if level:
		level.unlock(targets)

func can_use() -> bool:
	return not used

func prompt() -> String:
	return action if not used else "Done"

func _update_lamp() -> void:
	lamp.light_color = Color(0.3, 1.0, 0.45) if used else Color(1.0, 0.35, 0.15)
