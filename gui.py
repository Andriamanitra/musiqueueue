import tkinter as tk
from tkinter import ttk

from datetime import timedelta
from collections.abc import Callable, Sequence
from typing import Any, Literal, Optional

from playback import Playback, PlayerState
from library import Track
from queue_manager import QueueManager
from events import EventQueue, PlaybackEnded, TrackLoaded


def format_duration(duration: timedelta) -> str:
    seconds = int(duration.total_seconds())
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02}:{seconds:02}"
    return f"{minutes:02}:{seconds:02}"


type Callback[T] = Callable[[T], Optional[Literal["break"]]] | None


class MusicPane(ttk.Frame):
    def __init__(
            self,
            parent: tk.Widget,
            columns: Sequence[tuple[str, int]],
            on_sort: Callback[str] = None
    ) -> None:
        super().__init__(parent, padding=4)
        self.on_sort = on_sort

        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        column_ids = [name.lower() for name, _ in columns]

        self.tree = ttk.Treeview(
            container,
            columns=column_ids,
            show="headings",
            selectmode="extended",
        )
        self.tree.tag_configure("playing", font=("TkDefaultFont", 9, "bold"))

        for name, width in columns:
            def sort_by_column(c: str = name.lower()) -> None:
                if self.on_sort:
                    self.on_sort(c)

            self.tree.heading(
                name.lower(), text=name,
                command=sort_by_column
            )
            self.tree.column(name.lower(), width=width, minwidth=30)

        scrollbar = ttk.Scrollbar(
            container,
            orient=tk.VERTICAL,
            command=self.tree.yview,
        )

        def update_scrollbar(first: str, last: str) -> None:
            scrollbar.set(first, last)
            if float(first) <= 0 and 1 <= float(last):
                scrollbar.grid_remove()
            else:
                scrollbar.grid()

        self.tree.configure(yscrollcommand=update_scrollbar)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

    def get_drop_position(self, y: int) -> tuple[int, int]:
        children = self.tree.get_children()
        row = self.tree.identify_row(y)

        if not row:
            if children:
                bbox = self.tree.bbox(children[0])
                if bbox and y < bbox[1]:
                    return 0, bbox[1]

            return len(children), self.tree.winfo_height() - 2

        bbox = self.tree.bbox(row)
        if not bbox:
            return len(children), self.tree.winfo_height() - 2
        _, row_y, _, row_height = bbox
        after = y >= row_y + row_height / 2

        index = children.index(row) + int(after)
        line_y = row_y + row_height if after else row_y

        return index, line_y


class VolumeControl(tk.Label):
    def __init__(self, parent: tk.Widget, on_change: Callback[float] = None, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)

        self.volume = 100
        self.on_change = on_change
        self.update_label()

        self.bind("<MouseWheel>", self.on_scroll)
        self.bind("<Button-4>", lambda e: self.change_volume(1))
        self.bind("<Button-5>", lambda e: self.change_volume(-1))

    def update_label(self) -> None:
        self.config(text=f"{self.volume}%")

    def change_volume(self, amount: int) -> None:
        self.volume = max(0, min(100, self.volume + amount))
        self.update_label()
        if self.on_change:
            self.on_change(self.volume / 100)

    def on_scroll(self, event: tk.Event) -> None:
        self.change_volume(1 if event.delta > 0 else -1)


