# MotdHS's Python MIDI Player Rewritten
A MIDI player written in Python using raylib for graphics, because I am bored.

## Features
- Streaming MIDI data from disk
- GPU rendering with raylib
- PFA-like visuals
- Pitch bend visualization
- Info overlay with BPM, NPS, Polyphony, etc.
- Using `mido` with `kdmapi.mido_backend` for audio
- Slowness of Python :D (?)

## How to Run
**NOTE**: This program has only been tested on Windows and it may not work on other platforms, because it uses KDMAPI for audio, which requires OmniMIDI, which only natively supports Windows.
- Install [OmniMIDI](https://github.com/KeppySoftware/OmniMIDI/releases) for audio
- Install [Python](https://www.python.org/downloads/) (tested with Python 3.14)
- Run `pip install -r requirements.txt` in the project folder to install the dependencies
- Run `python player.py` to run the player

## Credits
- raylib: https://github.com/raysan5/raylib
- raylib-python-cffi: https://github.com/electronstudio/raylib-python-cffi
- OmniMIDI: https://github.com/KeppySoftware/OmniMIDI
- KDMAPI wrapper for Python: https://github.com/python-midi/kdmapi
- Mido: https://github.com/mido/mido
- Piano From Above: https://github.com/brian-pantano/PianoFromAbove