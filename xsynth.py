from cffi import FFI
from pathlib import Path

ffi = FFI()

ffi.cdef("""
#define XSYNTH_VERSION ...
#define XSYNTH_AUDIO_EVENT_NOTEON ...
#define XSYNTH_AUDIO_EVENT_NOTEOFF ...
#define XSYNTH_AUDIO_EVENT_ALLNOTESOFF ...
#define XSYNTH_AUDIO_EVENT_ALLNOTESKILLED ...
#define XSYNTH_AUDIO_EVENT_RESETCONTROL ...
#define XSYNTH_AUDIO_EVENT_CONTROL ...
#define XSYNTH_AUDIO_EVENT_PROGRAMCHANGE ...
#define XSYNTH_AUDIO_EVENT_PITCH ...
#define XSYNTH_AUDIO_EVENT_FINETUNE ...
#define XSYNTH_AUDIO_EVENT_COARSETUNE ...
#define XSYNTH_CONFIG_SETLAYERS ...
#define XSYNTH_CONFIG_SETPERCUSSIONMODE ...
#define XSYNTH_AUDIO_CHANNELS_MONO ...
#define XSYNTH_AUDIO_CHANNELS_STEREO ...
#define XSYNTH_INTERPOLATION_NEAREST ...
#define XSYNTH_INTERPOLATION_LINEAR ...
#define XSYNTH_ENVELOPE_CURVE_LINEAR ...
#define XSYNTH_ENVELOPE_CURVE_EXPONENTIAL ...

typedef struct {
    uint32_t sample_rate;
    uint16_t audio_channels;
} XSynth_StreamParams;

typedef struct {
    int32_t channel;
    int32_t key;
} XSynth_ParallelismOptions;

typedef struct {
    XSynth_StreamParams stream_params;
    uint32_t channels;
    bool fade_out_killing;
    XSynth_ParallelismOptions parallelism;
} XSynth_GroupOptions;

typedef struct {
    void *group;
} XSynth_ChannelGroup;

typedef struct {
    void *soundfont;
} XSynth_Soundfont;

typedef struct {
    uint8_t start;
    uint8_t end;
} XSynth_ByteRange;

typedef struct {
    uint32_t channels;
    int32_t multithreading;
    bool fade_out_killing;
    double render_window_ms;
    XSynth_ByteRange ignore_range;
} XSynth_RealtimeConfig;

typedef struct {
    void *synth;
} XSynth_RealtimeSynth;

typedef struct {
    uint64_t voice_count;
    int64_t buffer;
    double render_time;
} XSynth_RealtimeStats;

typedef struct {
    uint8_t attack_curve;
    uint8_t decay_curve;
    uint8_t release_curve;
} XSynth_EnvelopeOptions;

typedef struct {
    XSynth_StreamParams stream_params;
    int16_t bank;
    int16_t preset;
    XSynth_EnvelopeOptions vol_envelope_options;
    bool use_effects;
    uint16_t interpolator;
} XSynth_SoundfontOptions;

uint32_t XSynth_GetVersion(void);
XSynth_StreamParams XSynth_GenDefault_StreamParams(void);
XSynth_ParallelismOptions XSynth_GenDefault_ParallelismOptions(void);
XSynth_GroupOptions XSynth_GenDefault_GroupOptions(void);

XSynth_ChannelGroup XSynth_ChannelGroup_Create(XSynth_GroupOptions options);
void XSynth_ChannelGroup_SendAudioEvent(XSynth_ChannelGroup handle, uint32_t channel, uint16_t event, uint16_t params);
void XSynth_ChannelGroup_SendAudioEventAll(XSynth_ChannelGroup handle, uint16_t event, uint16_t params);
void XSynth_ChannelGroup_SendConfigEvent(XSynth_ChannelGroup handle, uint32_t channel, uint16_t event, uint32_t params);
void XSynth_ChannelGroup_SendConfigEventAll(XSynth_ChannelGroup handle, uint16_t event, uint32_t params);
void XSynth_ChannelGroup_SetSoundfonts(XSynth_ChannelGroup handle, const XSynth_Soundfont *sf_ids, uint64_t count);
void XSynth_ChannelGroup_ClearSoundfonts(XSynth_ChannelGroup handle);
void XSynth_ChannelGroup_ReadSamples(XSynth_ChannelGroup handle, float *buffer, uint64_t length);
uint64_t XSynth_ChannelGroup_VoiceCount(XSynth_ChannelGroup handle);
XSynth_StreamParams XSynth_ChannelGroup_GetStreamParams(XSynth_ChannelGroup handle);
void XSynth_ChannelGroup_Drop(XSynth_ChannelGroup handle);

XSynth_RealtimeConfig XSynth_GenDefault_RealtimeConfig(void);
XSynth_RealtimeSynth XSynth_Realtime_Create(XSynth_RealtimeConfig config);
void XSynth_Realtime_SendEventU32(XSynth_RealtimeSynth handle, uint32_t event);
void XSynth_Realtime_SendAudioEvent(XSynth_RealtimeSynth handle, uint32_t channel, uint16_t event, uint16_t params);
void XSynth_Realtime_SendAudioEventAll(XSynth_RealtimeSynth handle, uint16_t event, uint16_t params);
void XSynth_Realtime_SendConfigEvent(XSynth_RealtimeSynth handle, uint32_t channel, uint16_t event, uint32_t params);
void XSynth_Realtime_SendConfigEventAll(XSynth_RealtimeSynth handle, uint16_t event, uint32_t params);
void XSynth_Realtime_SetBuffer(XSynth_RealtimeSynth handle, double render_window_ms);
void XSynth_Realtime_SetIgnoreRange(XSynth_RealtimeSynth handle, XSynth_ByteRange ignore_range);
void XSynth_Realtime_SetSoundfonts(XSynth_RealtimeSynth handle, const XSynth_Soundfont *sf_ids, uint64_t count);
void XSynth_Realtime_ClearSoundfonts(XSynth_RealtimeSynth handle);
XSynth_StreamParams XSynth_Realtime_GetStreamParams(XSynth_RealtimeSynth handle);
XSynth_RealtimeStats XSynth_Realtime_GetStats(XSynth_RealtimeSynth handle);
void XSynth_Realtime_Reset(XSynth_RealtimeSynth handle);
void XSynth_Realtime_Drop(XSynth_RealtimeSynth handle);

XSynth_EnvelopeOptions XSynth_GenDefault_EnvelopeOptions(void);
XSynth_SoundfontOptions XSynth_GenDefault_SoundfontOptions(void);
XSynth_Soundfont XSynth_Soundfont_LoadNew(const char *path, XSynth_SoundfontOptions options);
void XSynth_Soundfont_Remove(XSynth_Soundfont handle);
""")

