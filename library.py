import mutagen

import sys
from dataclasses import dataclass
from pathlib import Path
from datetime import timedelta
from collections.abc import Generator


@dataclass(frozen=True)
class Track:
    path: Path
    title: str | None
    artist: str | None
    duration: timedelta | None


def read_track(path: Path) -> Track | None:
    audio_file = mutagen.File(path, easy=True)
    if audio_file is None:
        return None

    def get_tag(tag: str) -> str | None:
        values = audio_file.get(tag)
        if not values:
            return None
        return str(values[0])

    duration = None
    if audio_file.info:
        duration = timedelta(seconds=audio_file.info.length)
    return Track(
        path=path,
        title=get_tag("title") or path.stem,
        artist=get_tag("artist"),
        duration=duration,
    )


class MusicLibrary:
    def __init__(self, directory: Path):
        self.directory = directory

    def scan(self) -> Generator[Track]:
        extensions = {".mp3", ".flac", ".ogg", ".opus", ".wav", ".m4a"}

        for path in self.directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in extensions:
                track = read_track(path)
                if track is None:
                    print(f"Unrecognized file: {path}", file=sys.stderr)
                else:
                    yield track


if __name__ == "__main__":
    library_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    tracks = MusicLibrary(library_path).scan()
    for track in tracks:
        print(track)
