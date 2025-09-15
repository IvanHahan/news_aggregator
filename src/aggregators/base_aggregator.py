class BaseAggregator:
    def poll(self, *args, **kwargs) -> list[str]:
        raise NotImplementedError("Subclasses must implement this method")
