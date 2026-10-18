class_name VentCover
extends StaticBody3D
## Duct grille: blocks the duct until shot off.

var popped := false

func take_hit(_amount: float, _point: Vector3, dir: Vector3, _source: Node) -> void:
	if popped:
		return
	popped = true
	$Shape.set_deferred("disabled", true)
	var t := create_tween().set_parallel()
	t.tween_property(self, "position", position + dir.normalized() * 0.6 + Vector3(0, -0.4, 0), 0.35)
	t.tween_property(self, "rotation_degrees:x", 80.0, 0.35)
	t.chain().tween_interval(4.0)
	t.chain().tween_callback(queue_free)
