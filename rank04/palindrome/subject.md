# Exercise: List Palindromic Words

## Objective

Write a function `list_palindromes(words)` that identifies all palindromic words in a list and returns them sorted alphabetically.

A palindrome is a word that reads the same forwards and backwards, ignoring letter case.

Examples:

* `"abba"` → palindrome
* `"hoh"` → palindrome
* `"RaceCar"` → palindrome
* `"hello"` → not a palindrome

---

## Parameters

### `words`

A list of strings.

Example:

```python id="5w1l9e"
["abba", "aab", "hoh", "aaaaaaaaaa", "va"]
```

---

## Requirements

Implement a function that:

1. Iterates through all words in the list.
2. Checks whether each word is a palindrome.
3. Ignores differences between uppercase and lowercase letters.
4. Collects all palindromic words.
5. Returns the resulting list sorted in ascending alphabetical order.

---

## Example

### Input

```python id="i48gk9"
list_palindromes([
    "abba",
    "aab",
    "hoh",
    "aaaaaaaaaa",
    "va"
])
```

### Output

```python id="r6zq5w"
["aaaaaaaaaa", "abba", "hoh"]
```

### Explanation

The words:

```text id="a7c0qh"
abba
hoh
aaaaaaaaaa
```

are palindromes because they read the same forwards and backwards.

The words:

```text id="9r6n7l"
aab
va
```

are not palindromes and are therefore excluded.

---

## Additional Examples

### Example 1

```python id="7c6k3g"
list_palindromes([
    "RaceCar",
    "level",
    "python",
    "madam"
])
```

Output:

```python id="z8k2qp"
["RaceCar", "level", "madam"]
```

### Example 2

```python id="s5v1nx"
list_palindromes([
    "ABC",
    "aba",
    "Aa",
    "xyz"
])
```

Output:

```python id="m3q7ft"
["Aa", "aba"]
```

### Example 3

```python id="e2n9hr"
list_palindromes([])
```

Output:

```python id="v4k8jm"
[]
```

---

## Concepts Practiced

* Lists
* Strings
* String slicing
* Case-insensitive comparison
* Conditional statements
* Sorting
* Iteration

---

## Notes

A palindrome can be detected by comparing a word with its reversed version:

```python id="y5p3wc"
word.lower() == word.lower()[::-1]
```

Using `lower()` ensures that the comparison is case-insensitive, so words such as `"RaceCar"` and `"Aa"` are correctly identified as palindromes.

After collecting all palindromic words, the result should be sorted before being returned.