class PlaybackControls(ttk.Frame):
    def __init__(self, root: tk.Tk, playback: Playback, queue_manager: QueueManager) -> None:
        super().__init__(root, padding=4)

        self.playback = playback
        self.playing = False
        self.updating_seekbar = False
        self.queue_manager = queue_manager

        buttons = ttk.Frame(self)
        buttons.pack(side=tk.LEFT, padx=4)

        self.play_button = ttk.Button(buttons, text="▶", width=4, command=self.toggle_play)
        self.play_button.pack(side=tk.LEFT)
        ttk.Button(buttons, text="⏭", width=4, command=self.next).pack(side=tk.LEFT)

        self.seekbar = ttk.Scale(
            self,
            from_=0,
            to=1,
            command=self.on_seek,
        )
        self.seekbar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

        self.timestamp = ttk.Label(self, text="00:00 / 00:00")
        self.timestamp.pack(side=tk.LEFT, padx=4)

        ttk.Separator(self, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, pady=4, padx=4)

        self.volume = VolumeControl(self, on_change=self.playback.set_volume, width=5)
        self.volume.pack(side=tk.RIGHT)

    def next(self) -> None:
        entry = self.queue_manager.next()
        if entry is None:
            self.playback.stop()
            self.playing = False
        else:
            self.playback.play(entry.track)
            self.playing = True
        self.play_button.configure(text="⏸" if self.playing else "▶")

    def on_seek(self, value: str) -> None:
        if not self.updating_seekbar:
            self.playback.seek(timedelta(seconds=float(value)))

    def toggle_play(self) -> None:
        if self.playing:
            self.playback.pause()
            self.playing = False
        elif self.queue_manager.current is None:
            self.next()
        else:
            self.playback.resume()
            self.playing = True

        self.play_button.configure(text="⏸" if self.playing else "▶")

    def update_state(self, state: PlayerState) -> None:
        self.playing = state.playing
        self.play_button.configure(text="⏸" if state.playing else "▶")

        duration = state.duration.total_seconds()
        self.updating_seekbar = True
        self.seekbar.configure(to=max(duration, 1))
        self.seekbar.set(state.position.total_seconds())
        self.updating_seekbar = False

        self.timestamp.configure(
            text=f"{format_duration(state.position)} / "
                 f"{format_duration(state.duration)}"
        )


