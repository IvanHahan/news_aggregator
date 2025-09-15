class BasePublisher:
    def publish(self, items: list[str]) -> None:
        raise NotImplementedError("Subclasses must implement this method")
