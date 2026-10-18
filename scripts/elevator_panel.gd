class_name ElevatorPanel
extends StaticBody3D
## Usable button: on the platform (ride) or on a call post (call to `call_stop`).

@export var elevator: Elevator
## -1 = ride button on the platform; >= 0 = call post for that stop
@export var call_stop := -1

func interact(_p: Node) -> void:
	if elevator == null:
		return
	if call_stop < 0:
		elevator.ride()
	else:
		elevator.go_to(call_stop)

func prompt() -> String:
	if elevator and elevator.moving:
		return "Elevator moving..."
	if call_stop < 0:
		return "Ride elevator"
	return "Call elevator" if elevator and elevator.stop != call_stop else "Elevator is here"