_dll = ffi.dlopen(str(Path(__file__).parent / "xsynth-windows-x64.dll"))


# ---------------------------------------------------------------------------
# Pythonic wrappers
# ---------------------------------------------------------------------------
# pylint: disable=no-member

class XSynth:
    """Thin Python wrapper around the XSynth C API."""

    # event constants
    NOTE_ON          = XSYNTH_AUDIO_EVENT_NOTEON          = 0
    NOTE_OFF         = XSYNTH_AUDIO_EVENT_NOTEOFF         = 1
    ALL_NOTES_OFF    = XSYNTH_AUDIO_EVENT_ALLNOTESOFF     = 2
    ALL_NOTES_KILLED = XSYNTH_AUDIO_EVENT_ALLNOTESKILLED  = 3
    RESET_CONTROL    = XSYNTH_AUDIO_EVENT_RESETCONTROL    = 4
    CONTROL          = XSYNTH_AUDIO_EVENT_CONTROL         = 5
    PROGRAM_CHANGE   = XSYNTH_AUDIO_EVENT_PROGRAMCHANGE   = 6
    PITCH            = XSYNTH_AUDIO_EVENT_PITCH           = 7
    FINE_TUNE        = XSYNTH_AUDIO_EVENT_FINETUNE        = 8
    COARSE_TUNE      = XSYNTH_AUDIO_EVENT_COARSETUNE      = 9

    CONFIG_SET_LAYERS        = XSYNTH_CONFIG_SETLAYERS        = 0
    CONFIG_SET_PERCUSSION    = XSYNTH_CONFIG_SETPERCUSSIONMODE = 1

    MONO   = XSYNTH_AUDIO_CHANNELS_MONO   = 1
    STEREO = XSYNTH_AUDIO_CHANNELS_STEREO = 2

    INTERP_NEAREST = XSYNTH_INTERPOLATION_NEAREST = 0
    INTERP_LINEAR  = XSYNTH_INTERPOLATION_LINEAR  = 1

    ENV_LINEAR      = XSYNTH_ENVELOPE_CURVE_LINEAR      = 0
    ENV_EXPONENTIAL = XSYNTH_ENVELOPE_CURVE_EXPONENTIAL = 1

    @staticmethod
    def version():
        return _dll.XSynth_GetVersion()

    # -- ChannelGroup -------------------------------------------------------

    @staticmethod
    def gen_default_group_options():
        return _dll.XSynth_GenDefault_GroupOptions()

    @staticmethod
    def make_stream_params(sample_rate=44100, audio_channels=STEREO):
        p = ffi.new("XSynth_StreamParams *")
        p.sample_rate = sample_rate
        p.audio_channels = audio_channels
        return p

    @staticmethod
    def make_group_options(stream_params=None, channels=16,
                           fade_out_killing=True, parallelism_channel=0,
                           parallelism_key=0):
        o = ffi.new("XSynth_GroupOptions *")
        sp = stream_params or XSynth.make_stream_params()
        o.stream_params = sp[0]
        o.channels = channels
        o.fade_out_killing = fade_out_killing
        o.parallelism.channel = parallelism_channel
        o.parallelism.key = parallelism_key
        return o

    @staticmethod
    def channel_group_create(options):
        return _dll.XSynth_ChannelGroup_Create(options[0])

    @staticmethod
    def channel_group_send_audio_event(handle, channel, event, params):
        _dll.XSynth_ChannelGroup_SendAudioEvent(handle, channel, event, params)

    @staticmethod
    def channel_group_send_audio_event_all(handle, event, params):
        _dll.XSynth_ChannelGroup_SendAudioEventAll(handle, event, params)

    @staticmethod
    def channel_group_send_config_event(handle, channel, event, params):
        _dll.XSynth_ChannelGroup_SendConfigEvent(handle, channel, event, params)

    @staticmethod
    def channel_group_send_config_event_all(handle, event, params):
        _dll.XSynth_ChannelGroup_SendConfigEventAll(handle, event, params)

    @staticmethod
    def channel_group_set_soundfonts(handle, sf_ids):
        count = len(sf_ids)
        arr = ffi.new("XSynth_Soundfont[]", sf_ids)
        _dll.XSynth_ChannelGroup_SetSoundfonts(handle, arr, count)

    @staticmethod
    def channel_group_clear_soundfonts(handle):
        _dll.XSynth_ChannelGroup_ClearSoundfonts(handle)

    @staticmethod
    def channel_group_read_samples(handle, num_samples):
        buf = ffi.new("float[]", num_samples)
        _dll.XSynth_ChannelGroup_ReadSamples(handle, buf, num_samples)
        return list(buf)

    @staticmethod
    def channel_group_voice_count(handle):
        return _dll.XSynth_ChannelGroup_VoiceCount(handle)

    @staticmethod
    def channel_group_get_stream_params(handle):
        return _dll.XSynth_ChannelGroup_GetStreamParams(handle)

    @staticmethod
    def channel_group_drop(handle):
        _dll.XSynth_ChannelGroup_Drop(handle)

    # -- Soundfont ----------------------------------------------------------

    @staticmethod
    def gen_default_soundfont_options():
        return _dll.XSynth_GenDefault_SoundfontOptions()

    @staticmethod
    def make_soundfont_options(stream_params=None, bank=-1, preset=-1,
                               vol_envelope_options=None, use_effects=True,
                               interpolator=INTERP_NEAREST):
        o = ffi.new("XSynth_SoundfontOptions *")
        sp = stream_params or XSynth.make_stream_params()
        o.stream_params = sp[0]
        o.bank = bank
        o.preset = preset
        if vol_envelope_options:
            o.vol_envelope_options = vol_envelope_options
        o.use_effects = use_effects
        o.interpolator = interpolator
        return o

    @staticmethod
    def soundfont_load_new(path, options=None):
        if options is None:
            options = XSynth.make_soundfont_options()
        return _dll.XSynth_Soundfont_LoadNew(path.encode("utf-8"), options[0])

    @staticmethod
    def soundfont_remove(handle):
        _dll.XSynth_Soundfont_Remove(handle)

    # -- Realtime -----------------------------------------------------------

    @staticmethod
    def gen_default_realtime_config():
        return _dll.XSynth_GenDefault_RealtimeConfig()

    @staticmethod
    def make_realtime_config(channels=16, multithreading=-1,
                             fade_out_killing=False, render_window_ms=10.0,
                             ignore_start=0, ignore_end=0):
        c = ffi.new("XSynth_RealtimeConfig *")
        c.channels = channels
        c.multithreading = multithreading
        c.fade_out_killing = fade_out_killing
        c.render_window_ms = render_window_ms
        c.ignore_range.start = ignore_start
        c.ignore_range.end = ignore_end
        return c

    @staticmethod
    def realtime_create(config):
        return _dll.XSynth_Realtime_Create(config[0])

    @staticmethod
    def realtime_send_event_u32(handle, event):
        _dll.XSynth_Realtime_SendEventU32(handle, event)

    @staticmethod
    def realtime_send_audio_event(handle, channel, event, params):
        _dll.XSynth_Realtime_SendAudioEvent(handle, channel, event, params)

    @staticmethod
    def realtime_send_audio_event_all(handle, event, params):
        _dll.XSynth_Realtime_SendAudioEventAll(handle, event, params)

    @staticmethod
    def realtime_send_config_event(handle, channel, event, params):
        _dll.XSynth_Realtime_SendConfigEvent(handle, channel, event, params)

    @staticmethod
    def realtime_send_config_event_all(handle, event, params):
        _dll.XSynth_Realtime_SendConfigEventAll(handle, event, params)

    @staticmethod
    def realtime_set_buffer(handle, render_window_ms):
        _dll.XSynth_Realtime_SetBuffer(handle, render_window_ms)

    @staticmethod
    def realtime_set_ignore_range(handle, start, end):
        r = ffi.new("XSynth_ByteRange *")
        r.start = start
        r.end = end
        _dll.XSynth_Realtime_SetIgnoreRange(handle, r[0])

    @staticmethod
    def realtime_set_soundfonts(handle, sf_ids):
        count = len(sf_ids)
        arr = ffi.new("XSynth_Soundfont[]", sf_ids)
        _dll.XSynth_Realtime_SetSoundfonts(handle, arr, count)

    @staticmethod
    def realtime_clear_soundfonts(handle):
        _dll.XSynth_Realtime_ClearSoundfonts(handle)

    @staticmethod
    def realtime_get_stream_params(handle):
        return _dll.XSynth_Realtime_GetStreamParams(handle)

    @staticmethod
    def realtime_get_stats(handle):
        return _dll.XSynth_Realtime_GetStats(handle)

    @staticmethod
    def realtime_reset(handle):
        _dll.XSynth_Realtime_Reset(handle)

    @staticmethod
    def realtime_drop(handle):
        _dll.XSynth_Realtime_Drop(handle)


# ---------------------------------------------------------------------------
# Quick smoke test when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    ver = XSynth.version()
    major = (ver >> 16) & 0xFF
    minor = (ver >> 8) & 0xFF
    patch = ver & 0xFF
    print(f"XSynth version: {major}.{minor}.{patch} (0x{ver:06X})")
    print("Library loaded successfully.")
