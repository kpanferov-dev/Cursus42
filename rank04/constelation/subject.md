# Exercise: Constellation Generator

## Objective

Write a function `constelation(stars, size)` that generates a square representation of a constellation using a grid of characters.

The grid should use:

* `"*"` to represent a star.
* `"."` to represent empty space.

The positions of the stars are given as a list of coordinates.

---

## Parameters

### `stars`

A list of tuples `(row, column)` indicating the positions of stars in the grid.

Example:

```python
stars = [
    (0, 0),
    (0, 2),
    (1, 1)
]
```

### `size`

An integer representing the width and height of the square grid.

---

## Requirements

Implement a function that:

1. Creates a square grid of dimensions `size × size`.
2. Places a `"*"` character at every coordinate specified in `stars`.
3. Fills all remaining positions with `"."`.
4. Returns the resulting grid as a list of strings.

---

## Example

### Input

```python
stars = [
    (0,0), (0,2), (0,3),
    (1,1), (1,3),
    (2,2), (2,4),
    (3,1)
]

constelation(stars, 5)
```

### Output

```python
[
    "*.**.",
    ".*.*.",
    "..*.*",
    ".*...",
    "....."
]
```

### Visual Representation

```text
*.**.
.*.*.
..*.*
.*...
.....
```

---

## Concepts Practiced

* Lists and tuples
* Sets for fast lookup
* Nested loops
* Grid generation
* Coordinate systems
* String construction

---

## Notes

For efficiency, the list of star coordinates can be converted into a set:

```python
set_stars = set(stars)
```

This allows constant-time membership checks when determining whether a position contains a star.

The algorithm iterates through every cell of the grid and builds each row character by character, placing `"*"` when a star exists at the current coordinate and `"."` otherwise.
