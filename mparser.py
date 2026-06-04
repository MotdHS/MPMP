# pyright: standard

MThd = b"MThd"
MTrk = b"MTrk"

print("Loading MotdHS's MIDI Parser")

def decode_vlq_single(a):
    return [a >> 7, a & 0b0111_1111]

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
    ret = [value, len(result)]
    # print(ret)
    return ret

def split_chunks(inp, verbose=False):
    out = {
         "format": inp[9]
        ,"tracks": (inp[10] << 8) + inp[11]
        ,"ppq": (inp[12] << 8) + inp[13]
        ,"track_data": []
    }
    # if verbose: print(out)
    ci = 14 # current index
    for i in range(out["tracks"]):
        if inp[ci:ci+4] == MTrk:
            ci += 4
            tracklen = 0
            for j in inp[ci:ci+4]:
                tracklen <<= 8
                tracklen += j
            ci += 4
            out["track_data"].append(inp[ci:ci+tracklen])
            ci += tracklen
            if verbose:
                print(f"Loaded Track {i+1}, {tracklen} bytes long")
        else:
            if verbose:
                raise ValueError(f"Invalid MIDI file structure (probably) (Index: {ci})")
    return out

def parse_chunk(chunk, verbose=False):
    out = []
    ci = 0
    previous_event_type = 0
    while ci < len(chunk):
        delta_time = decode_vlq(chunk[ci:ci+4])
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
                out.append([delta_time[0], "tempo", tempo])
                ci += length[0]
            else:
                out.append([delta_time[0], "ignore"])
                ci += length[0]
        elif event_type in range(0xf0, 0xf8): # sysex messages, unnecessary for now
            length = decode_vlq(chunk[ci:ci+4])
            out.append([delta_time[0], "ignore"])
            ci += length[1] + length[0]

        elif event_type >> 4 in [0x8, 0x9, 0xa, 0xb, 0xe]: # note off/on, polyphonic pressure, controller, and pitch bend events
            out.append([delta_time[0], event_type, chunk[ci], chunk[ci+1]])
            ci += 2

        elif event_type >> 4 in [0xc, 0xd]: # program change/channel pressure event
            out.append([delta_time[0], event_type, chunk[ci]])
            ci += 1

        previous_event_type = event_type
    return out

def load_midi(inputfile, verbose=False):
    if verbose:
        print(f"Loading MIDI file: {inputfile}")
    midi = b""
    with open(inputfile, "rb") as file:
        midi = file.read()
    smidi = split_chunks(midi, verbose)
    pmidi = {
         "format": smidi["format"]
        ,"ppq": smidi["ppq"]
        ,"tracks": []
        ,"event_count": 0
    }
    j = 0
    for i in smidi["track_data"]:
        j += 1
        if verbose:
            print(f"Parsing Track {j:,}/{len(smidi['track_data']):,} ({len(i):,} bytes)")
        parsed_chunk = parse_chunk(i, verbose)
        pmidi["tracks"].append(parsed_chunk)
        pmidi["event_count"] += len(parsed_chunk)
    if verbose:
        print("Finished!")
    return pmidi