class_name Tracer
extends MeshInstance3D
## Short-lived energy streak from muzzle to impact.

@export var life := 0.1
var t := 0.0
var frames := 0

func setup(from: Vector3, to: Vector3, color: Color) -> void:
	var len := from.distance_to(to)
	global_position = (from + to) * 0.5
	if len > 0.01:
		look_at(to, Vector3.UP if absf((to - from).normalized().y) < 0.99 else Vector3.RIGHT)
	scale = Vector3(1, 1, len)
	pass  # colour comes from the tracer material

func _process(delta: float) -> void:
	t += delta
	frames += 1
	var k := clampf(1.0 - t / life, 0.25, 1.0)
	scale.x = k
	scale.y = k
	if t >= life and frames > 2:   # always survive 2 drawn frames (low-fps safe)
		queue_free()
