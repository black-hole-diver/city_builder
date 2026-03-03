class EventBus:
    _subscribers = {}

    @classmethod
    def subscribe(cls, event_type, callback):
        """Registers a function to listen for a specific event."""
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        cls._subscribers[event_type].append(callback)

    @classmethod
    def publish(cls, event_type, *args, **kwargs):
        """Broadcasts an event, triggering all registered callbacks."""
        if event_type in cls._subscribers:
            for callback in cls._subscribers[event_type]:
                callback(*args, **kwargs)
