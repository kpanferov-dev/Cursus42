#Write a function that generates an `n x n` 2D matrix filled with numbers from 1 to `n^2` in clockwise spiral order.
#The spiral starts at the top-left cell (0, 0) moving right, then down, then left, then up, continuing inwards.

def generate_spiral(n: int) -> list[list[int]]:
    matrix = [[0] * n for _ in range(n)]

    top = 0
    bottom = n - 1
    left = 0
    right = n - 1
    value = 1

    while top <= bottom and left <= right:
        # De izquierda a derecha
        for col in range(left, right + 1):
            matrix[top][col] = value
            value += 1
        top += 1

        # De arriba a abajo
        for row in range(top, bottom + 1):
            matrix[row][right] = value
            value += 1
        right -= 1

        # De derecha a izquierda
        if top <= bottom:
            for col in range(right, left - 1, -1):
                matrix[bottom][col] = value
                value += 1
            bottom -= 1

        # De abajo a arriba
        if left <= right:
            for row in range(bottom, top - 1, -1):
                matrix[row][left] = value
                value += 1
            left += 1

    return matrix

matrix = generate_spiral(3)

for row in matrix:
    print(row)
