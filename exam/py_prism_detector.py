#Write a function that searches for all occurrences of a target word pattern within a 2D grid of characters in all 8 cardinal and diagonal directions.

#The directions and their codes are:
#- (1, 0) -> "H" (Horizontal right)
#- (-1, 0) -> "H-" (Horizontal left)
#- (0, 1) -> "V" (Vertical down)
#- (0, -1) -> "V-" (Vertical up)
#- (1, 1) -> "D1" (Diagonal down-right)
#- (-1, -1) -> "D1-" (Diagonal up-left)
#- (-1, 1) -> "D2" (Diagonal up-right)
#- (1, -1) -> "D2-" (Diagonal down-left)

#The function should:
#- Take a grid of strings `grid` and a target string `pattern`.
#- Return a list of tuples `(x, y, direction_code)` for each match, where `x` is the column index and `y` is the row index of the first character.
#- Return an empty list `[]` if either `grid` or `pattern` is empty.

def prism_detector(grid: list[str], pattern: str):
    if not grid or not pattern:
        return []

    result = []

    directions = [
        (1, 0, "H"),
        (-1, 0, "H-"),
        (0, 1, "V"),
        (0, -1, "V-"),
        (1, 1, "D1"),
        (-1, -1, "D1-"),
        (-1, 1, "D2"),
        (1, -1, "D2-")
    ]

    rows = len(grid)
    cols = len(grid[0])

    for y in range(rows):
        for x in range(cols):

            for dx, dy, code in directions:
                match = True

                for i in range(len(pattern)):
                    nx = x + i * dx
                    ny = y + i * dy

                    if nx < 0 or nx >= cols or ny < 0 or ny >= rows:
                        match = False
                        break

                    if grid[ny][nx] != pattern[i]:
                        match = False
                        break

                if match:
                    result.append((x, y, code))

    return result


print(prism_detector(["CAT", "A..", "T.."], "CAT"))
print(prism_detector([], "CAT"))