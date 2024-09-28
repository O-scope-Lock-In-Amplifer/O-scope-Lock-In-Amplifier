import abc
import dataclasses
from enum import Enum
from functools import wraps
from typing import TypeVar, Callable, Any, List, Dict, Optional

import numpy as np


class OscilloscopeChannels(Enum):
    CHANNEL_1 = 1
    CHANNEL_2 = 2
    CHANNEL_3 = 3
    CHANNEL_4 = 4


@dataclasses.dataclass(frozen=True)
class AcquisitionData:
    ref_dat: np.ndarray
    time_increment: float
    time_origin: float
    aqu_dat: np.ndarray


class OScope(abc.ABC):
    def __init__(
        self,
        ref_channel: OscilloscopeChannels = OscilloscopeChannels.CHANNEL_1,
        acquisition_channel: OscilloscopeChannels = OscilloscopeChannels.CHANNEL_2,
    ):
        self.ref_channel = ref_channel
        self.acquisition_channel = acquisition_channel

    @abc.abstractmethod
    def get_data(self) -> AcquisitionData:
        pass


T = TypeVar("T", bound=Callable[..., Any])


def allowed_vals(**constraints: List[Any]) -> Callable[[T], T]:
    """
    Decorator to enforce constraints on specific function arguments and store allowed values and types.

    :param constraints: Keyword arguments specifying the allowed values for each argument.
                        E.g., memory_depth=[12000, 120000, 1200000]
    """

    def decorator(func: T) -> T:
        # Extract the names of the function's positional arguments
        arg_names: List[str] = list(
            func.__code__.co_varnames[: func.__code__.co_argcount]
        )

        # Create a dictionary mapping argument names to their allowed values or None
        allowed_values: Dict[str, Optional[List[Any]]] = {
            arg: constraints.get(arg, None) for arg in arg_names
        }

        # Create a dictionary mapping argument names to their types based on allowed values
        argument_types: Dict[str, Optional[type]] = {}
        for arg in arg_names:
            allowed = allowed_values[arg]
            if allowed is not None:
                # Use cast to inform mypy that 'allowed' is indeed a List[Any]
                first_val = allowed[0]
                argument_types[arg] = type(first_val)
            else:
                argument_types[arg] = None

        # Attach the allowed values and argument types to the function for inspection
        setattr(func, "allowed_values", allowed_values)
        setattr(func, "argument_types", argument_types)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Combine positional and keyword arguments into a single dictionary
            provided_args: Dict[str, Any] = dict(zip(arg_names, args))
            provided_args.update(kwargs)

            # Validate each provided argument against its allowed values
            for arg_name, allowed_vals in allowed_values.items():
                if arg_name in provided_args:
                    if (
                        allowed_vals is not None
                        and provided_args[arg_name] not in allowed_vals
                    ):
                        raise ValueError(
                            f"Invalid value for '{arg_name}'. Allowed values are {allowed_vals}."
                        )

            return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator
