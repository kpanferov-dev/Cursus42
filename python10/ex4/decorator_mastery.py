"""
decorator_mastery.py
Playing with decorators
"""

import time
import functools
import random


def spell_timer(func: callable) -> callable:
    """Decorator that measures and prints the execution time of a function."""
    @functools.wraps(func)
    def wrapper(name):
        print(f"Casting {func.__name__}...")
        start = time.time()
        result = func(name)
        elapsed = time.time() - start
        print(f"Spell completed in {elapsed:.3f} seconds")
        return result
    return wrapper


def power_validator(min_power: int) -> callable:
    """
    Decorator factory that validates the power argument.
    """
    def decorator(func: callable) -> callable:
        @functools.wraps(func)
        def wrapper(self, spell_name: str, power: int) -> str:
            if power >= min_power:
                return func(self, spell_name, power)
            return "Insufficient power for this spell"
        return wrapper
    return decorator


def retry_spell(max_attempts: int) -> callable:
    """Decorator factory that retries a function up to max_attempts times."""
    def decorator(func: callable) -> callable:
        @functools.wraps(func)
        def wrapper(spell_name: str) -> str:
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(spell_name)
                except Exception:
                    print("Spell failed, retrying... " +
                          f"(attempt {attempt}/{max_attempts})")
            return f"Spell casting failed after {max_attempts} attempts"
        return wrapper
    return decorator


class MageGuild:
    """Guild of mages demonstrating
    @staticmethod and decorated instance methods.
    """

    @staticmethod
    def validate_mage_name(name: str) -> bool:
        """Return True if name is >= 3 chars
        and contains only letters/spaces.
        """
        return (len(name) >= 3 and
                all(ch.isalpha() or ch.isspace() for ch in name))

    @power_validator(min_power=10)
    def cast_spell(self, spell_name: str, power: int) -> str:
        """Cast a spell if power is sufficient."""
        return f"Successfully cast {spell_name} with {power} power"


@spell_timer
def fireball(name: str) -> str:
    time.sleep(0.101)
    return f"{name.capitalize()} cast!"


@retry_spell(max_attempts=3)
def trash_skill(name: str):
    if random.random() < 0.5:
        raise RuntimeError(f"{name} failed")
    return f"{name} successfully cast!"


if __name__ == "__main__":
    print("Testing spell timer...")
    result = fireball("fireball")
    print(f"Result: {result}")

    print("\nTesting MageGuild...")
    print(MageGuild.validate_mage_name("Merlin"))
    print(MageGuild.validate_mage_name("M2"))

    print("\nTesting useless skill")
    print(trash_skill("Meteor"))

    print()
    guild = MageGuild()
    print(guild.cast_spell("Lightning", 15))
    print(guild.cast_spell("Lightning", 1))
