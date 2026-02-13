"""
basic.py: basic alchemy
"""


from alchemy.elements import create_fire, create_earth


def lead_to_gold():
    """Lead to gold"""
    return f"Lead transmuted to gold using {create_fire()}"


def stone_to_gem():
    """Transmute a stone into gem"""
    return f"Stone transmuted to gem using {create_earth()}"
