import abc
import functools
from typing import Callable, Dict, TypeVar


class Freezable(abc.ABC):
    @property
    @abc.abstractmethod
    def frozen(self) -> bool:
        pass


T = TypeVar("T")
T_Freezable = TypeVar("T_Freezable", bound=Freezable)


def cache_on_frozen(func: Callable[[T_Freezable], T]) -> Callable[[T_Freezable], T]:
    """
    Decorate `func` such that if `self.frozen` is True,
    cache the property's value under the instance.
    `func` must be a method of a Freezable class.

    References:
    - https://stackoverflow.com/q/64882468/4651668
    """
    fname = func.__name__

    @functools.wraps(func)
    def wrapped(self: T_Freezable) -> T:
        if not self.frozen:
            return func(self)
        try:
            method_cache: Dict[str, T] = getattr(self, "__method_cache")
        except AttributeError:
            method_cache: Dict[str, T] = {}  # type: ignore [no-redef]
            setattr(self, "__method_cache", method_cache)
        if fname not in method_cache:
            method_cache[fname] = func(self)
        return method_cache[fname]

    # It would be convenient to `return property(wrapped)`.
    # But mypy looses track of the return type.
    # https://github.com/python/mypy/issues/8083
    return wrapped
