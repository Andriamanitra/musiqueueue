import vlc

from abc import abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from library import Track
from events import EventQueue, PlaybackEnded


@dataclass
class PlayerState:
    playing: bool
    position: timedelta
    track: Track | None

    @property
    def duration(self) -> timedelta:
        return self.track.duration if self.track and self.track.duration else timedelta()


class Playback(Protocol):
    @abstractmethod
    def connect_events(self, event_sink: EventQueue) -> None:
        raise NotImplementedError

    @abstractmethod
    def play(self, track: Track) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def pause(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def resume(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def seek(self, position: timedelta) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_volume(self, volume: float) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_state(self) -> PlayerState:
        raise NotImplementedError


class VLCPlayback:
    def __init__(self) -> None:
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.current_track: Track | None = None
        self.event_manager = self.player.event_manager()

    def connect_events(self, event_sink: EventQueue) -> None:
        self.event_manager.event_attach(
            vlc.EventType.MediaPlayerEndReached,
            lambda _ev: event_sink.put(PlaybackEnded()),
        )

    def play(self, track: Track) -> None:
        media = self.instance.media_new(str(track.path))
        self.current_track = track
        self.player.set_media(media)
        self.player.play()

    def stop(self) -> None:
        self.current_track = None
        self.player.stop()

    def pause(self) -> None:
        self.player.pause()

    def resume(self) -> None:
        self.player.set_pause(0)

    def seek(self, position: timedelta) -> None:
        self.player.set_time(int(position.total_seconds() * 1000))

    def set_volume(self, volume: float) -> None:
        self.player.audio_set_volume(round(volume * 100))

    def get_state(self) -> PlayerState:
        position_ms = self.player.get_time()
        return PlayerState(
            playing=self.player.is_playing(),
            position=timedelta(milliseconds=max(position_ms, 0)),
            track=self.current_track,
        )
