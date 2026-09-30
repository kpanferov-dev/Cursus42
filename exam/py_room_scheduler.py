#Write a function that determines the minimum number of meeting rooms required to schedule a list of meeting time intervals without overlap, and assigns meetings to rooms.

#Each meeting is represented as a list of two integers `[start_time, end_time]`.

#The function should:
#- Sort meetings by start time and assign them to available rooms sequentially.
#- Return a dictionary containing:
#  - `"total_rooms"`: the integer count of rooms required.
#  - `"schedule"`: a list of lists containing the scheduled intervals for each room.
#- If the input list is empty, return `{"total_rooms": 0, "schedule": []}`.

def py_room_scheduler(meetings: list[list[int]]) -> dict:
    rooms = []

    for meeting in sorted(meetings):
        for room in rooms:
            if room[-1][1] <= meeting[0]:
                room.append(meeting)
                break
        else:
            rooms.append([meeting])

    return {"total_rooms": len(rooms), "schedule": rooms}


print(py_room_scheduler([[0, 30], [5, 10], [15, 20]]))
print(py_room_scheduler([]))


def schedule_meetings(intervals: list[tuple[int, int]]) -> tuple[int, list]:
    rooms = []

    for meeting in sorted(intervals):
        for room in rooms:
            if room[-1][1] <= meeting[0]:
                room.append(meeting)
                break
        else:
            rooms.append([meeting])

    return len(rooms), rooms

print(schedule_meetings([(0, 30), (5, 10), (15, 20)]))
print(schedule_meetings([]))