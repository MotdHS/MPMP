# pyright: standard
from pathlib import Path
import heapq
import mmap
from pprint import pprint
import time
from typing import TypedDict

MThd = b"MThd"
MTrk = b"MTrk"

class MIDIData(TypedDict):
    format: int
    tracks: int
    ppq: int
    track_indices: list[tuple[int, int]]

def decode_vlq_single(a):
    return (a >> 7, a & 0b0111_1111)

def decode_vlq(a):
    result = []
    value = 0
    for i in a:
        vlq = decode_vlq_single(i)
        result.append(vlq[1])
        if not vlq[0]:
            break
    for i in result:
        value <<= 7
        value += i
    ret = (value, len(result))
    # print(ret)
    return ret

def get_midi_data(file: Path, verbose=False) -> MIDIData:
    with file.open("rb") as f:
        f.seek(8, 0)
        out: MIDIData = {
            "format": int.from_bytes(f.read(2), byteorder="big"),
            "tracks": int.from_bytes(f.read(2), byteorder="big"),
            "ppq": int.from_bytes(f.read(2), byteorder="big"),
            "track_indices": []
        }
        for i in range(out["tracks"]):
            if f.read(4) == MTrk:
                tracklen = int.from_bytes(f.read(4), byteorder="big")
                out["track_indices"].append((f.tell(), tracklen))
                f.seek(tracklen, 1)
                if verbose:
                    print(f"Added Track {i+1} - {tracklen:,} bytes long")
            else:
                if verbose:
                    raise ValueError(f"Invalid MIDI file structure (probably) (Index: {f.tell():,})")
        return out

def parse_track(m_file: mmap.mmap, track_index: tuple[int, int], track_num: int, verbose=False):
    chunk = memoryview(m_file)[track_index[0] : track_index[0] + track_index[1]]
    ci = 0
    previous_event_type = 0
    current_time = 0
    while ci < len(chunk):
        delta_time = decode_vlq(chunk[ci:ci+4])
        current_time += delta_time[0]
        ci += delta_time[1]
        event_type = chunk[ci]
        if event_type < 0x80:
            event_type = previous_event_type
        else:
            ci += 1

        # print(event_type)

        if event_type == 0xff: # meta event
            meta_type = chunk[ci]
            ci += 1
            length = decode_vlq(chunk[ci:ci+4])
            ci += length[1]
            if meta_type == 0x51: # tempo event
                tempo_us = 0
                for i in chunk[ci:ci+3]:
                    tempo_us <<= 8
                    tempo_us += i
                tempo = 60_000_000.0/float(tempo_us)
                yield (track_num, current_time, "tempo", tempo, None)
                ci += length[0]
            else:
                ci += length[0]
        elif event_type in range(0xf0, 0xf8): # sysex messages, unnecessary for now
            length = decode_vlq(chunk[ci:ci+4])
            ci += length[1] + length[0]

        elif event_type >> 4 in [0x8, 0x9, 0xa, 0xb, 0xe]: # note off/on, polyphonic pressure, controller, and pitch bend events
            yield (track_num, current_time, event_type, chunk[ci], chunk[ci+1])
            ci += 2

        elif event_type >> 4 in [0xc, 0xd]: # program change/channel pressure event
            yield (track_num, current_time, event_type, chunk[ci], None)
            ci += 1

        previous_event_type = event_type

def midi_stream(file: Path, verbose=False):
    if verbose:
        print(f"Initializing MIDI stream: {file}")
    midi_data: MIDIData = get_midi_data(file, verbose)
    with file.open("rb") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
            track_generators = []
            for i, track_index in enumerate(midi_data["track_indices"]):
                track_generators.append(parse_track(m, track_index, i, verbose))
            merged_stream = heapq.merge(*track_generators, key=lambda event: event[1])
            for event in merged_stream:
                yield event

if __name__ == "__main__":
    stream = midi_stream(Path(r"D:\MIDIs\Toilet_Story_3_-_700_TRACK_VERSION\Toilet Story 3 - 700 TRACK VERSION!!!.mid"), verbose=True)
    while (event := next(stream, None)) is not None:
        pass
    print("Doen")