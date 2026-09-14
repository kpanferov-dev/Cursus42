#Write a function that determines the minimum number 
# of meeting rooms required to schedule a list of 
# meeting time intervals without overlap, and assigns meetings to rooms.

#Each interval is represented as a tuple of `(start_time, end_time)`.

#The function should:
#- Sort meetings by start time and assign them to available rooms sequentially.
#- Return a tuple `(num_rooms, rooms)` where 
# `num_rooms` is the integer count of rooms required, 
# and `rooms` is a list of lists containing the scheduled intervals for each room.
#- If the input list is empty, return `(0, [])`.

def schedule_meetings(intervals: list[tuple[int, int]]) -> tuple[int, list]:
    if not intervals:
        return (0, [])

    intervals = sorted(intervals)

    rooms = []
    end_times = []

    for meeting in intervals:
        start, end = meeting

        room_found = False

        for i in range(len(rooms)):
            if end_times[i] <= start:
                rooms[i].append(meeting)
                end_times[i] = end
                room_found = True
                break

        if not room_found:
            rooms.append([meeting])
            end_times.append(end)

    return (len(rooms), rooms)

print(schedule_meetings([(0, 30), (5, 10), (15, 20)]))
print(schedule_meetings([]))