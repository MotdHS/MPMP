# pyright: standard
import time
import mido
import mparser
import pyray as rl
from tkinter import filedialog
from collections import deque

VERSION = "v1_dev"

def file_dialog():
    return filedialog.askopenfilename(filetypes=(
        ("MIDI Files", "*.mid"),
        ("Karaoke Files (?)", "*.kar"),
    ))

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

def parse_tracks(tracks, total_events):
    color_palette: dict[tuple[int, int], tuple[int, int, int]] = {}
    notes = 0
    active_notes = {}
    events = []

    total_parsed = 0

    cci = 0 # current color index
    for i, track in enumerate(tracks, start=1):
        tick = 0
        for j, event in enumerate(track, start=1):
            ignore_event = False
            tick += event[0]
            if event[1] == "ignore":
                ignore_event = True
            elif event[1] != "tempo":
                if event[1] >> 4 == 0x9:
                    if event[3] != 0:
                        notes += 1
                        if (i, event[1] & 0b1111) not in color_palette: # color palette thing
                            color_palette[(i, event[1] & 0b1111)] = PFA_COLORS[cci%16]
                            cci += 1
                        nid = (i, event[1] & 0b1111, event[2]) # note identifier
                        active_notes[nid] = active_notes.get(nid, 0) + 1 # add to active notes
                if event[1] >> 4 in [0x8, 0x9]: # for removing active notes
                    if event[1] >> 4 == 0x8 or event[3] == 0:
                        nid = (i, event[1] & 0b1111, event[2]) # note identifier
                        if nid in active_notes:
                            active_notes[nid] -= 1
                            if not active_notes[nid]:
                                del active_notes[nid]
                        else:
                            ignore_event = True

            if not ignore_event:
                events.append([tick, i, *event[1:]])
            # print(active_notes)
            # if active_notes:
            #     time.sleep(0.01)
            total_parsed += 1
            if total_parsed%1_000 == 0:
                print(f"Parsed {total_parsed:,}/{total_events:,} events\r", end="")
        # print(f"Parsed {i:,}/{len(tracks):,}")
    print()
    return {
        "events": events,
        "color_palette": color_palette,
        "notes": notes,
    }

