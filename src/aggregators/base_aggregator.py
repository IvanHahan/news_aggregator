from typing import Any


class BaseAggregator:
    def poll(self, *args, **kwargs) -> list[Any]:
        raise NotImplementedError("Subclasses must implement this method")
