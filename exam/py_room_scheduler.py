#Write a function that determines the minimum number of meeting rooms required to schedule a list of meeting time intervals without overlap, and assigns meetings to rooms.

#Each meeting is represented as a list of two integers `[start_time, end_time]`.

#The function should:
#- Sort meetings by start time and assign them to available rooms sequentially.
#- Return a dictionary containing:
#  - `"total_rooms"`: the integer count of rooms required.
#  - `"schedule"`: a list of lists containing the scheduled intervals for each room.
#- If the input list is empty, return `{"total_rooms": 0, "schedule": []}`.

from typing import Any

def py_room_scheduler(meetings: list[list[int]]) -> dict[str, Any]:
    if not meetings:
        return {"total_rooms": 0, "schedule": []}

    # Sort by start time.
    meetings = sorted(meetings, key=lambda meeting: meeting[0])

    # Each room stores its scheduled meetings.
    schedule: list[list[list[int]]] = []

    # Track the end time of the last meeting in each room.
    room_end_times: list[int] = []

    for meeting in meetings:
        start, end = meeting

        # Find the first room whose previous meeting has ended.
        room_index = None
        for i, room_end in enumerate(room_end_times):
            if room_end <= start:
                room_index = i
                break

        if room_index is None:
            # No room is available, so create a new one.
            schedule.append([meeting])
            room_end_times.append(end)
        else:
            schedule[room_index].append(meeting)
            room_end_times[room_index] = end

    return {
        "total_rooms": len(schedule),
        "schedule": schedule,
    }

print(py_room_scheduler([[0, 30], [5, 10], [15, 20]]))
print(py_room_scheduler([]))