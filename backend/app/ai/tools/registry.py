from collections.abc import Callable

_TOOLS: dict[str, Callable] = {}


def register_tool(name: str):
    def decorator(fn: Callable) -> Callable:
        _TOOLS[name] = fn
        return fn

    return decorator


def get_tool(name: str) -> Callable:
    if name not in _TOOLS:
        raise KeyError(f"Tool '{name}' is not registered")
    return _TOOLS[name]


def list_tools() -> list[str]:
    return sorted(_TOOLS.keys())
