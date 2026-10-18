class_name EnemyData
extends Resource
## Content definition for a sprite enemy.

@export var display_name := "Enemy"
@export var max_health := 30.0
@export var move_speed := 3.5
@export var preferred_range := 8.0
@export var wake_range := 24.0
@export var hover_height := 1.3
@export var attack_interval := 2.2
@export var attack_windup := 0.35
@export var projectile: PackedScene
@export var projectile_speed := 11.0
@export var projectile_damage := 10.0
@export var pain_chance := 0.6
@export_enum("fly", "ground") var movement := "fly"
@export_enum("ranged", "melee") var attack := "ranged"
@export var melee_range := 1.6
@export var melee_damage := 8.0
@export var lunge_speed := 9.0
## after first noticing the player, wait this long before the first attack
@export var notice_delay := 0.8
## seconds of clear sight at wake_range before it notices (instant up close)
@export var notice_time := 1.2
## radius it hears the player's gun from, through walls
@export var hear_radius := 9.0
## seconds without a sighting before it gives up the chase and goes dormant
@export var lose_time := 7.0
## waking up alerts idle allies within this radius
@export var alert_radius := 10.0
@export var death_fx: PackedScene
@export_group("Sprite")
@export var frames_idle := PackedInt32Array([0, 1])
@export var frame_attack := 2
@export var frame_pain := 3
@export var frames_death := PackedInt32Array([4, 5, 6, 7])
@export var anim_fps := 4.0
