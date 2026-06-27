# Exercise: Merge and Sort Multiple Lists

## Objective

Write a function `merge_sorted_lists(lists)` that merges multiple lists into a single list and returns the result sorted in ascending order.

---

## Parameters

### `lists`

A list of lists containing comparable elements (e.g., integers).

Example:

```python id="p1q8kd"
[[1, 2, 4, 3], [5, 1, 5, 23], [21, 7, 0]]
```

---

## Requirements

Implement a function that:

1. Accepts a list of lists.
2. Merges all inner lists into a single list.
3. Sorts the merged list in ascending order.
4. Returns the sorted result.

---

## Example

### Input

```python id="k2v9ds"
merge_sorted_lists([[1,2,4,3], [5, 1, 5, 23], [21, 7, 0]])
```

### Output

```python id="m7x3lz"
[0, 1, 1, 2, 3, 4, 5, 5, 7, 21, 23]
```

---

## Explanation

Given the input:

```text id="a9c2pw"
[1, 2, 4, 3]  
[5, 1, 5, 23]  
[21, 7, 0]
```

### Step 1: Merge all lists

```text id="v6t3qr"
[1, 2, 4, 3, 5, 1, 5, 23, 21, 7, 0]
```

### Step 2: Sort the result

```text id="n8f4ld"
[0, 1, 1, 2, 3, 4, 5, 5, 7, 21, 23]
```

---

## Additional Examples

### Example 1

```python id="t5k2mq"
merge_sorted_lists([[3, 1], [2, 0]])
```

Output:

```python id="x9p7wv"
[0, 1, 2, 3]
```

---

### Example 2

```python id="r4h8cn"
merge_sorted_lists([[], [10, 5], [3]])
```

Output:

```python id="b6j1sa"
[3, 5, 10]
```

---

### Example 3

```python id="u3z9ek"
merge_sorted_lists([])
```

Output:

```python id="c8d2fy"
[]
```

---

## Concepts Practiced

* Lists of lists
* List concatenation
* Iteration
* Sorting
* Flattening data structures

---

## Notes

The function works by flattening all inner lists into a single list:

```python id="q1m8vn"
result.extend(l)
```

Then it applies Python’s built-in sorting:

```python id="w7c2td"
sorted(result)
```

This ensures the final output is fully ordered regardless of the original structure of the input lists.
