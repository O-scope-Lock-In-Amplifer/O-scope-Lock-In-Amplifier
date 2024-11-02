"""Turn your oscilloscope into a lock in amplifier with this one simple trick!"""

from typing import Type

from o_scope_lock_in_amplifier.ds1054z import DS1054z
from o_scope_lock_in_amplifier.oscilloscope_utils import OScope

scope_types: list[Type[OScope]]

try:
    from o_scope_lock_in_amplifier.ps6000e import PS6000E

except ImportError:
    scope_types = [
        DS1054z,
    ]
else:
    scope_types = [
        DS1054z,
        PS6000E,
    ]
