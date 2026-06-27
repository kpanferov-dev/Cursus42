# Exercise: Palindrome Splitter

## Objective

Write a function `palindrome_spliter(s1)` that determines how many cuts are needed to divide a string into palindromic substrings.

A palindrome is a sequence of characters that reads the same forwards and backwards.

Examples:

* `"aba"` → palindrome
* `"abba"` → palindrome
* `"racecar"` → palindrome
* `"abc"` → not a palindrome

---

## Requirements

Implement a function that:

1. Starts at the beginning of the string.
2. Finds the longest palindrome starting at the current position.
3. Splits the string at the end of that palindrome.
4. Continues processing the remaining characters.
5. Returns the number of cuts required to obtain all palindromic segments.

---

## Example

### Input

```python
palindrome_spliter("abbab")
```

### Decomposition

```text
abba | b
```

Both segments are palindromes.

### Output

```python
1
```

---

## Concepts Practiced

* String manipulation
* String slicing
* Nested functions
* Palindrome detection
* Greedy algorithms
* While loops
* Index management

---

## Notes

A palindrome can be checked using string reversal:

```python
word == word[::-1]
```

The provided implementation uses a greedy approach: at each step, it selects the longest palindromic substring starting at the current position and counts the resulting segments. The final result is the number of cuts between those segments.
