# pyright: standard
from pathlib import Path
import time
from typing import TYPE_CHECKING, Any
import mido
import math
import midistream
import pyray as pr
import raylib as rl
from tkinter import filedialog
from collections import deque

VERSION = "v1.0.0"

WIDTH = 1280
HEIGHT = 720
VISUALIZE_PITCH_BENDS = True

DEBUG = False
MAX_DELTA = True
CATCH_UP = True

PFA_COLORS = [
    (51, 102, 255),
    (255, 126, 51),
    (51, 255, 102),
    (255, 51, 129),
    (51, 255, 255),
    (228, 51, 255),
    (153, 255, 51),
    (75, 51, 255),
    (255, 204, 51),
    (51, 180, 255),
    (255, 51, 51),
    (51, 255, 177),
    (255, 51, 204),
    (78, 255, 51),
    (153, 51, 255),
    (231, 255, 51)
]

IS_SHARP: list[bool] = [False, True, False, True, False, False, True, False, True, False, True, False, False, True, False, True, False, False, True, False, True, False, True, False, False, True, False, True, False, False, True, False, True, False, True, False, False, True, False, True, False, False, True, False, True, False, True, False, False, True, False, True, False, False, True, False, True, False, True, False, False, True, False, True, False, False, True, False, True, False, True, False, False, True, False, True, False, False, True, False, True, False, True, False, False, True, False, True, False, False, True, False, True, False, True, False, False, True, False, True, False, False, True, False, True, False, True, False, False, True, False, True, False, False, True, False, True, False, True, False, False, True, False, True, False, False, True, False]

WHITE_NOTE: tuple[bool, tuple[int, int, int, int]] = (False, (255, 255, 255, 255))
BLACK_NOTE: tuple[bool, tuple[int, int, int, int]] = (False, (0, 0, 0, 255))

SHARP_RATIO = 0.65
KB_PERCENT = 0.25
KEY_RATIO = 0.1775

def multiply_color(color: tuple[int, int, int, int], mul):
    tempus = []
    for i in color[0:3]:
        curlor = int(i*mul)
        if curlor > 255:
            curlor = 255
        tempus.append(curlor)
    tempus.append(color[3])
    return tuple(tempus)

def DrawRectangleRecGradientH(rect: tuple[Any, Any, Any, Any], left: tuple[Any, Any, Any, Any], right: tuple[Any, Any, Any, Any]):
    rl.DrawRectangleGradientEx(rect, left, left, right, right)

def DrawRectangleRecGradientV(rect: tuple[Any, Any, Any, Any], top: tuple[Any, Any, Any, Any], bottom: tuple[Any, Any, Any, Any]):
    rl.DrawRectangleGradientEx(rect, top, bottom, bottom, top)

def DrawSkew(p1: tuple[Any, Any], p2: tuple[Any, Any], p3: tuple[Any, Any], p4: tuple[Any, Any], c1: tuple[Any, Any, Any, Any], c2: tuple[Any, Any, Any, Any] | None = None, c3: tuple[Any, Any, Any, Any] | None = None, c4: tuple[Any, Any, Any, Any] | None = None):
    if c2 is None and c3 is None and c4 is None:
        c2 = c3 = c4 = c1
    if c2 is None or c3 is None or c4 is None:
        raise ValueError("idk if this is the correct exception to raise but whatever idfk basically you should either provide one or four color inputs not two or three :D")
    rl.DrawTriangleGradient(p1, p3, p2, c1, c3, c2)
    rl.DrawTriangleGradient(p1, p4, p3, c1, c4, c3)

def align_rectangle(rect: tuple) -> tuple:
    left = math.floor(rect[0] + 0.5)
    top = math.floor(rect[1] + 0.5)
    right = math.floor(rect[0] + rect[2] + 0.5)
    bottom = math.floor(rect[1] + rect[3] + 0.5)
    return (left, top, right - left, bottom - top)

def file_dialog():
    return filedialog.askopenfilename(filetypes=(
        ("MIDI Files", "*.mid"),
        ("Karaoke Files (?)", "*.kar"),
    ))

