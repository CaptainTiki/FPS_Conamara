class_name FlickerLight
extends OmniLight3D
## Failing light: mostly dim with stuttering bursts. Baked by Level for broken fixtures.

@export var base_energy := 0.6
var t := 0.0
var next_burst := 0.0
var burst_left := 0.0
var rng := RandomNumberGenerator.new()

func _ready() -> void:
	rng.randomize()
	next_burst = rng.randf_range(0.5, 3.0)
	if Engine.is_editor_hint():
		set_process(false)

func _process(delta: float) -> void:
	t += delta
	if burst_left > 0.0:
		burst_left -= delta
		light_energy = base_energy * (1.6 if rng.randf() < 0.5 else 0.05)
	else:
		light_energy = base_energy * (0.25 + 0.05 * sin(t * 37.0))
		next_burst -= delta
		if next_burst <= 0.0:
			burst_left = rng.randf_range(0.1, 0.6)
			next_burst = rng.randf_range(1.0, 5.0)
