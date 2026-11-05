from dataclasses import dataclass
from itertools import count

from library import Track


@dataclass
class QueueEntry:
    id: int
    track: Track
    played: bool = False


class QueueManager:
    def __init__(self) -> None:
        self.entries: list[QueueEntry] = []
        self.current: QueueEntry | None = None
        self._ids = count()

    def append(self, track: Track) -> QueueEntry:
        entry = QueueEntry(next(self._ids), track)
        self.entries.append(entry)
        return entry

    def insert_next(self, track: Track) -> QueueEntry:
        return self.insert(self._current_index() + 1, track)

    def insert(self, index: int, track: Track) -> QueueEntry:
        entry = QueueEntry(next(self._ids), track)
        self.entries.insert(index, entry)
        return entry

    def remove(self, *entries: int) -> None:
        removed_entries = set(entries)
        self.entries = [
            entry for entry in self.entries
            if entry.id == self.current.id or entry.id not in removed_entries
        ]

    def move(self, entry_ids: set[int], index: int) -> None:
        moving = [e for e in self.entries if e.id in entry_ids]
        if not moving:
            return
        old_indices = [i for i, e in enumerate(self.entries) if e.id in entry_ids]
        index -= sum(i < index for i in old_indices)
        self.entries = [e for e in self.entries if e.id not in entry_ids]
        self.entries[index:index] = moving

    def next(self) -> QueueEntry | None:
        if self.current:
            self.current.played = True

        next_index = self._current_index() + 1
        if 0 <= next_index < len(self.entries):
            self.current = self.entries[next_index]
        else:
            self.current = None
        return self.current

    def mark_played(self, entry: QueueEntry) -> None:
        entry.played = True
        if self.current == entry:
            self.current = None

    def _current_index(self) -> int:
        if self.current is None:
            return -1
        return self.entries.index(self.current)
