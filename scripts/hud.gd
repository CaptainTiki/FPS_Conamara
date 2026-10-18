class_name Hud
extends CanvasLayer
## Minimal HUD: crosshair, health, cells, damage flash.

@onready var health_label: Label = $Health/Value
@onready var ammo_label: Label = $Ammo/Value
@onready var damage_flash: ColorRect = $DamageFlash
@onready var toast_label: Label = $Toast
@onready var banner: Label = $Banner
@onready var prompt_label: Label = $Prompt
@onready var keys_label: Label = $Keys

func set_health(h: float, _max_h: float) -> void:
	health_label.text = str(int(ceil(h)))
	health_label.modulate = Color(1, 0.35, 0.3) if h <= 25.0 else Color.WHITE

func set_ammo(a: int, max_a: int) -> void:
	ammo_label.text = str(a) if max_a > 0 else "--"

func set_weapon(d: WeaponData) -> void:
	$Ammo/Caption.text = "CELLS" if d.ammo_per_shot > 0 else d.display_name.to_upper()

func flash_damage(strength: float) -> void:
	damage_flash.color.a = 0.45 * strength
	var t := create_tween()
	t.tween_property(damage_flash, "color:a", 0.0, 0.4)

func toast(text: String, color := Color.WHITE) -> void:
	toast_label.text = text
	toast_label.modulate = color
	toast_label.modulate.a = 1.0
	var t := create_tween()
	t.tween_interval(0.8)
	t.tween_property(toast_label, "modulate:a", 0.0, 0.6)

func show_banner(text: String) -> void:
	banner.text = text
	banner.visible = true

## usable = false shows the text alone (a locked door saying why it's shut)
func set_prompt(text: String, usable := true) -> void:
	if text == "":
		prompt_label.text = ""
	else:
		prompt_label.text = ("[E]  " + text) if usable else text

## keycards held, shown bottom centre
func set_keys(ids: Array) -> void:
	keys_label.text = "   ".join(ids.map(func(k): return "[%s KEY]" % str(k).to_upper()))
