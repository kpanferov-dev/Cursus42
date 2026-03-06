"""
decorator_mastery.py
Playing with decorators
"""

import time
import functools


# ── 1. spell_timer ──────────────────────────────────────────────────────────

def spell_timer(func: callable) -> callable:
    """Decorator that measures and prints the execution time of a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Casting {func.__name__}...")
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"Spell completed in {elapsed:.3f} seconds")
        return result
    return wrapper


# ── 2. power_validator ──────────────────────────────────────────────────────

def power_validator(min_power: int) -> callable:
    """Decorator factory that validates the first positional argument (power)."""
    def decorator(func: callable) -> callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # For instance methods the first arg is `self`, second is power;
            # for plain functions the first arg is power.
            # We inspect whether the first arg looks like `self` by checking
            # whether the second positional arg (if it exists) is an int.
            if len(args) >= 2 and isinstance(args[1], int):
                power = args[1]          # instance method: (self, spell_name, power)
            elif len(args) >= 1 and isinstance(args[0], int):
                power = args[0]          # plain function: (power, ...)
            else:
                # Fall back to a keyword argument named 'power'
                power = kwargs.get('power', min_power)

            if power >= min_power:
                return func(*args, **kwargs)
            return "Insufficient power for this spell"
        return wrapper
    return decorator


# ── 3. retry_spell ──────────────────────────────────────────────────────────

def retry_spell(max_attempts: int) -> callable:
    """Decorator factory that retries a function up to max_attempts times."""
    def decorator(func: callable) -> callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    print(f"Spell failed, retrying... (attempt {attempt}/{max_attempts})")
            return f"Spell casting failed after {max_attempts} attempts"
        return wrapper
    return decorator


# ── 4. MageGuild ─────────────────────────────────────────────────────────────

class MageGuild:
    """Guild of mages demonstrating @staticmethod and decorated instance methods."""

    @staticmethod
    def validate_mage_name(name: str) -> bool:
        """Return True if name is >= 3 chars and contains only letters/spaces."""
        return len(name) >= 3 and all(ch.isalpha() or ch.isspace() for ch in name)

    @power_validator(min_power=10)
    def cast_spell(self, spell_name: str, power: int) -> str:
        """Cast a spell if power is sufficient."""
        return f"Successfully cast {spell_name} with {power} power"


# ── Demo ─────────────────────────────────────────────────────────────────────

@spell_timer
def fireball(name: str) -> str:
    time.sleep(0.1)          # simulate spell casting time
    return f"{name} cast!"


if __name__ == "__main__":
    # Test spell_timer
    print("Testing spell timer...")
    result = fireball("fireball")
    print(f"Result: {result}")

    # Test MageGuild
    print("\nTesting MageGuild...")
    print(MageGuild.validate_mage_name("Merlin"))   # True
    print(MageGuild.validate_mage_name("M2"))       # False

    guild = MageGuild()
    print(guild.cast_spell("Lightning", 15))        # Success
    print(guild.cast_spell("Lightning", 5))         # Insufficient power