class BaseAggregator:
    def poll(self) -> list[str]:
        raise NotImplementedError("Subclasses must implement this method")