def main():
    file_path = file_dialog()
    print("Loading MIDI...")
    load_start = time.perf_counter()
    midi = mparser.load_midi(file_path, verbose=True)
    load_end = time.perf_counter()
    print(f"Took {load_end - load_start:.5f} seconds")


    mido.set_backend("kdmapi.mido_backend")

    ppq = midi["ppq"]
    total_events = midi["event_count"]
    parsed_tracks = parse_tracks(midi["tracks"], total_events)
    events = parsed_tracks["events"]
    color_palette = parsed_tracks["color_palette"]
    notes = parsed_tracks["notes"]

    del midi, parsed_tracks

    print(f"Notes: {notes:,}")

    print("Sorting events...")
    events = sorted(events, key=lambda x: x[0])
    print("Done!")

    with mido.open_output() as out: # type: ignore
        start_time = time.perf_counter() + 2
        a_current_time = 0

        a_bpm = 120
        a_seconds_per_tick = 60 / (a_bpm * ppq)
        a_last_tick = 0
        a_index = 0
        a_played_notes = 0
        a_polyphony = 0
        a_finished = False
        a_finished_time = 0
        a_nps_list = deque()
        a_pitch_bend = []
        a_pitch_bend_range = []
        a_rpn = []
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
        a_active_notes = [[deque() for _ in range(128)] for _2 in range(16)]
        a_min_velocity = 0
        a_max_delay = 0

        v_index = 0
        v_bpm = 120
        v_seconds_per_tick = 60 / (v_bpm * ppq)
        v_last_tick = 0
        v_notespeed = 0.15
        v_current_time = - v_notespeed
        v_time = time.perf_counter() - start_time
        v_paused_start = time.perf_counter()
        v_paused_time = 0
        v_rendered = 0
        v_max_rendered = 0

        v_notes = {}            # Only stores ACTIVE notes
        v_falling_notes = deque() # Stores FINISHED notes (rendering only)

        skipping = False
        paused = True

        rl.init_window(1280, 720, f"MotdHS's Python MIDI Player Rewritten {VERSION}")
        # rl.set_target_fps(165)

        while not rl.window_should_close() and not rl.is_key_pressed(rl.KeyboardKey.KEY_Q):
            if rl.is_key_pressed(rl.KeyboardKey.KEY_RIGHT) or rl.is_key_pressed_repeat(rl.KeyboardKey.KEY_RIGHT):
                start_time -= 2
                skipping = True
            if rl.is_key_pressed(rl.KeyboardKey.KEY_SPACE):
                if paused:
                    paused = False
                else:
                    v_paused_start = time.perf_counter()
                    paused = True
                    for channel in range(16):
                        out.send(mido.Message.from_bytes([0xB0 + channel, 123, 0]))

            if paused:
                v_paused_time = time.perf_counter() - v_paused_start
            else:
                if v_paused_time:
                    start_time += v_paused_time
                    v_paused_time = 0
                v_time = time.perf_counter() - start_time
            v_cur_ft = rl.get_frame_time()

            if skipping:
                for channel in range(16):
                    out.send(mido.Message.from_bytes([0xB0 + channel, 123, 0]))
                if paused:
                    v_time += 2

            while not paused or skipping:
                if a_index >= len(events):
                    a_finished = True
                    break
                ignore_event = False
                event = events[a_index]
                a_delta_tick = event[0] - a_last_tick
                a_current_time_temp = a_current_time + (a_delta_tick * a_seconds_per_tick)
                if a_current_time_temp > v_time:
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
                            a_nps_list.append(start_time + a_current_time + 1)
                            if event[4] < a_min_velocity:
                                ignore_event = True
                            # print(a_current_time)
                            if a_max_delay:
                                if time.perf_counter() > start_time + a_current_time + a_max_delay:
                                    ignore_event = True
                            a_active_notes[event[2] & 0b1111][event[3]].append(ignore_event)
                    if event[2] >> 4 in [0x8, 0x9]:
                        if event[2] >> 4 == 0x8 or event[4] == 0:
                            a_polyphony -= 1
                            if a_active_notes:
                                ignore_event = a_active_notes[event[2] & 0b1111][event[3]].popleft()
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

                    if (not skipping or event[2] >> 4 not in [0x8, 0x9]) and not ignore_event:
                        out.send(mido.Message.from_bytes(event[2:]))
                a_last_tick = event[0]
                a_index += 1

            try:
                while a_nps_list[0] <= time.perf_counter():
                    a_nps_list.popleft()
            except IndexError:
                pass
            if skipping:
                skipping = False

            rl.begin_drawing()
            rl.clear_background(rl.DARKGRAY)

            # --- 1. PROCESS EVENTS ---
            while True:
                if v_index >= len(events):
                    break
                ev = events[v_index]
                v_delta_tick = ev[0] - v_last_tick
                v_current_time_temp = v_current_time + (v_delta_tick * v_seconds_per_tick)
                if v_current_time_temp > v_time:
                    break
                v_current_time = v_current_time_temp

                if ev[2] == "tempo":
                    v_bpm = ev[3]
                    v_seconds_per_tick = 60 / (v_bpm * ppq)

                if ev[2] != "tempo" and ev[2] >> 4 in (0x8, 0x9):
                    evi = (ev[1], ev[2] & 0b1111, ev[3]) # Track, Channel, Note

                    # NOTE ON
                    if ev[2] >> 4 == 0x9 and ev[4] != 0:
                        if evi not in v_notes:
                            v_notes[evi] = deque()
                        v_notes[evi].append((v_current_time, ev[4]))

                    # NOTE OFF
                    else:
                        if evi in v_notes and v_notes[evi]:
                            start_t, _ = v_notes[evi].popleft() # Remove from active (FIFO)
                            duration = v_current_time - start_t
                            if not v_notes[evi]:
                                del v_notes[evi]

                            if v_current_time >= v_time - v_notespeed:
                                v_falling_notes.append([evi, start_t, duration]) # Add to falling

                v_last_tick = ev[0]
                v_index += 1

            # --- 2. CLEANUP OLD NOTES (Optimization) ---
            # efficiently remove notes that have scrolled off the bottom
            # Condition: start + duration < v_time - v_notespeed
            while len(v_falling_notes) > 0:
                # Check the oldest note (index 0)
                note = v_falling_notes[0]
                if note[1] + note[2] < v_time - v_notespeed:
                    v_falling_notes.popleft() # Fast removal
                else:
                    break # Since notes are roughly chronological, we can stop checking

            # --- 3. DRAW ALL NOTES (Unified) ---
            scale_y = 720 / v_notespeed
            scale_x = 1280 / 128

            # Merge active and falling notes for rendering
            render_queue = []

            # Add falling notes
            render_queue.extend(v_falling_notes)

            # Add active notes
            for evi, note_list in v_notes.items():
                for start, _ in note_list:
                    duration = v_time - start
                    render_queue.append((evi, start, duration))

            # Sort by start time (render older notes first, newer on top)
            render_queue.sort(key=lambda x: (x[1], x[0][1], x[0][0])) # (start, channel, track)
            # print(render_queue)
            v_rendered = 0
            for evi, start, duration in render_queue[:v_max_rendered if v_max_rendered else None]:
                # Calculate Y position
                # Same formula: Scale * (CurrentTime - Start - Duration)
                x_pos = (evi[2] + a_pitch_bend[evi[1]]*a_pitch_bend_range[evi[1]]) * scale_x
                y_pos = int(scale_y * (v_time - start - duration))
                height = int(max(1, scale_y * duration))

                note_color: tuple[int, int, int] = color_palette[evi[0:2]]

                rl.draw_rectangle(
                    int(x_pos),
                    y_pos,
                    int(scale_x),
                    height,
                    rl.Color(note_color[0], note_color[1], note_color[2], 255)
                )
                # rl.draw_rectangle_gradient_h(
                #     int(evi[2] * scale_x),
                #     int(y_pos),
                #     10,
                #     int(max(1, height)),
                #     rl.Color(*note_color, 255),
                #     rl.Color(*(int(x/1.75) for x in note_color), 255),
                # )
                rl.draw_rectangle_lines(
                    int(x_pos),
                    y_pos,
                    int(scale_x),
                    height,
                    rl.Color(int(note_color[0]/1.75), int(note_color[1]/1.75), int(note_color[2]/1.75), 255)
                )
                v_rendered += 1

            info_text: list[tuple[str, rl.Color]] = [
                (f"Time: {"-" if v_time < 0 else ""}{abs(v_time)//60:.0f}:{abs(v_time)%60:0>5.2f}{" (Paused)" if paused else ""}", rl.WHITE),
                (f"BPM: {a_bpm:.2f}", rl.WHITE),
                (f"Notes: {a_played_notes:,}/{notes:,}", rl.WHITE),
                (f"NPS: {len(a_nps_list):,}", rl.WHITE),
                (f"Polyphony: {a_polyphony:,}", rl.WHITE),
                (f"Rendered: {v_rendered:,}/{v_max_rendered:,}", rl.WHITE),
                ("FPS: ", rl.WHITE) if v_cur_ft == 0 else
                (f"FPS: {1/v_cur_ft:,.2f}", rl.WHITE) if v_cur_ft < 1 else
                (f"SPF: {v_cur_ft:,.2f}", rl.RED)
            ]

            info_length = max([rl.measure_text(x, 20) for x, _ in info_text])

            rl.draw_rectangle(
                0,
                0,
                info_length + 20,
                len(info_text)*22 + 20,
                rl.Color(0, 0, 0, 127)
            )

            for i, (text, tcolor) in enumerate(info_text):
                rl.draw_text(text, 10, 10 + 22*i, 20, tcolor)


            if a_finished:
                if not a_finished_time:
                    a_finished_time = time.perf_counter() - start_time
                finished_text_width = rl.measure_text(f"Playback Finished in {a_finished_time:.3f}!", 20)
                rl.draw_text(f"Playback Finished in {a_finished_time:.3f}!", 1280 - finished_text_width - 10, 10, 20, rl.GREEN)
            rl.end_drawing()

        rl.close_window()

if __name__ == "__main__":
    main()