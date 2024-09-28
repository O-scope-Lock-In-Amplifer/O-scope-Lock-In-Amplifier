"""Turn your oscilloscope into a lock in amplifier with this one simple trick!."""

import numpy as np  # type: ignore

from ds1054z import DS1054z

scope_types = [
    DS1054z,
]
