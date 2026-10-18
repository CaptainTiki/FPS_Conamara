class_name Elevator
extends Node3D
## Platform lift between stops (local heights). Ride with the panel on the platform;
## call it from an ElevatorCall post on any stop.

signal arrived(stop: int)

@export var stops := PackedFloat32Array([0.0, 4.0])
@export var speed := 2.6

@onready var platform: AnimatableBody3D = $Platform
var stop := 0
var target := 0
var moving := false

func _physics_process(delta: float) -> void:
	if not moving:
		return
	var goal := stops[target]
	platform.position.y = move_toward(platform.position.y, goal, speed * delta)
	if is_equal_approx(platform.position.y, goal):
		moving = false
		stop = target
		arrived.emit(stop)

func go_to(i: int) -> void:
	if i == stop and not moving:
		return
	target = clampi(i, 0, stops.size() - 1)
	moving = true

## ride panel on the platform: go to the next stop
func ride() -> void:
	if not moving:
		go_to((stop + 1) % stops.size())

func status() -> String:
	return "moving" if moving else "at stop %d" % stop
