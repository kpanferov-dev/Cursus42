# Exercise: Find the Intersection of Multiple Lists

## Objective

Write a function `intersection_finder(lists)` that finds all elements that are present in every list of a collection of lists.

The function should return the common elements regardless of whether they are numbers, strings, or other hashable values.

---

## Parameters

### `lists`

A list containing multiple lists.

Example:

```python
[
    [1, 2, "a", 5],
    [1, 5, "a"],
    ["a", 1],
    [3, "5", "7", 1, "a"]
]
```

---

## Requirements

Implement a function that:

1. Accepts a list of lists.
2. Identifies the elements that appear in **all** lists.
3. Returns the common elements as a set.
4. Returns an empty list if no lists are provided.

---

## Example

### Input

```python
intersection_finder([
    [1, 2, "a", 5],
    [1, 5, "a"],
    ["a", 1],
    [3, "5", "7", 1, "a"]
])
```

### Output

```python
{1, "a"}
```

### Explanation

The elements:

```text
1
a
```

appear in every list.

The values:

```text
2
5
3
"5"
"7"
```

do not appear in all lists and are therefore excluded.

---

## Additional Examples

### Example 1

```python
intersection_finder([
    [1, 2, 3],
    [2, 3, 4],
    [3, 2]
])
```

Output:

```python
{2, 3}
```

### Example 2

```python
intersection_finder([
    ["apple", "banana"],
    ["banana", "orange"],
    ["banana"]
])
```

Output:

```python
{"banana"}
```

### Example 3

```python
intersection_finder([])
```

Output:

```python
[]
```

---

## Concepts Practiced

* Lists
* Sets
* Set intersection
* Iteration over collections
* Handling edge cases
* Mixed data types

---

## Notes

A common and efficient approach is to:

1. Convert the first list into a set.
2. Iterate through the remaining lists.
3. Compute the intersection with each subsequent set.

Example:

```python
result &= set(current_list)
```

This operation keeps only the elements that are present in both sets.

The final result contains exactly the elements shared by every list in the input collection.
