from collections.abc import Iterator
from dataclasses import dataclass
from library import Track
from queue import Queue, Empty


@dataclass(frozen=True, slots=True)
class PlaybackEnded:
    pass


@dataclass(frozen=True, slots=True)
class TrackLoaded:
    track: Track


type Event = PlaybackEnded | TrackLoaded


class EventQueue:
    def __init__(self) -> None:
        self.q: Queue[Event] = Queue()

    def put(self, event: Event) -> None:
        self.q.put(event)

    def get_nowait(self) -> Event:
        return self.q.get_nowait()

    def __iter__(self) -> Iterator[Event]:
        try:
            while True:
                event = self.get_nowait()
                yield event
        except Empty:
            return
