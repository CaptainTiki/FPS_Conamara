class_name Projectile
extends Area3D
## Slow, dodgeable energy orb. Hurts whatever take_hit()-able body it touches.

@export var life := 6.0
@export var impact_fx: PackedScene

var velocity := Vector3.ZERO
var damage := 10.0
var source: Node
var t := 0.0

func launch(from: Vector3, vel: Vector3, dmg: float, src: Node) -> void:
	global_position = from
	velocity = vel
	damage = dmg
	source = src

func _ready() -> void:
	body_entered.connect(_on_body)

func _physics_process(delta: float) -> void:
	global_position += velocity * delta
	t += delta
	if t > life:
		queue_free()

func _on_body(b: Node) -> void:
	var src: Node = source if is_instance_valid(source) else null
	if src != null and b == src:
		return
	if b.has_method("take_hit"):
		b.take_hit(damage, global_position, velocity.normalized(), src)
	if impact_fx:
		var fx: Node3D = impact_fx.instantiate()
		get_tree().current_scene.add_child(fx)
		fx.global_position = global_position
	queue_free()
