class_name Explosive
extends StaticBody3D
## Explosive canister: blows after a few hits, hurts everything nearby (including
## other canisters, which chain).

@export var health := 8.0
@export var radius := 4.5
@export var damage := 70.0
@export var blast_fx: PackedScene
var blown := false

func take_hit(amount: float, _point: Vector3, _dir: Vector3, _source: Node) -> void:
	if blown:
		return
	health -= amount
	if health <= 0.0:
		blown = true
		_explode.call_deferred()

func _explode() -> void:
	var centre := global_position + Vector3(0, 0.6, 0)
	if blast_fx:
		var fx: Node3D = blast_fx.instantiate()
		get_tree().current_scene.add_child(fx)
		fx.global_position = centre
	var shape := SphereShape3D.new()
	shape.radius = radius
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = shape
	q.transform = Transform3D(Basis(), centre)
	q.collision_mask = 1 | 2 | 4
	q.exclude = [get_rid()]
	for hit in get_world_3d().direct_space_state.intersect_shape(q, 256):
		var c: Object = hit.collider
		if c is Node3D and c.has_method("take_hit"):
			var n := c as Node3D
			var d := n.global_position.distance_to(centre)
			var amt := damage * clampf(1.0 - d / radius, 0.15, 1.0)
			n.take_hit(amt, centre, (n.global_position - centre).normalized() * 3.0, self)
	for p in get_tree().get_nodes_in_group("player"):
		var pl := p as Player
		var d2 := pl.global_position.distance_to(centre)
		if d2 < 14.0:
			pl.add_shake(clampf(1.2 - d2 / 12.0, 0.15, 1.0))
	queue_free()