def main():
    file_path = file_dialog()
    print("Initializing MIDI...")
    load_start = time.perf_counter()
    # midi = mparser.load_midi(file_path, verbose=True)
    a_stream = midistream.midi_stream(Path(file_path), verbose=True)
    v_stream = midistream.midi_stream(Path(file_path), verbose=True)
    # p_stream = midistream.midi_stream(Path(file_path), verbose=True)
    next(a_stream)
    next(v_stream)
    # next(p_stream)
    load_end = time.perf_counter()
    print(f"Took {load_end - load_start:.5f} seconds")
    midi: midistream.MIDIData = midistream.get_midi_data(Path(file_path), verbose=True)

    mido.set_backend("kdmapi.mido_backend")

    ppq = midi["ppq"]
    color_palette: dict[int, tuple[tuple[int, int, int, int], tuple[int, int, int, int], tuple[int, int, int, int]]] = {}

    print("Done!")
    white_key_offsets = []
    current_white_count = 0
    for is_sharp in IS_SHARP:
        white_key_offsets.append(current_white_count)
        if not is_sharp:
            current_white_count += 1

    def get_note_x(n: int):
        white_keys = white_key_offsets[n]
        start_x = (0 - IS_SHARP[n]) * SHARP_RATIO / 2
        if IS_SHARP[n]:
            note = n % 12
            if note in {1, 6}: # C# or F#
                start_x -= SHARP_RATIO / 5
            elif note in {3, 10}: # D# or A#
                start_x += SHARP_RATIO / 5
        return r_notes_x + r_white_cx * (white_keys + start_x)

    def render_note(note: tuple):
        n = note[3]
        t = note[2]
        c = note[1]
        s = note[0]
        d = note[4]
        note_color = color_palette[(t<<8) | (c)]

        # Compute true positions
        x = get_note_x(n)
        if VISUALIZE_PITCH_BENDS:
            x += a_pitch_bend[c] * a_pitch_bend_range[c] * WIDTH/128
        y = r_notes_cy * (midi_time - s - d) / v_notespeed
        cx = (r_white_cx * SHARP_RATIO) if IS_SHARP[n] else r_white_cx
        cy = r_notes_cy * d / v_notespeed
        # deflate = r_white_cx * 0.15 / 2.0

        # deflate = math.floor(deflate + 0.5)
        # deflate = max(min(deflate, 3.0), 1.0)
        deflate = max(min(math.floor((r_white_cx * 0.15 / 2.0) + 0.5), 3.0), 1.0)

        # Clipping :/
        # min_y = r_notes_y - 5.0
        # max_y = r_notes_y + r_notes_cy + 5.0
        # if y > max_y:
        #     cy -= y - max_y
        #     y = max_y
        # if y - cy < min_y:
        #     cy -= min_y - y + cy
        #     y = min_y + cy

        rl.DrawRectangleRec(
            align_rectangle((x, y, cx, max(cy, 1.0))),
            note_color[2]
        )
        DrawRectangleRecGradientH(
            align_rectangle((x + deflate, y + deflate, cx - deflate * 2, cy - deflate * 2)),
            note_color[0], note_color[1]
        )

    prev_time = time.perf_counter()
    with mido.open_output() as out: # type: ignore
        a_current_time = 0

        a_bpm = 120
        a_seconds_per_tick = 60 / (a_bpm * ppq)
        a_last_tick = 0
        a_played_notes = 0
        a_polyphony = 0
        a_finished = False
        a_finished_time = 0
        a_nps_list = deque()
        a_pitch_bend = []
        a_pitch_bend_range = []
        a_rpn = []
        a_reuse_event = False
        # cython
        # for i in range(16):
        #     a_pitch_bend[i] = 0.0
        #     a_pitch_bend_range[i] = 2
        #     a_rpn[i][0] = 0x7f
        #     a_rpn[i][1] = 0x7f
        # python
        for i in range(16):
            a_pitch_bend.append(0.0)
            a_pitch_bend_range.append(2)
            a_rpn.append([0x7f, 0x7f])

        v_bpm = 120
        v_seconds_per_tick = 60 / (v_bpm * ppq)
        v_last_tick = 0
        v_notespeed = 0.15
        v_current_time = - v_notespeed
        midi_time = -2
        real_time = -2
        behind = False
        min_delta = 0

        v_rendered = 0
        v_reuse_event = False
        current_color_index = 0

        v_notes = {}            # Only stores ACTIVE notes
        v_falling_notes = deque() # Stores FINISHED notes (rendering only)

        cs_background = (0x46, 0x46, 0x46, 255)
        cs_background_dark = multiply_color(cs_background, 0.7)
        cs_background_verydark = multiply_color(cs_background, 1.3)

        cs_kb_background = (0x99, 0x99, 0x99, 255)
        cs_kb_background_dark = multiply_color(cs_kb_background, 0.4)
        cs_kb_background_verydark = multiply_color(cs_kb_background, 0)

        cs_kb_red = (0x98, 0x0a, 0x0d, 255)
        cs_kb_red_dark = multiply_color(cs_kb_red, 0.5)
        cs_kb_red_verydark = multiply_color(cs_kb_red, 0.2)

        cs_kb_white = (255, 255, 255, 255)
        cs_kb_white_dark = multiply_color(cs_kb_white, 0.8)
        cs_kb_white_verydark = multiply_color(cs_kb_white, 0.6)

        cs_kb_sharp = (0x40, 0x40, 0x40, 255)
        cs_kb_sharp_dark = multiply_color(cs_kb_sharp, 0.5)
        cs_kb_sharp_verydark = multiply_color(cs_kb_sharp, 0)

        skipping = False
        paused = True

        seekback_pending = False
        seekback_amount = 0


        pr.init_window(WIDTH, HEIGHT, f"MotdHS's Python MIDI Player {VERSION}")
        # pr.set_target_fps(165)

        while not pr.window_should_close() and not pr.is_key_pressed(pr.KeyboardKey.KEY_Q):
            if pr.is_key_pressed(pr.KeyboardKey.KEY_RIGHT) or pr.is_key_pressed_repeat(pr.KeyboardKey.KEY_RIGHT):
                if seekback_pending:
                    seekback_amount += 2
                    if not seekback_amount:
                        seekback_pending = False
                else:
                    midi_time += 2
                    real_time = midi_time
                    behind = False
                    skipping = True
            if pr.is_key_pressed(pr.KeyboardKey.KEY_LEFT) or pr.is_key_pressed_repeat(pr.KeyboardKey.KEY_LEFT):
                seekback_amount -= 2
                if not seekback_pending:
                    seekback_pending = True
                    for channel in range(16):
                        out.send(mido.Message.from_bytes([0xB0 + channel, 123, 0]))
            if pr.is_key_pressed(pr.KeyboardKey.KEY_HOME) or pr.is_key_pressed(pr.KeyboardKey.KEY_PERIOD):
                skipping = True
                paused = True
                behind = False
                midi_time = real_time = -2
                a_stream = midistream.midi_stream(Path(file_path), verbose=True)
                v_stream = midistream.midi_stream(Path(file_path), verbose=True)
                # p_stream = midistream.midi_stream(Path(file_path), verbose=True)
                next(a_stream)
                next(v_stream)
                # next(p_stream)
                a_current_time = 0

                a_bpm = 120
                a_seconds_per_tick = 60 / (a_bpm * ppq)
                a_last_tick = 0
                a_played_notes = 0
                a_polyphony = 0
                a_finished = False
                a_finished_time = 0
                a_nps_list = deque()
                a_pitch_bend = []
                a_pitch_bend_range = []
                a_rpn = []
                a_reuse_event = False
                for i in range(16):
                    a_pitch_bend.append(0.0)
                    a_pitch_bend_range.append(2)
                    a_rpn.append([0x7f, 0x7f])

                v_bpm = 120
                v_seconds_per_tick = 60 / (v_bpm * ppq)
                v_last_tick = 0
                v_current_time = - v_notespeed

                v_rendered = 0
                v_reuse_event = False
                current_color_index = 0

                v_notes = {}            # Only stores ACTIVE notes
                v_falling_notes = deque() # Stores FINISHED notes (rendering only)

            if pr.is_key_pressed(pr.KeyboardKey.KEY_ENTER) and seekback_pending:
                seekback_pending = False
                skipping = True
                paused = True
                behind = False
                midi_time += seekback_amount
                real_time = midi_time
                seekback_amount = 0
                a_stream = midistream.midi_stream(Path(file_path), verbose=True)
                v_stream = midistream.midi_stream(Path(file_path), verbose=True)
                # p_stream = midistream.midi_stream(Path(file_path), verbose=True)
                next(a_stream)
                next(v_stream)
                # next(p_stream)
                a_current_time = 0

                a_bpm = 120
                a_seconds_per_tick = 60 / (a_bpm * ppq)
                a_last_tick = 0
                a_played_notes = 0
                a_polyphony = 0
                a_finished = False
                a_finished_time = 0
                a_nps_list = deque()
                a_pitch_bend = []
                a_pitch_bend_range = []
                a_rpn = []
                a_reuse_event = False
                for i in range(16):
                    a_pitch_bend.append(0.0)
                    a_pitch_bend_range.append(2)
                    a_rpn.append([0x7f, 0x7f])

                v_bpm = 120
                v_seconds_per_tick = 60 / (v_bpm * ppq)
                v_last_tick = 0
                v_current_time = - v_notespeed

                v_rendered = 0
                v_reuse_event = False
                current_color_index = 0

                v_notes = {}            # Only stores ACTIVE notes
                v_falling_notes = deque() # Stores FINISHED notes (rendering only)

            if pr.is_key_pressed(pr.KeyboardKey.KEY_END):
                midi_time += 12345678
                real_time += 12345678
            if pr.is_key_pressed(pr.KeyboardKey.KEY_SPACE):
                if paused:
                    paused = False
                else:
                    paused = True
                    for channel in range(16):
                        out.send(mido.Message.from_bytes([0xB0 + channel, 123, 0]))

            # if paused:
            #     v_paused_time = time.perf_counter() - v_paused_start
            # else:
            #     if v_paused_time:
            #         start_time += v_paused_time
            #         v_paused_time = 0
            #     midi_time = time.perf_counter() - start_time

            if real_time + v_notespeed >= midi_time >= real_time - v_notespeed:
                behind = False
                midi_time = real_time
                min_delta = 0
            else:
                min_delta = min(real_time - midi_time, v_notespeed) if CATCH_UP else 0

            delta_meow = delta_sec = time.perf_counter() - prev_time
            if MAX_DELTA:
                delta_meow = min(delta_meow, v_notespeed)
            if min_delta:
                delta_meow = max(delta_meow, min_delta)
            if delta_meow != delta_sec and not (paused or skipping):
                behind = True

            if not (paused or skipping or seekback_pending):
                midi_time += delta_meow
                real_time += delta_sec
            prev_time = time.perf_counter()

            if skipping:
                for channel in range(16):
                    out.send(mido.Message.from_bytes([0xB0 + channel, 123, 0]))
            if TYPE_CHECKING:
                event = (0, 0, 0, 0, 0)
            audio_start = time.perf_counter()
            while not (paused or seekback_pending) or skipping: # AUDIO LOOP
                # Before checking, decide if we need to fetch a new event or reuse the old one
                if not a_reuse_event:
                    event = next(a_stream, None)
                else:
                    a_reuse_event = False  # Reset the flag since we just reused it

                if event is None:
                    a_finished = True
                    break

                a_delta_tick = event[1] - a_last_tick
                a_current_time_temp = a_current_time + (a_delta_tick * a_seconds_per_tick)
                if a_current_time_temp > midi_time:
                    a_reuse_event = True
                    break
                a_current_time = a_current_time_temp

                if event[2] == "tempo":
                    a_bpm = event[3]
                    # print(a_bpm)
                    a_seconds_per_tick = 60 / (a_bpm * ppq)

                if event[2] != "tempo":
                    if event[2] >> 4 == 0x9:
                        if event[4] != 0:
                            a_played_notes += 1
                            a_polyphony += 1
                            a_nps_list.append(midi_time + 1)
                            color_key = (event[0] << 8) | (event[2] & 0b1111)
                            if color_key not in color_palette:
                                fill_rgb = PFA_COLORS[current_color_index % 16]
                                color_palette[color_key] = (
                                    (fill_rgb[0], fill_rgb[1], fill_rgb[2], 255),
                                    (int(fill_rgb[0]/2), int(fill_rgb[1]/2), int(fill_rgb[2]/2), 255),
                                    (int(fill_rgb[0]/5), int(fill_rgb[1]/5), int(fill_rgb[2]/5), 255),
                                )
                                current_color_index += 1
                    if event[2] >> 4 in [0x8, 0x9]:
                        if event[2] >> 4 == 0x8 or event[4] == 0:
                            a_polyphony -= 1
                            color_key = (event[0] << 8) | (event[2] & 0b1111)
                    if event[2] >> 4 == 0xb: #controller, here i'll only use it for pitch bend range
                        if event[3] == 0x64:
                            a_rpn[event[2] & 0b1111][0] = event[4]
                        elif event[3] == 0x65:
                            a_rpn[event[2] & 0b1111][1] = event[4]
                        elif event[3] == 0x06:
                            if a_rpn[event[2] & 0b1111][0] == 0 and a_rpn[event[2] & 0b1111][1] == 0:
                                a_pitch_bend_range[event[2] & 0b1111] = event[4]
                    if event[2] >> 4 == 0xe: #pitch bend
                        a_pitch_bend[event[2] & 0b1111] = (event[3] + (event[4] << 7) - 8192) / 8192

                    if (not skipping or event[2] >> 4 not in [0x8, 0x9]) and event is not None:
                        # print(event)
                        out.send(mido.Message.from_bytes(event[2:]))
                a_last_tick = event[1]
            audio_dur = time.perf_counter() - audio_start


            pop_start = time.perf_counter()
            try:
                while a_nps_list[0] <= midi_time:
                    a_nps_list.popleft()
            except IndexError:
                pass
            if skipping:
                skipping = False
            pop_dur = time.perf_counter() - pop_start

            rl.BeginDrawing()
            rl.ClearBackground(cs_background)

            if TYPE_CHECKING:
                ev = (0, 0, 0, 0, 0)
            # --- 1. PROCESS EVENTS ---
            pv_start = time.perf_counter()
            while True:
                # Before checking, decide if we need to fetch a new event or reuse the old one
                if not v_reuse_event:
                    ev = next(v_stream, None)
                else:
                    v_reuse_event = False  # Reset the flag since we just reused it

                if ev is None:
                    break

                v_delta_tick = ev[1] - v_last_tick
                v_current_time_temp = v_current_time + (v_delta_tick * v_seconds_per_tick)
                if v_current_time_temp > midi_time:
                    v_reuse_event = True
                    break
                v_current_time = v_current_time_temp

                if ev[2] == "tempo":
                    v_bpm = ev[3]
                    v_seconds_per_tick = 60 / (v_bpm * ppq)

                if ev[2] != "tempo" and ev[2] >> 4 in (0x8, 0x9):
                    tr = ev[0]
                    ch = ev[2] & 0b1111
                    no = ev[3]
                    note_key = (tr << 16) | (ch << 8) | no

                    # NOTE ON
                    if ev[2] >> 4 == 0x9 and ev[4] != 0:
                        if note_key not in v_notes:
                            v_notes[note_key] = deque()
                        v_notes[note_key].append((v_current_time, ev[4]))
                        color_key = (tr << 8) | ch
                        if color_key not in color_palette:
                            fill_rgb = PFA_COLORS[current_color_index % 16]
                            color_palette[color_key] = (
                                (fill_rgb[0], fill_rgb[1], fill_rgb[2], 255),
                                (int(fill_rgb[0]/2), int(fill_rgb[1]/2), int(fill_rgb[2]/2), 255),
                                (int(fill_rgb[0]/5), int(fill_rgb[1]/5), int(fill_rgb[2]/5), 255),
                            )
                            current_color_index += 1

                    # NOTE OFF
                    else:
                        if note_key in v_notes and v_notes[note_key]:
                            start_t, _ = v_notes[note_key].popleft()
                            duration = v_current_time - start_t
                            if not v_notes[note_key]:
                                del v_notes[note_key]

                            if v_current_time >= midi_time - v_notespeed:
                                v_falling_notes.append((start_t, ch, tr, no, duration))

                v_last_tick = ev[1]
            pv_dur = time.perf_counter() - pv_start

            # --- 2. CLEANUP OLD NOTES (Optimization) ---
            # efficiently remove notes that have scrolled off the bottom
            # Condition: start + duration < v_time - v_notespeed
            clean_start = time.perf_counter()
            while v_falling_notes:
                note = v_falling_notes[0]
                if note[0] + note[4] < midi_time - v_notespeed:
                    v_falling_notes.popleft()
                else:
                    break
            clean_dur = time.perf_counter() - clean_start

            # --- 3. DRAW ALL NOTES (Unified) ---
            sort_start = time.perf_counter()
            render_queue = []

            render_queue.extend(v_falling_notes)

            for note_key, note_list in v_notes.items():
                tr = note_key >> 16
                ch = (note_key >> 8) & 0xFF
                no = note_key & 0xFF
                for start, _ in note_list:
                    duration = midi_time - start
                    render_queue.append((start, ch, tr, no, duration))

            render_queue.sort()
            sort_dur = time.perf_counter() - sort_start


            v_rendered = 0
            ren_start = time.perf_counter()
            """
            for start, ch, tr, no, duration in render_queue:
                x_pos = (no + a_pitch_bend[ch]*a_pitch_bend_range[ch]) * scale_x
                y_pos = scale_y * (midi_time - start - duration)
                height = max(1, scale_y * duration)

                fill_color, outline_color = color_palette[(tr << 8) | ch]

                rl.DrawRectangleRec(
                    align_rectangle((
                        x_pos,
                        y_pos,
                        scale_x,
                        height
                    )),
                    fill_color
                )
                # pr.draw_rectangle_gradient_h(
                #     int(evi[2] * scale_x),
                #     int(y_pos),
                #     10,
                #     int(max(1, height)),
                #     pr.Color(*note_color, 255),
                #     pr.Color(*(int(x/1.75) for x in note_color), 255),
                # )
                rl.DrawRectangleLinesEx(
                    align_rectangle((
                        x_pos,
                        y_pos,
                        scale_x,
                        height
                    )),
                    1,
                    outline_color
                )
                v_rendered += 1

            for key in range(128):
                rl.DrawRectangleRec(
                    align_rectangle((
                        scale_x * key,
                        HEIGHT - v_keyboard_height,
                        scale_x,
                        v_keyboard_height
                    )),
                    key_colors[key][1]
                )
            """

            # replicating PFA's rendering :D




            # Screen X info
            r_notes_x = 0
            r_notes_cx = WIDTH

            # Keys info
            r_all_white_keys = IS_SHARP.count(False)
            r_buffer = ((SHARP_RATIO / 2.0) if IS_SHARP[0] else 0.0) + ((SHARP_RATIO / 2.0) if IS_SHARP[127] else 0.0)
            r_white_cx = r_notes_cx / (r_all_white_keys + r_buffer)

            # Screen Y info
            r_notes_y = 0
            r_max_key_cy = HEIGHT * KB_PERCENT
            r_ideal_key_cy = r_white_cx / KEY_RATIO
            # .95 for the top vs near. 2.0 for the spacer. .93 for the transition and the red. ESTIMATE.
            r_ideal_key_cy = (r_ideal_key_cy / 0.95 + 2) / 0.93
            r_notes_cy = math.floor(HEIGHT - min(r_ideal_key_cy, r_max_key_cy) + 0.5)

            # Round down start time. This is only used for rendering purposes
            # nvm i can probably skip this (?)

            if "RenderLines()":
                # Vertical lines
                for i in range(1, 128):
                    if not IS_SHARP[i-1] and not IS_SHARP[i]:
                        r_white_keys = IS_SHARP[0:i].count(False)
                        r_start_x = IS_SHARP[0] * SHARP_RATIO / 2
                        r_x = math.floor((r_notes_x + r_white_cx * (r_white_keys + r_start_x)) + 0.5)
                        DrawRectangleRecGradientH(
                            align_rectangle((r_x - 1, r_notes_y, 3, r_notes_cy)),
                            cs_background_dark, cs_background_verydark
                        )

                # Horizontal (Hard!)
                # hell nah i ain't doing it

            key_colors = [(BLACK_NOTE if IS_SHARP[x] else WHITE_NOTE) for x in range(128)]
            if "RenderNotes()": # render_queue: list of (start, ch, tr, no, duration)
                # i'll optimize this later idk :D

                # Do we have any notes to render?
                # I am not sure!

                # Render notes. Regular notes then sharps to  make sure they're not hidden
                r_has_sharp = False
                for note in render_queue:
                    if not IS_SHARP[note[3]]:
                        render_note(note)
                        v_rendered += 1
                    else:
                        r_has_sharp = True
                    if note[0] + v_notespeed <= midi_time:
                        color_key = (note[2] << 8) | (note[1] & 0b1111)
                        key_colors[note[3]] = (True, color_palette[color_key][0])

                if r_has_sharp:
                    for note in render_queue:
                        if IS_SHARP[note[3]]:
                            render_note(note)
                            v_rendered += 1
                        else:
                            r_has_sharp = True





            if "RenderKeys()":
                r_keys_y = r_notes_y + r_notes_cy
                r_keys_cy = HEIGHT - r_notes_cy

                r_transition_pct = .02
                r_transition_cy = max(3.0, math.floor(r_keys_cy * r_transition_pct + 0.5))
                r_red_pct = .05
                r_red_cy = math.floor(r_keys_cy * r_red_pct + 0.5)
                r_spacer_cy = 2.0
                r_top_cy = math.floor((r_keys_cy - r_spacer_cy - r_red_cy - r_transition_cy) * 0.95 + 0.5)
                r_near_cy = r_keys_cy - r_spacer_cy - r_red_cy - r_transition_cy - r_top_cy

                # Draw the background
                rl.DrawRectangleRec(
                    align_rectangle((r_notes_x, r_keys_y, r_notes_cx, r_keys_cy)),
                    cs_kb_background_verydark
                )
                DrawRectangleRecGradientV(
                    align_rectangle((r_notes_x, r_keys_y, r_notes_cx, r_transition_cy)),
                    cs_background, cs_kb_background_verydark
                )
                DrawRectangleRecGradientV(
                    align_rectangle((r_notes_x, r_keys_y + r_transition_cy, r_notes_cx, r_red_cy)),
                    cs_kb_red_dark, cs_kb_red
                )
                rl.DrawRectangleRec(
                    align_rectangle((r_notes_x, r_keys_y + r_transition_cy + r_red_cy, r_notes_cx, r_spacer_cy)),
                    cs_kb_background_dark
                )

                # Keys info
                r_key_gap = max(1.0, math.floor(r_white_cx * 0.05 + 0.5))
                r_key_gap1 = r_key_gap - math.floor(r_key_gap / 2 + 0.5)

                r_start_render = 0
                r_end_render = 127
                r_start_x = 0
                r_sharp_cy = r_top_cy * 0.67

                # Draw the white keys
                r_cur_x = r_notes_x + r_start_x
                r_cur_y = r_keys_y + r_transition_cy + r_red_cy + r_spacer_cy
                for i in range(r_start_render, r_end_render + 1):
                    if not IS_SHARP[i]:
                        if key_colors[i][0] == False:
                            DrawRectangleRecGradientV(
                                align_rectangle((r_cur_x + r_key_gap1, r_cur_y, r_white_cx - r_key_gap, r_top_cy + r_near_cy)),
                                cs_kb_white_dark, cs_kb_white
                            )
                            DrawRectangleRecGradientV(
                                align_rectangle((r_cur_x + r_key_gap1, r_cur_y + r_top_cy, r_white_cx - r_key_gap, r_near_cy)),
                                cs_kb_white_dark, cs_kb_white_verydark
                            )
                            DrawRectangleRecGradientV(
                                align_rectangle((r_cur_x + r_key_gap1, r_cur_y + r_top_cy, r_white_cx - r_key_gap, 2)),
                                cs_kb_background_dark, cs_kb_white_verydark
                            )

                            if i == 60: # C4
                                r_mx_gap = math.floor(r_white_cx * 0.25 + 0.5)
                                r_mcx = r_white_cx - r_mx_gap * 2 - r_key_gap
                                r_my = max(r_cur_y + r_top_cy - r_mcx - 5, r_cur_y + r_sharp_cy + 5)

                                rl.DrawRectangleRec(
                                    align_rectangle((r_cur_x + r_key_gap1 + r_mx_gap, r_my, r_mcx, r_cur_y + r_top_cy - 5 - r_my)),
                                    cs_kb_white_dark
                                )
                        else:
                            key_color = key_colors[i][1]
                            key_color_dark = multiply_color(key_color, 0.5)

                            DrawRectangleRecGradientV(
                                align_rectangle((r_cur_x + r_key_gap1, r_cur_y, r_white_cx - r_key_gap, r_top_cy + r_near_cy - 2.0)),
                                key_color_dark, key_color
                            )
                            rl.DrawRectangleRec(
                                align_rectangle((r_cur_x + r_key_gap1, r_cur_y + r_top_cy + r_near_cy - 2.0, r_white_cx - r_key_gap, 2.0)),
                                key_color_dark
                            )

                            if i == 60: # C4
                                r_mx_gap = math.floor(r_white_cx * 0.25 + 0.5)
                                r_mcx = r_white_cx - r_mx_gap * 2.0 - r_key_gap
                                r_my = max(r_cur_y + r_top_cy + r_near_cy - r_mcx - 7.0, r_cur_y + r_sharp_cy + 5.0)

                                rl.DrawRectangleRec(
                                    align_rectangle((r_cur_x + r_key_gap1 + r_mx_gap, r_my, r_mcx, r_cur_y+ r_top_cy + r_near_cy - 7.0 - r_my)),
                                    key_color_dark
                                )
                            DrawRectangleRecGradientH(
                                align_rectangle((math.floor(r_cur_x + r_key_gap1 + r_white_cx - r_key_gap + 0.5), r_cur_y, r_key_gap, r_top_cy + r_near_cy)),
                                cs_kb_background_verydark, cs_kb_background
                            )
                        r_cur_x += r_white_cx

                # Draw the sharps
                r_start_render = 0
                r_end_render = 127
                r_start_x = 0

                r_sharp_top = SHARP_RATIO * 0.7
                r_cur_x = r_notes_x + r_start_x
                r_cur_y = r_keys_y + r_transition_cy + r_red_cy + r_spacer_cy
                for i in range(r_start_render, r_end_render + 1):
                    if not IS_SHARP[i]:
                        r_cur_x += r_white_cx
                    else:
                        r_nudge_x = 0.0
                        r_note = i % 12
                        if r_note in {1, 6}: # C# or F#
                            r_nudge_x = -SHARP_RATIO / 5
                        elif r_note in {3, 10}: # D# or A#
                            r_nudge_x = SHARP_RATIO / 5

                        r_cx = r_white_cx * SHARP_RATIO
                        r_x = r_cur_x - r_white_cx * (SHARP_RATIO / 2 - r_nudge_x)
                        r_sharp_top_x1 = r_x + r_white_cx * (SHARP_RATIO - r_sharp_top) / 2
                        r_sharp_top_x2 = r_sharp_top_x1 + r_white_cx * r_sharp_top

                        if key_colors[i][0] == False:
                            DrawSkew(
                                (r_sharp_top_x1, r_cur_y + r_sharp_cy - r_near_cy),
                                (r_sharp_top_x2, r_cur_y + r_sharp_cy - r_near_cy),
                                (r_x + r_cx, r_cur_y + r_sharp_cy),
                                (r_x, r_cur_y + r_sharp_cy),
                                cs_kb_sharp, cs_kb_sharp, cs_kb_sharp_verydark, cs_kb_sharp_verydark
                            )
                            DrawSkew(
                                (r_sharp_top_x1, r_cur_y - r_near_cy),
                                (r_sharp_top_x1, r_cur_y + r_sharp_cy - r_near_cy),
                                (r_x, r_cur_y + r_sharp_cy),
                                (r_x, r_cur_y),
                                cs_kb_sharp, cs_kb_sharp, cs_kb_sharp_verydark, cs_kb_sharp_verydark
                            )
                            DrawSkew(
                                (r_sharp_top_x2, r_cur_y + r_sharp_cy - r_near_cy),
                                (r_sharp_top_x2, r_cur_y - r_near_cy),
                                (r_x + r_cx, r_cur_y),
                                (r_x + r_cx, r_cur_y + r_sharp_cy),
                                cs_kb_sharp, cs_kb_sharp, cs_kb_sharp_verydark, cs_kb_sharp_verydark
                            )
                            rl.DrawRectangleRec(
                                align_rectangle((r_sharp_top_x1, r_cur_y - r_near_cy, r_sharp_top_x2 - r_sharp_top_x1, r_sharp_cy)),
                                cs_kb_sharp_verydark
                            )
                            DrawSkew(
                                (r_sharp_top_x1, r_cur_y - r_near_cy),
                                (r_sharp_top_x2, r_cur_y - r_near_cy),
                                (r_sharp_top_x2, r_cur_y - r_near_cy + r_sharp_cy * 0.45),
                                (r_sharp_top_x1, r_cur_y - r_near_cy + r_sharp_cy * 0.35),
                                cs_kb_sharp_dark, cs_kb_sharp_dark, cs_kb_sharp, cs_kb_sharp
                            )
                            DrawSkew(
                                (r_sharp_top_x1, r_cur_y - r_near_cy + r_sharp_cy * 0.35),
                                (r_sharp_top_x2, r_cur_y - r_near_cy + r_sharp_cy * 0.45),
                                (r_sharp_top_x2, r_cur_y - r_near_cy + r_sharp_cy * 0.65),
                                (r_sharp_top_x1, r_cur_y - r_near_cy + r_sharp_cy * 0.55),
                                cs_kb_sharp, cs_kb_sharp, cs_kb_sharp_verydark, cs_kb_sharp_verydark
                            )
                        else:
                            key_color = key_colors[i][1]
                            key_color_dark = multiply_color(key_color, 0.5)

                            r_new_near = r_near_cy * 0.25

                            DrawSkew(
                                (r_sharp_top_x1, r_cur_y + r_sharp_cy - r_new_near),
                                (r_sharp_top_x2, r_cur_y + r_sharp_cy - r_new_near),
                                (r_x + r_cx, r_cur_y + r_sharp_cy),
                                (r_x, r_cur_y + r_sharp_cy),
                                key_color, key_color, key_color_dark, key_color_dark
                            )
                            DrawSkew(
                                (r_sharp_top_x1, r_cur_y - r_new_near),
                                (r_sharp_top_x1, r_cur_y + r_sharp_cy - r_new_near),
                                (r_x, r_cur_y + r_sharp_cy),
                                (r_x, r_cur_y),
                                key_color, key_color, key_color_dark, key_color_dark
                            )
                            DrawSkew(
                                (r_sharp_top_x2, r_cur_y + r_sharp_cy - r_new_near),
                                (r_sharp_top_x2, r_cur_y - r_new_near),
                                (r_x + r_cx, r_cur_y),
                                (r_x + r_cx, r_cur_y + r_sharp_cy),
                                key_color, key_color, key_color_dark, key_color_dark
                            )
                            rl.DrawRectangleRec(
                                align_rectangle((r_sharp_top_x1, r_cur_y - r_new_near, r_sharp_top_x2 - r_sharp_top_x1, r_sharp_cy)),
                                key_color_dark
                            )
                            DrawSkew(
                                (r_sharp_top_x1, r_cur_y - r_new_near),
                                (r_sharp_top_x2, r_cur_y - r_new_near),
                                (r_sharp_top_x2, r_cur_y - r_new_near + r_sharp_cy * 0.35),
                                (r_sharp_top_x1, r_cur_y - r_new_near + r_sharp_cy * 0.25),
                                key_color, key_color, key_color, key_color
                            )
                            DrawSkew(
                                (r_sharp_top_x1, r_cur_y - r_new_near + r_sharp_cy * 0.25),
                                (r_sharp_top_x2, r_cur_y - r_new_near + r_sharp_cy * 0.35),
                                (r_sharp_top_x2, r_cur_y - r_new_near + r_sharp_cy * 0.75),
                                (r_sharp_top_x1, r_cur_y - r_new_near + r_sharp_cy * 0.65),
                                key_color, key_color, key_color_dark, key_color_dark
                            )




            ren_dur = time.perf_counter() - ren_start

            info_text: list[tuple[str, pr.Color]] = [
                (f"Time: {"-" if midi_time < 0 else ""}{abs(midi_time)//60:.0f}:{abs(midi_time)%60:0>5.2f}{" (Paused)" if paused else ""}", pr.WHITE),
                (f"BPM: {a_bpm:.2f}", pr.WHITE),
                (f"Notes: {a_played_notes:,}", pr.WHITE),
                (f"NPS: {len(a_nps_list):,}", pr.WHITE),
                (f"Polyphony: {a_polyphony:,}", pr.WHITE),
                (f"Rendered: {v_rendered:,}", pr.WHITE),
                ("FPS: ", pr.WHITE) if delta_sec == 0 else
                (f"FPS: {1/delta_sec:,.2f}", pr.WHITE) if delta_sec < 1 else
                (f"SPF: {delta_sec:,.2f}", pr.RED),
            ]
            if DEBUG:
                info_text.extend([
                    (f"Time to audio: {audio_dur:,.4f}", pr.YELLOW),
                    (f"Time to pop: {pop_dur:,.4f}", pr.YELLOW),
                    (f"Time to pv: {pv_dur:,.4f}", pr.YELLOW),
                    (f"Time to clean: {clean_dur:,.4f}", pr.YELLOW),
                    (f"Time to sort: {sort_dur:,.4f}", pr.YELLOW),
                    (f"Time to render: {ren_dur:,.4f}", pr.YELLOW),
                    (f"Total: {audio_dur+pop_dur+pv_dur+clean_dur+sort_dur+ren_dur:,.4f}", pr.YELLOW),
                    (f"Previous delta time: {delta_sec:,.4f}", pr.YELLOW),
                ])
            if behind:
                info_text.append((f"Lagging behind by {abs(real_time - midi_time)//60:.0f}:{abs(real_time - midi_time)%60:0>7.4f}", pr.RED))

            if seekback_pending:
                seekback_text = f"Seek backwards by {abs(seekback_amount)} seconds? Press [Enter] to confirm"
                seekback_text_length = pr.measure_text(seekback_text, 30)
                pr.draw_text(seekback_text, int(WIDTH/2-seekback_text_length/2)+3, int(HEIGHT/2-33/2)+3, 30, (32, 32, 32, 255))
                pr.draw_text(seekback_text, int(WIDTH/2-seekback_text_length/2), int(HEIGHT/2-33/2), 30, pr.GREEN)

                seekback_warning = "Seeking backwards is not optimized yet, as it just restarts the entire MIDI stream. It could take a while on large MIDIs."
                seekback_warning_length = pr.measure_text(seekback_warning, 20)
                pr.draw_text(seekback_warning, int(WIDTH/2-seekback_warning_length/2)+2, int(HEIGHT/2-22/2)+2+30, 20, (32, 32, 32, 255))
                pr.draw_text(seekback_warning, int(WIDTH/2-seekback_warning_length/2), int(HEIGHT/2-22/2)+30, 20, pr.ORANGE)


            info_length = max([pr.measure_text(x, 20) for x, _ in info_text])

            rl.DrawRectangle(
                0,
                0,
                info_length + 20,
                len(info_text)*22 + 20,
                (0, 0, 0, 127)
            )

            for i, (text, tcolor) in enumerate(info_text):
                pr.draw_text(text, 10, 10 + 22*i, 20, tcolor)


            if a_finished:
                if not a_finished_time:
                    a_finished_time = midi_time
                finished_text_width = pr.measure_text(f"Playback Finished!", 20)
                pr.draw_text(f"Playback Finished!", WIDTH - finished_text_width - 10, 10, 20, pr.GREEN)
            rl.EndDrawing()

        pr.close_window()

if __name__ == "__main__":
    main()