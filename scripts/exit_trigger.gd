class_name ExitTrigger
extends Area3D
## End of a section: shows the clear banner with kills and time.

signal reached

var done := false
var play_time := 0.0   # seconds of actual play: mouse captured (or bot driving)
var total := 0
var player: Player

func _ready() -> void:
	body_entered.connect(_on_body)
	await get_tree().process_frame
	total = get_tree().get_nodes_in_group("enemies").size()

func _process(delta: float) -> void:
	if done:
		return
	if player == null:
		player = get_tree().get_first_node_in_group("player") as Player
	var bot := player != null and player.intent.bot
	if bot or Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		play_time += delta

func _on_body(b: Node) -> void:
	var p := b as Player
	if p == null or done:
		return
	done = true
	var alive := 0
	for e in get_tree().get_nodes_in_group("enemies"):
		if (e as Enemy).state != Enemy.State.DEAD:
			alive += 1
	var secs := play_time
	p.hud.show_banner("SECTION CLEAR\nanomalies %d / %d    time %d:%02d" % [total - alive, total, int(secs) / 60, int(secs) % 60])
	reached.emit()
