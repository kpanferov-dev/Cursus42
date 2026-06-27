# Exercise: Package Dependency Resolver

## Objective

Write a function `package_dependency(packages)` that determines a valid installation order for a set of packages based on their dependencies.

A package can only be installed after all of its dependencies have been installed.

---

## Parameters

### `packages`

A dictionary where:

* Keys are package names.
* Values are lists of dependencies (other package names).

Example:

```python id="d2k8vn"
{
    "b": ["hola"],
    "a": ["hola", "b"],
    "adios": ["a", "b"],
    "hola": []
}
```

---

## Requirements

Implement a function that:

1. Determines an order to install all packages.
2. Ensures that each package appears **after all its dependencies**.
3. Processes multiple installable packages in alphabetical order when possible.
4. Returns a list representing the valid installation order.
5. Returns an empty list if no valid order exists (circular or unresolved dependencies).

---

## Example

### Input

```python id="q8x1lm"
package_dependency({
    "b": ["hola"],
    "a": ["hola", "b"],
    "adios": ["a", "b"],
    "hola": []
})
```

---

### Output

```python id="t6c9rq"
["hola", "b", "a", "adios"]
```

---

## Step-by-Step Explanation

### Initial state

```text id="m4p7sd"
Installed: []
Remaining: hola, b, a, adios
```

---

### Step 1

Install packages with no dependencies:

```text id="v9k3nd"
hola
```

```text id="c1x7qw"
Installed: [hola]
```

---

### Step 2

Now packages whose dependencies are satisfied:

```text id="r8f2jp"
b (depends on hola)
```

```text id="l3v9ta"
Installed: [hola, b]
```

---

### Step 3

Next installable packages:

```text id="n7b5zx"
a (depends on hola, b)
```

```text id="s6d1ko"
Installed: [hola, b, a]
```

---

### Step 4

Final package:

```text id="p2m8vc"
adios (depends on a, b)
```

```text id="u5r0lf"
Installed: [hola, b, a, adios]
```

---

## Additional Examples

### Example 1: Independent packages

```python id="y1t6qa"
package_dependency({
    "c": [],
    "b": [],
    "a": []
})
```

Output:

```python id="z9n2hw"
["a", "b", "c"]
```

---

### Example 2: Linear dependency chain

```python id="k8p3ld"
package_dependency({
    "c": ["b"],
    "b": ["a"],
    "a": []
})
```

Output:

```python id="w4c7vn"
["a", "b", "c"]
```

---

### Example 3: Circular dependency (invalid case)

```python id="h6x1qs"
package_dependency({
    "a": ["b"],
    "b": ["a"]
})
```

Output:

```python id="e3m9tp"
[]
```

---

## Concepts Practiced

* Dependency resolution
* Graph-like structures
* Topological sorting (Kahn-style approach)
* Dictionary manipulation
* Iterative processing
* Cycle detection (implicit)

---

## Notes

This algorithm repeatedly selects all packages whose dependencies have already been installed:

```python id="f7k2jd"
if all(dep in result for dep in deps):
```

Packages are processed in alphabetical order within each iteration:

```python id="a8v5lc"
temp.sort()
```

If at any iteration no package can be installed, it means there is a circular dependency or missing dependency, and the function returns an empty list.
