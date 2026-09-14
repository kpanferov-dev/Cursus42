#Write a function island_matrix_counter(matrix) that receives a 2D matrix containing "1" and "0" string values and returns the total number of islands.

#An island is a group of connected "1" cells. Cells are considered connected only when they are directly adjacent horizontally (left, right) or vertically (up, down). Diagonal cells do not count as connected.

#Requirements:
#- "1" represents land.
#- "0" represents water.
#- Count each separate island exactly once.
#- An empty matrix (or matrix with no rows) should return 0.
#- DFS/BFS traversal or matrix mutation can be used to explore each complete island.

def island_matrix_counter(matrix: list[list[str]]) -> int:
    if not matrix:
        return 0

    rows = len(matrix)
    cols = len(matrix[0])
    islands = 0

    def dfs(row, col):
        if row < 0 or row >= rows:
            return

        if col < 0 or col >= cols:
            return

        if matrix[row][col] == "0":
            return

        matrix[row][col] = "0"

        dfs(row - 1, col)  # arriba
        dfs(row + 1, col)  # abajo
        dfs(row, col - 1)  # izquierda
        dfs(row, col + 1)  # derecha

    for row in range(rows):
        for col in range(cols):
            if matrix[row][col] == "1":
                islands += 1
                dfs(row, col)

    return islands

print(island_matrix_counter([["1", "1", "1", "1", "0"], ["1", "1", "1", "0", "0"], ["1", "1", "1", "1", "0"], ["0", "0", "0", "0", "0"]]))
print(island_matrix_counter([["1", "1", "0", "0", "0"], ["1", "1", "0", "0", "0"], ["0", "0", "1", "0", "0"], ["0", "0", "0", "1", "1"]]))
print(island_matrix_counter([]))