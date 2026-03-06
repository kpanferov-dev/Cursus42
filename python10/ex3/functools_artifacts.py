"""
functools_artifacts.py
Playing with functools and operator
"""
import functools as f
import operator as o

def spell_reducer(spells: list[int], operation: str) -> int:
    """Applies an op to each pair of elems in an accumulative way"""
    ops = {
        "add":      o.add,
        "multiply": o.mul,
        "max":      lambda a, b: a if a > b else b,
        "min":      lambda a, b: a if a < b else b,
    }
    return f.reduce(ops[operation], spells)


def partial_enchanter(base_enchantment: callable) -> dict[str, callable]:
    """Freezes some arguments of a function, creating a new simpler one"""
    return {
        "fire_enchant": f.partial(base_enchantment, power=50, element="fire"),
        "ice_enchant": f.partial(base_enchantment, power=50, element="ice"),
        "lightning_enchant": f.partial(base_enchantment, power=50, element="lightning"),
    }


@f.lru_cache(maxsize=None)
def memoized_fibonacci(n: int) -> int:
    """
    When function is pure , same input gives same output
    there is no reason to calculate it again
    """
    if n <= 1:
        return n
    return memoized_fibonacci(n - 1) + memoized_fibonacci(n - 2)


def spell_dispatcher() -> callable:
    """Function more beautifull than if/elif is instance
        depending of type it calls one or other
    """
    @f.singledispatch
    def cast(spell):
        return f"Unknown spell type: {type(spell)}"

    @cast.register(int)
    def _(spell):
        return f"Damage spell cast! Power: {spell}"

    @cast.register(str)
    def _(spell):
        return f"Enchantment applied: {spell}"

    @cast.register(list)
    def _(spell):
        return f"Multi-cast! Spells: {', '.join(str(s) for s in spell)}"

    return cast


def main():
     # --- spell_reducer demo ---
    print("Testing spell reducer...")
    spells = [10, 20, 30, 40]
    print(f"Sum:      {spell_reducer(spells, 'add')}")
    print(f"Product:  {spell_reducer(spells, 'multiply')}")
    print(f"Max:      {spell_reducer(spells, 'max')}")
    print(f"Min:      {spell_reducer(spells, 'min')}")

    # --- partial_enchanter demo ---
    print("\nTesting partial enchanter...")
    def base_enchantment(target, power, element):
        return f"{element.capitalize()} enchantment (power {power}) applied to {target}"

    enchants = partial_enchanter(base_enchantment)
    print(enchants["fire_enchant"](target="Sword"))
    print(enchants["ice_enchant"](target="Shield"))
    print(enchants["lightning_enchant"](target="Staff"))

    # --- memoized_fibonacci demo ---
    print("\nTesting memoized fibonacci...")
    print(f"Fib(10): {memoized_fibonacci(10)}")
    print(f"Fib(15): {memoized_fibonacci(15)}")
    print(f"Fib(20): {memoized_fibonacci(20)}")
    print(f"Cache info: {memoized_fibonacci.cache_info()}")

    # --- spell_dispatcher demo ---
    print("\nTesting spell dispatcher...")
    cast = spell_dispatcher()
    print(cast(100))
    print(cast("Flaming Sword"))
    print(cast([10, 20, 30]))


if __name__ == "__main__":
    main()
