import tkinter as tk

import sys
from threading import Thread
from pathlib import Path

from gui import MusicPlayer
from playback import VLCPlayback
from library import MusicLibrary
from events import TrackLoaded


def main(args: list[str]) -> None:
    root = tk.Tk()
    icon = tk.PhotoImage(file="assets/icon.png")
    root.iconphoto(True, icon)
    playback = VLCPlayback()
    app = MusicPlayer(root, playback)

    music_library_path = Path(args[0] if args else Path.home() / "Music")

    def scan_library() -> None:
        musics = MusicLibrary(music_library_path)
        for track in musics.scan():
            app.events.put(TrackLoaded(track))

    Thread(target=scan_library, daemon=True).start()

    root.mainloop()


if __name__ == "__main__":
    main(sys.argv[1:])
