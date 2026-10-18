class_name Ladder
extends Area3D
## Climbable ladder. While the player is inside the volume, forward climbs, back
## descends, and letting go hangs on. Baked by tools/build_level.gd (`l` full-height
## ladders, `u` short ladders off a ledge up through a ceiling grate).

## climb height from this node's origin to the landing above
@export var height := 4.0

func _ready() -> void:
	if not is_equal_approx(height, 4.0):
		# short ladder: size the climb volume, the backstop and the mesh to fit
		var area := BoxShape3D.new()
		area.size = Vector3(1.2, height + 0.4, 1.3)
		$Shape.shape = area
		$Shape.position.y = (height + 0.4) * 0.5
		var stop := BoxShape3D.new()
		stop.size = Vector3(2, height, 0.8)
		$Backstop/Shape.shape = stop
		$Backstop/Shape.position.y = height * 0.5
		$Mesh.scale.y = (height + 0.9) / 5.0
	body_entered.connect(func(b: Node): if b is Player: (b as Player).ladder = self)
	body_exited.connect(func(b: Node): if b is Player and (b as Player).ladder == self: (b as Player).ladder = null)