class MusicPlayer:
    def __init__(self, root: tk.Tk, playback: Playback) -> None:
        self.root = root
        self.playback = playback
        self.queue_manager = QueueManager()
        self.tracks: dict[str, Track] = {}
        self.events = EventQueue()
        playback.connect_events(self.events)

        root.title("musiqueueue")
        root.geometry("1000x600")
        root.minsize(400, 35)
        root.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)

        panes = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        panes.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        self.queue = MusicPane(panes, [("Artist", 150), ("Title", 200), ("Time", 50)])
        self.library = MusicPane(panes, [("Artist", 200), ("Title", 250), ("Time", 50)],
                                 on_sort=self.sort_library)

        panes.add(self.queue, weight=3)
        panes.add(self.library, weight=7)

        self.controls = PlaybackControls(root, self.playback, self.queue_manager)
        self.controls.grid(row=1, column=0, sticky="ew")

        self.library.tree.bind("<KeyPress>", self.on_library_key)

        self.dragged_items: tuple[Any, ...] = ()
        self.dragging = False
        self.drag_source: Literal["library"] | Literal["queue"] | None = None
        self.drop_indicator = ttk.Frame(self.queue.tree, height=2, style="Accent.TFrame")

        def _queue_and_play(ev: tk.Event) -> None:
            row_id = self.library.tree.identify_row(ev.y)
            if not row_id:
                return
            track = self.tracks[row_id]
            self.queue_manager.insert_next(track)
            self.controls.next()
            self.refresh_queue()

        def _play_queued_track(ev: tk.Event) -> None:
            row_id = self.queue.tree.identify_row(ev.y)
            if not row_id:
                return
            entry_id = int(row_id.removeprefix("queue-"))
            entry = next(entry for entry in self.queue_manager.entries if entry.id == entry_id)
            self.queue_manager.current = entry
            self.playback.play(entry.track)

        def _remove_selected(event: tk.Event) -> Literal["break"] | None:
            selection = self.queue.tree.selection()
            if not selection:
                return "break"
            self.queue_manager.remove(*{int(iid.removeprefix("queue-")) for iid in selection})
            self.refresh_queue()
            return "break"

        self.library.tree.bind("<Double-1>", _queue_and_play)
        self.queue.tree.bind("<Double-1>", _play_queued_track)
        self.queue.tree.bind("<Delete>", _remove_selected)
        self.queue.tree.bind("<BackSpace>", _remove_selected)
        self.library.tree.bind("<ButtonPress-1>", lambda e: self.start_drag(e, "library"))
        self.queue.tree.bind("<ButtonPress-1>", lambda e: self.start_drag(e, "queue"))

        self.root.bind_all("<B1-Motion>", self.on_drag_motion, add="+")
        self.root.bind_all("<ButtonRelease-1>", self.on_drag_release, add="+")

        self.root.after(50, self.process_events)
        self.root.after(100, self.update_playback_state)

    def update_playback_state(self) -> None:
        state = self.playback.get_state()
        self.controls.update_state(state)

        current = self.queue_manager.current
        current_id = f"queue-{current.id}" if current else None

        tree = self.queue.tree
        for iid in tree.get_children():
            tree.item(iid, tags=("playing",) if iid == current_id else ())

        self.root.after(100, self.update_playback_state)

    def on_library_key(self, event: tk.Event) -> Literal["break"] | None:
        if not event.char.isalnum():
            return None
        tree = self.library.tree
        letter = event.char.casefold()
        column = getattr(self, "_sort_column", None) or "artist"
        for iid in tree.get_children():
            value = getattr(self.tracks[iid], column, "")
            if value.casefold().startswith(letter):
                tree.see(iid)
                tree.selection_set(iid)
                tree.focus(iid)
                return "break"
        return None

    def process_events(self) -> None:
        for event in self.events:
            match event:
                case TrackLoaded(track):
                    self.add_track(track)
                case PlaybackEnded():
                    self.controls.next()
                case other:
                    print(other)

        self.root.after(50, self.process_events)

    def add_track(self, track: Track) -> None:
        t_id = self.library.tree.insert(
            "",
            tk.END,
            values=(
                track.artist or "",
                track.title or track.path.stem,
                format_duration(track.duration) if track.duration else "??:??",
            ),
        )
        self.tracks[t_id] = track

    def start_drag(self, event: tk.Event, source: Literal["library"] | Literal["queue"]) -> None:
        tree = self.library.tree if source == "library" else self.queue.tree
        row = tree.identify_row(event.y)

        self.drag_source = None
        self.dragged_items = ()
        self.dragging = False

        if not row:
            return

        selection = tree.selection()
        if row in selection:
            self.dragged_items = selection
        else:
            self.dragged_items = row,
        self.drag_source = source

    def on_drag_motion(self, event: tk.Event) -> None:
        if not self.drag_source or not self.dragged_items:
            return

        self.dragging = True

        tree = self.queue.tree
        x = event.x_root - tree.winfo_rootx()
        y = event.y_root - tree.winfo_rooty()

        if not (0 <= x < tree.winfo_width() and 0 <= y < tree.winfo_height()):
            self.drop_indicator.place_forget()
            return

        if tree.identify_region(x, y) == "heading":
            self.drop_indicator.place_forget()
            return

        _, line_y = self.queue.get_drop_position(y)

        self.drop_indicator.place(
            x=0,
            y=line_y - 1,
            relwidth=1,
            height=2,
        )

    def on_drag_release(self, event: tk.Event) -> None:
        try:
            if not self.dragging:
                return

            tree = self.queue.tree
            x = event.x_root - tree.winfo_rootx()
            y = event.y_root - tree.winfo_rooty()

            if not (0 <= x < tree.winfo_width() and 0 <= y < tree.winfo_height()):
                return

            if tree.identify_region(x, y) == "heading":
                return

            index, _ = self.queue.get_drop_position(y)

            if self.drag_source == "library":
                for offset, iid in enumerate(self.dragged_items):
                    track = self.tracks.get(iid)
                    if track:
                        self.queue_manager.insert(index + offset, track)

            elif self.drag_source == "queue":
                entry_ids = {
                    int(iid.removeprefix("queue-"))
                    for iid in self.dragged_items
                }
                self.queue_manager.move(entry_ids, index)

            self.refresh_queue()

        finally:
            self.drop_indicator.place_forget()
            self.drag_source = None
            self.dragged_items = ()
            self.dragging = False

    def refresh_queue(self) -> None:
        tree = self.queue.tree
        tree.delete(*tree.get_children())

        for entry in self.queue_manager.entries:
            track = entry.track

            tree.insert(
                "",
                "end",
                iid=f"queue-{entry.id}",
                values=(
                    track.artist or "",
                    track.title,
                    format_duration(track.duration)
                    if track.duration else "",
                ),
            )

    def sort_library(self, column: str) -> None:
        tree = self.library.tree

        reverse = getattr(self, "_sort_reverse", False)
        last_column = getattr(self, "_sort_column", None)

        if last_column == column:
            reverse = not reverse
        else:
            reverse = False

        self._sort_column = column
        self._sort_reverse = reverse

        keys: dict[str, Callable[[Track], Any]] = {
            "artist": lambda t: (t.artist or "").casefold(),
            "title": lambda t: (t.title or t.path.stem).casefold(),
            "time": lambda t: t.duration.total_seconds() if t.duration else -1,
        }

        items = [
            (iid, self.tracks[iid])
            for iid in tree.get_children()
        ]

        items.sort(
            key=lambda item: keys[column](item[1]),
            reverse=reverse,
        )

        for index, (iid, _) in enumerate(items):
            tree.move(iid, "", index)
