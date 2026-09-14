#Write a function that determines whether a directed graph contains at least one cycle.

#The function takes a dictionary representing an adjacency list where keys are integer node IDs and values are lists of integer neighbor node IDs.

#The function should:
#- Return True if the directed graph contains a cycle.
#- Return False if the graph is acyclic or if the input graph dictionary is empty.
#- Correctly handle graphs with multiple disconnected components.

def py_graph_cycle_detector(graph: dict[int, list[int]]) -> bool:
    visited = set()
    path = set()

    def dfs(node):
        if node in path:
            return True

        if node in visited:
            return False

        visited.add(node)
        path.add(node)

        for neighbor in graph.get(node, []):
            if dfs(neighbor):
                return True

        path.remove(node)
        return False

    for node in graph:
        if dfs(node):
            return True

    return False

print(py_graph_cycle_detector({0: [1], 1: [2], 2: [0]}))
print(py_graph_cycle_detector({0: [1], 1: [2], 2: []}))
print(py_graph_cycle_detector({}))