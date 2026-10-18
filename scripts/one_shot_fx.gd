class_name OneShotFx
extends Node3D
## Fires every CPUParticles3D child once, flashes an optional light, then frees itself.

@export var lifetime := 1.2
@export var light_fade := 0.15

@onready var light: OmniLight3D = get_node_or_null("Light")
var t := 0.0
var light_energy := 0.0
var frames := 0

func _ready() -> void:
	for c in get_children():
		if c is CPUParticles3D:
			c.emitting = true
	if light:
		light_energy = light.light_energy

func _process(delta: float) -> void:
	t += delta
	frames += 1
	if light:
		light.light_energy = light_energy * (1.0 if frames <= 1 else clampf(1.0 - t / light_fade, 0.0, 1.0))
	if t >= lifetime and frames > 2:
		queue_free()
