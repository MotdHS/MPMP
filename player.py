# pyright: standard
from pathlib import Path
import time
from typing import TYPE_CHECKING
import mido
import math
import midistream
import pyray as pr
import raylib as rl
from tkinter import filedialog
from collections import deque

VERSION = "v1_dev"

DEBUG = False
MAX_DELTA = 0

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
    color_palette: dict[int, tuple[tuple[int, int, int, int], tuple[int, int, int, int]]] = {}

    print("Done!")

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
        a_key_color_stack: list[list] = [[] for _ in range(128)]

        key_colors = [(BLACK_NOTE if IS_SHARP[x] else WHITE_NOTE) for x in range(128)]

        v_bpm = 120
        v_seconds_per_tick = 60 / (v_bpm * ppq)
        v_last_tick = 0
        v_notespeed = 0.15
        v_current_time = - v_notespeed
        midi_time = -2

        v_rendered = 0
        v_reuse_event = False
        current_color_index = 0

        v_keyboard_height = 60

        v_notes = {}            # Only stores ACTIVE notes
        v_falling_notes = deque() # Stores FINISHED notes (rendering only)

        skipping = False
        paused = True

        pr.init_window(1280, 720, f"MotdHS's Python MIDI Player Rewritten {VERSION}")
        # pr.set_target_fps(165)

        while not pr.window_should_close() and not pr.is_key_pressed(pr.KeyboardKey.KEY_Q):
            if pr.is_key_pressed(pr.KeyboardKey.KEY_RIGHT) or pr.is_key_pressed_repeat(pr.KeyboardKey.KEY_RIGHT):
                midi_time += 2
                skipping = True
            if pr.is_key_pressed(pr.KeyboardKey.KEY_END):
                midi_time += 12345678
            if pr.is_key_pressed(pr.KeyboardKey.KEY_SPACE):
                if paused:
                    paused = False
                else:
                    v_paused_start = time.perf_counter()
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
            delta_sec = time.perf_counter() - prev_time
            if not paused:
                midi_time += min(delta_sec, MAX_DELTA) if MAX_DELTA else delta_sec
            prev_time = time.perf_counter()

            if skipping:
                for channel in range(16):
                    out.send(mido.Message.from_bytes([0xB0 + channel, 123, 0]))
            if TYPE_CHECKING:
                event = (0, 0, 0, 0, 0)
            audio_start = time.perf_counter()
            key_colors = [(BLACK_NOTE if IS_SHARP[x] else WHITE_NOTE) for x in range(128)]
            a_index = -1
            while not paused or skipping: # AUDIO LOOP
                a_index += 1
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
                                    (int(fill_rgb[0]/1.75), int(fill_rgb[1]/1.75), int(fill_rgb[2]/1.75), 255),
                                )
                                current_color_index += 1
                            a_key_color_stack[event[3]].append(color_key)
                    if event[2] >> 4 in [0x8, 0x9]:
                        if event[2] >> 4 == 0x8 or event[4] == 0:
                            a_polyphony -= 1
                            stack = a_key_color_stack[event[3]]
                            color_key = (event[0] << 8) | (event[2] & 0b1111)
                            for i in range(len(stack) - 1, -1, -1):
                                if stack[i] == color_key:
                                    stack.pop(i)
                                    break
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

            for note in range(128):
                if a_key_color_stack[note]:
                    key_colors[note] = (True, color_palette[a_key_color_stack[note][-1]][0])

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
            rl.ClearBackground(rl.DARKGRAY)

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
                                (int(fill_rgb[0]/1.75), int(fill_rgb[1]/1.75), int(fill_rgb[2]/1.75), 255),
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
            scale_y = (720 - v_keyboard_height) / v_notespeed
            scale_x = (1280) / 128

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
                rl.DrawRectangle(
                    int(scale_x * key),
                    720 - v_keyboard_height,
                    int(scale_x),
                    v_keyboard_height,
                    key_colors[key][1]
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
                pr.draw_text(f"Playback Finished!", 1280 - finished_text_width - 10, 10, 20, pr.GREEN)
            rl.EndDrawing()

        pr.close_window()

if __name__ == "__main__":
    main()