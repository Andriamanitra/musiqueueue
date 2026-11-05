# musiqueueue

musiqueueueueue is a music player GUI tailored unapologetically to *my* personal preferences.


## Why?

I have tried numerous audio players and I haven't been happy with any of them.

* I want something that is lightweight (doesn't require Electron or web view).
* I want the playback queue to:
    * always be visible
    * keep songs that you've already played this session unless you explicitly remove them
    * be able to hold the same song multiple times
    * be easy to reorder
* I want to be able to make the player very compact simply by resizing so I can make it play nice with a window-stacking compositor.
* I want to experiment with tiny little UX features to make the application pleasant to use.
* I want the user interface to be brutally minimal. No fancy themes and icons.
* I want to have the exact set of features I use and nothing more. I don't care about visualizations or organizing music by album/genre.
* I want [last.fm](https://www.last.fm/) scrobbling to work properly:
    * The player should send "Now Playing" requests, not just scrobbles.
    * Scrobbles should only happen after a song has been played from beginning to end, not halfway through or when you reach the end after having skipped 90% of the song.

## How?

* Python because it allows me to experiment with the interface quickly (no compile times to worry about).
* [tkinter](https://docs.python.org/3/library/tkinter.html) for the GUI. I think it looks great out of the box (especially compared to GTK/Qt) and I have always enjoyed working with it.
* VLC (through [python-vlc](https://github.com/oaubert/python-vlc) bindings) for actually playing music. I am mostly interested in the user interface rather than playback so I just picked the first thing that seemed easy, might switch it eventually.
* [mutagen](https://mutagen.readthedocs.io) for dealing with metadata.
