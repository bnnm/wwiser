from . import wfmt


# Each major release changes bank version, and each version roughly adds +1 per breaking
# change. So if they add/remove 1 field, or multiple fields/things in a single commit = +1,
# but with some new bitflag in an existing field or restructured code there is no version
# change. Also, release number doesn't always correspond with year. Bank version is usually
# AK_SOUNDBANK_VERSION in AkTypes.h.
#
# Later SDKs support a version range (ex. 0x86: 0x76~86, 0x7F: 0x74~7F) but only for
# media content (objects still may change).
#
# Versions marked with "*" were not checked against SDKs and may contain bugs for untested games
#
# related changelog
# - 06.1: XMA1
# - 06.2: XMA2
# - 06.3: Blends
# - 07.1: Interactive music
# - 07.2: Dynamic dialogue, plugins [KK2 has DialogueEvent in code, string table]
# - 07.4: removed string table, SoundBanksInfo.xml instead of .info
bank_versions = [
    #--, #0x-- Wwise 2006.1~3  *(non-public betas)
    #14, #0x0E Wwise 2007.1/2? *[Shadowrun (X360)]
     26, #0x1A Wwise 2007.3?   *[Too Human (X360), KetnetKick 2 (PC)]
     29, #0x1D Wwise 2007.4?   *[Army of Two: The 40th Day (PS3)-test banks]
     34, #0x22 Wwise 2008.1?   *[Spider-Man: Web of Shadows (X360), The Lord of the Rings: Conquest (PC), Halo Wars (X360)]
     35, #0x23 Wwise 2008.2?   *[Jungle Speed (Wii), Punch Out!! (Wii)]
     36, #0x24 Wwise 2008.3?   *[UFC 2009 Undisputed (PS3)]
     38, #0x26 Wwise 2008.4    *[The King of Fighters XII (PS3), Food Network (Wii)]
     44, #0x2C Wwise 2009.1?   *[Assassin's Creed II (X360), Mass Effect 2 (X360), The Saboteur (X360), Doc Louis's Punch Out!! (Wii)]
     45, #0x2D Wwise 2009.2?   *[Dance on Broadway (Wii), Army of Two: The 40th Day (X360)-buggy + has v44/38/34 banks]
     46, #0x2E Wwise 2009.3     [Enslaved (X360), The King of Fighters XIII (AC), Tron Evolution (PS3), Epic Mickey (Wii), Driver: San Francisco (Wii)]
     48, #0x30 Wwise 2010.1     [Assassin's Creed: Brotherhood (X360), Splatterhouse (PS3), Harry Potter and the Deathly Hallows Part 1 (PS3), Driver: San Francisco (X360)]
     52, #0x34 Wwise 2010.2     [Chime Super Deluxe (PS3/X360), Saints Row the Third (X360)-some banks]
     53, #0x35 Wwise 2010.3     [Assassin's Creed: Revelations (X360), Saints Row the Third (X360)-most banks, Captain America: Super Soldier (X360), inFamous 2 (PS3), Harry Potter and the Deathly Hallows Part 2 (PS3)]
     56, #0x38 Wwise 2011.1     [Super Stardust Delta (Vita), I Am Alive (PS3), Trine 2 (PS3), The King of Fighters XIII (PS3)]
     62, #0x3E Wwise 2011.2     [Borderlands 2 (X360), Quantum Conumdrum (X360), South Park: Tenorman's Revenge (X360)]
     65, #0x41 Wwise 2011.3?   *[Assassin's Creed III (X360), DmC (PC), Zone of the Enders HD (X360)]
     70, #0x46 Wwise 2012.1?   *[Metal Gear Rising (PC/X360)-some banks]
     72, #0x48 Wwise 2012.2     [Metal Gear Rising (PC/X360)-most banks, Saints Row IV (PC), South Park: The Stick of Truth (PC)]
     88, #0x58 Wwise 2013.1/2   [Bayonetta 2 (WiiU), Devil's Third (WiiU), Total War: Rome (PC)]
     89, #0x59 Wwise 2013.2-B? *[Destiny (PS4)]
    112, #0x70 Wwise 2014.1     [Transformers (PS3/X360), Oddworld (Vita), Star Fox Zero (WiiU)-buggy, Star Fox Guard (WiiU)-buggy, Plants vs Zombies 2 (Android), Total War: Attila (PC)]
    113, #0x71 Wwise 2015.1     [Nier Automata (PC), Doom 2016 (PC), South Park: The Fractured But Whole (PC)]
    118, #0x76 Wwise 2016.1     [WipEout: Omega Collection (PS4), Coffence (PC), Mario + Rabbids Kingdom Battle (Switch)]
    120, #0x78 Wwise 2016.2     [Polyball (PC), Battle Chasers (PC)]
    122, #0x7A Wwise 2017.1-B? *[Total War: Warhammer 2 (PC)-update]
    125, #0x7D Wwise 2017.1     [Devil May Cry 5 (PC), Wolfenstein II The New Colossus (PC)]
    126, #0x7E Wwise 2017.1-B? *[Total War: Thrones of Britannia (PC)]
    128, #0x80 Wwise 2017.2     [Spyro Reignited Trilogy (PC/PS4), Let's Go Pikachu (Switch), Magatsu Wahrheit (Android)]
    129, #0x81 Wwise 2017.2-B? *[Total War: Three Kingdoms (PC)]
    132, #0x84 Wwise 2018.1     [Astral Chain (Switch), John Wick Hex (PC), Spyro Reignited Trilogy (Switch)]
    134, #0x86 Wwise 2019.1     [Doom Eternal (PC), Girl Cafe Gun (Android)]
   #135, #0x87 Wwise 2019.1-B? *[Total War Saga: Troy (PC)-base]
    135, #0x87 Wwise 2019.2     [Assassin's Creed: Valhalla (PC), Mario Kart Live: Home Circuit (Switch)]
    136, #0x88 Wwise 2019.2-B? *[Total War Saga: Troy (PC)-update]
    140, #0x8C Wwise 2021.1     [Disney Speedstorm (PC)]
    141, #0x8D Wwise 2021.1-B?  [Overwatch (PC)]
    144, #0x90 Wwise 2022.1-B   (none known)
    145, #0x91 Wwise 2022.1     [Sea of Stars (PC), Mortal Kombat 1 (PC)]
    150, #0x96 Wwise 2023.1     [Aster Tatariqus (Android)-update, Dead by Daylight (PC), Age of Empires II DE (PC)-2024.11 update]
    152, #0x98 Wwise 2024.1-B   (none known)
    154, #0x9A Wwise 2024.1     [Age of Empires II DE (PC)-2025.04 update]
    160, #0xA8 Wwise 2025.1.0-B (none known)-one bank
    168, #0xA8 Wwise 2025.1.0-B (none known)
    169, #0xA9 Wwise 2025.1.1-B (none known)
    171, #0xAB Wwise 2025.1.2-B (none known)
    172, #0xAC Wwise 2025.1.3   (none known)
]

# no txtp support, even if forced
partial_versions = {
  14, 26
}

ancient_versions = 25 #<=

# Total War series have some weird versions with upper bit set, possibly custom versions (src available to licensed customers)
# (all have special custom fields, that don't exist for regular versions).
bank_custom_versions = {
    0x8000007A: 122,  #same as 120
    0x8000007E: 126,  #same as 125
    0x80000081: 129,  #same as 128
    0x80000087: 135,  #same as 134 (not like 135)
    0x80000088: 136,  #some diffs vs 135 and 140
}


# for extra detection
v112_buggy_project_ids = {
  0x000004A0, #Star Fox Zero
  0x00000950  #Star Fox Guard
}
aot2_buggy_banks = {
    #base
    3915989931, #Amb_Spot_Sparks
    2026489925, #Destructibles_Car
    3309142066, #gun_type_m249saw
    4045268090, #SE_Embassy_Morality_Immoral
    4259715843, #Trig_CamShake_Debris
    #langs
    2610742330, #Global_VO
    2867304520, #VO_INT_FDI_HEAVIES
}


#TODO
# Wwise allows customs props/rtpcs (meaning not defined/registered in bnk), that start right after
# last reserved ID (MaxNum*). In those cases we want some kind of readable default if not defined.
#AkRTPC_MaxNumRTPC = { ... }


# #############################################################################
# INTERNAL HELPERS

# format helpers
fmt_hexfix = wfmt.FormatterHex(fixed=True)
fmt_hex = wfmt.FormatterHex()
fmt_ch = wfmt.FormatterChannelConfig()

# hash types
fnv_no = 'none' #special value, no hashname allowed
fnv_bnk = 'bank'
fnv_lng = 'language'
fnv_evt = 'event'
fnv_bus = 'bus'
fnv_sfx = 'sfx'
fnv_trg = 'trigger'
fnv_aco = 'acoustic texture'
fnv_gme = 'base rtpc/game-variable'
fnv_gmx = 'rtpc/game-variable' #separate from the above
fnv_var = 'variable' #switches/states names
fnv_val = 'value' #switches/states values
fnv_unk = '???'
fnv_order = [
  fnv_bnk, fnv_lng, fnv_evt, fnv_bus, fnv_sfx, fnv_trg, fnv_aco, fnv_gme, fnv_gmx, fnv_var, fnv_val, fnv_unk
]
fnv_order_join = [
  fnv_bnk, fnv_lng, fnv_bus
]
fnv_conditionals = {
    fnv_gmx
}
fnv_conditionals_origin = {
    fnv_gme
}

# #############################################################################
# AK ENUMS AND FORMATS

chunk_type = wfmt.FormatterLUT({
  b'AKBK': "Audiokinetic Bank",
  b'BKHD': "Bank Header",
  b'HIRC': "Hierarchy",
  b'DATA': "Data",
  b'STMG': "Global Settings",
  b'DIDX': "Media Index",
  b'FXPR': "FX Parameters",
  b'ENVS': "Enviroment Settings",
  b'STID': "String Mappings",
  b'PLAT': "Custom Platform",
  b'INIT': "Plugin",
})

#list from docs, only some IDs were checked but seems ok (later versions use hashnames)
language_id = wfmt.FormatterLUT({
  0x00: "SFX", #actual default, as seen in hashes
  0x01: "Arabic",
  0x02: "Bulgarian",
  0x03: "Chinese(HK)",
  0x04: "Chinese(PRC)",
  0x05: "Chinese(Taiwan)",
  0x06: "Czech",
  0x07: "Danish",
  0x08: "Dutch",
  0x09: "English(Australia)",
  0x0A: "English(India)",
  0x0B: "English(UK)",
  0x0C: "English(US)",
  0x0D: "Finnish",
  0x0E: "French(Canada)",
  0x0F: "French(France)",
  0x10: "German",
  0x11: "Greek",
  0x12: "Hebrew",
  0x13: "Hungarian",
  0x14: "Indonesian",
  0x15: "Italian",
  0x16: "Japanese",
  0x17: "Korean",
  0x18: "Latin",
  0x19: "Norwegian",
  0x1A: "Polish",
  0x1B: "Portuguese(Brazil)",
  0x1C: "Portuguese(Portugal)",
  0x1D: "Romanian",
  0x1E: "Russian",
  0x1F: "Slovenian",
  0x20: "Spanish(Mexico)",
  0x21: "Spanish(Spain)",
  0x22: "Spanish(US)",
  0x23: "Swedish",
  0x24: "Turkish",
  0x25: "Ukrainian",
  0x26: "Vietnamese",
})

#046>= 125<=
AkBank__AKBKHircType_126 = wfmt.FormatterLUT({
  0x01: "State",
  0x02: "Sound",
  0x03: "Action",
  0x04: "Event",
  0x05: "Random/Sequence Container", #RanSeqCntr
  0x06: "Switch Container", #SwitchCntr
  0x07: "Actor-Mixer", #ActorMixer
  0x08: "Bus",
  0x09: "Layer Container", #LayerCntr
  0x0a: "Music Segment", #Segment
  0x0b: "Music Track", #Track
  0x0c: "Music Switch", #MusicSwitch
  0x0d: "Music Random/Sequence", #MusicRanSeq
  0x0e: "Attenuation",
  0x0f: "DialogueEvent",
  0x10: "FeedbackBus",
  0x11: "FeedbackNode",
  0x12: "FxShareSet",
  0x13: "FxCustom",
  0x14: "Auxiliary Bus",
  0x15: "LFO",
  0x16: "Envelope",
  0x17: "AudioDevice",
})
#128>= 154<=
AkBank__AKBKHircType_128 = wfmt.FormatterLUT({
  0x01: "State",
  0x02: "Sound",
  0x03: "Action",
  0x04: "Event",
  0x05: "Random/Sequence Container",
  0x06: "Switch Container",
  0x07: "Actor-Mixer", #renamed to 'Containers' in 2025.1 but editor only, internally still Actor-Mixer
  0x08: "Audio Bus",
  0x09: "Layer Container",
  0x0a: "Music Segment",
  0x0b: "Music Track",
  0x0c: "Music Switch",
  0x0d: "Music Random Sequence",
  0x0e: "Attenuation",
  0x0f: "Dialogue Event",
  0x10: "Fx Share Set",
  0x11: "Fx Custom",
  0x12: "Auxiliary Bus",
  0x13: "LFO",
  0x14: "Envelope",
  0x15: "Audio Device",
  0x16: "Time Mod",
  0x17: "SidechainMix", #168>=
})
AkBank__AKBKHircType = None

#048>=
AkPluginType = wfmt.FormatterLUT({
  0x00: "None",
  0x01: "Codec",
  0x02: "Source",
  0x03: "Effect",
  0x04: "MotionDevice", #125<=
  0x05: "MotionSource", #125<=
  0x06: "Mixer",
  0x07: "Sink",
  0x08: "GlobalExtension", #132>=
  0x09: "Metadata", #140>=
  #Mask=0x0F
  #internal classes like Sound/Bus/DialogueEvent/etc also get plugin IDs, with type 0x10
})

AkPluginType_company = wfmt.FormatterLUT({
    0: "Audiokinetic",
    1: "Audiokinetic External",
   64: "Plugin", #PLUGINDEV_MIN

  255: "Plugin", #PLUGINDEV_MAX
  256: "McDSP",
  257: "WaveArts",
  258: "Phonetic Arts",
  259: "iZotope",
  261: "Crankcase Audio",
  262: "IOSONO",
  263: "Auro Technologies",
  264: "Dolby",
  265: "Two Big Ears",
  266: "Oculus",
  267: "Blue Ripple Sound",
  268: "Enzien Audio",
  269: "Krotos (Dehumanizer)",
  270: "Nurulize",
  271: "Super Powered",
  272: "Google",
  273: "NVIDIA",
  274: "Reserved",
  275: "Microsoft",
  276: "YAMAHA",
  277: "VisiSonics",
 
  #unofficial?
  128: "Ubisoft",
  666: "CD Projekt RED",
})

#derived from SDK includes/xmls/docs
# 0xPPPPCCCT (PPPP=plugin ID, CCC=company ID, T=Type)
AkPluginType_id = wfmt.FormatterLUT({
          -1: "None", #found in early banks with no id
  0x00000000: "None", #found in early banks with no id

  #AKCODECID
  0x00000001: "BANK",
  0x00010001: "PCM",
  0x00020001: "ADPCM",
  0x00030001: "XMA",
  0x00040001: "VORBIS",
  0x00050001: "WIIADPCM",
 #0x00060001: "?",
  0x00070001: "PCMEX", # "Standard PCM WAV file parser for Wwise Authoring" (same as PCM with another codec)
  0x00080001: "EXTERNAL_SOURCE", # "unknown encoding" (.wem can be anything defined at runtime)
  0x00090001: "XWMA",
  0x000A0001: "AAC",
  0x000B0001: "FILE_PACKAGE", # "File package files generated by the File Packager utility."
  0x000C0001: "ATRAC9",
  0x000D0001: "VAG/HE-VAG",
  0x000E0001: "PROFILERCAPTURE", # "Profiler capture file (.prof)"
  0x000F0001: "ANALYSISFILE",
  0x00100001: "MIDI", # .wmid (modified .mid)
  0x00110001: "OPUSNX", # originally just OPUS
  0x00120001: "CAF", # unused?
  0x00130001: "OPUS",
  0x00140001: "OPUS_WEM",
  0x00150001: "OPUS_WEM", #"Memory stats file as written through AK::MemoryMgr::DumpToFile()"
  0x00160001: "SONY360", #unused/internal? '360 Reality Audio', MPEG-H derived?

  #other types
  0x00640002: "Wwise Sine", #AkSineTone
  0x00650002: "Wwise Silence", #AkSilenceGenerator
  0x00660002: "Wwise Tone Generator", #AkToneGen
  0x00670003: "Wwise ?", #[The Lord of the Rings: Conquest (Wii)]
  0x00680003: "Wwise ?", #[KetnetKick 2 (PC), The Lord of the Rings: Conquest (Wii)]
  0x00690003: "Wwise Parametric EQ", #AkParametricEQ
  0x006A0003: "Wwise Delay", #AkDelay
  0x006C0003: "Wwise Compressor", #AkCompressor
  0x006D0003: "Wwise Expander", #
  0x006E0003: "Wwise Peak Limiter", #AkPeakLimiter
  0x006F0003: "Wwise ?", #[Tony Hawk's Shred (Wii)]
  0x00700003: "Wwise ?", #[Tony Hawk's Shred (Wii)]
  0x00730003: "Wwise Matrix Reverb", #AkMatrixReverb
  0x00740003: "SoundSeed Impact", #
  0x00760003: "Wwise RoomVerb", #AkRoomVerb
  0x00770002: "SoundSeed Air Wind", #AkSoundSeedAir
  0x00780002: "SoundSeed Air Woosh", #AkSoundSeedAir
  0x007D0003: "Wwise Flanger", #AkFlanger
  0x007E0003: "Wwise Guitar Distortion", #AkGuitarDistortion
  0x007F0003: "Wwise Convolution Reverb", #AkConvolutionReverb
  0x00810003: "Wwise Meter", #AkSoundEngineDLL
  0x00820003: "Wwise Time Stretch", #AkTimeStretch
  0x00830003: "Wwise Tremolo", #AkTremolo
  0x00840003: "Wwise Recorder", #
  0x00870003: "Wwise Stereo Delay", #AkStereoDelay
  0x00880003: "Wwise Pitch Shifter", #AkPitchShifter
  0x008A0003: "Wwise Harmonizer", #AkHarmonizer
  0x008B0003: "Wwise Gain", #AkGain
  0x00940002: "Wwise Synth One", #AkSynthOne
  0x00AB0003: "Wwise Reflect", #AkReflect

  0x00AE0007: "System", #DefaultSink
  0x00B00007: "Communication", #DefaultSink
  0x00B10007: "Controller Headphones", #DefaultSink
  0x00B30007: "Controller Speaker", #DefaultSink
  0x00B50007: "No Output", #DefaultSink
  0x03840009: "Wwise System Output Settings", #DefaultSink
  0x00B70002: "SoundSeed Grain", #
  0x00BA0003: "Mastering Suite", #MasteringSuite
  0x00BE0003: "Wwise 3D Audio Bed Mixer", #Ak3DAudioBedMixer
  0x00C80002: "Wwise Audio Input", #AkAudioInput
  0x01950002: "Wwise Motion Generator", #AkMotion (used in CAkSound, v128>= / v130<=?)
  0x01950005: "Wwise Motion Generator", #AkMotion (used in CAkFeedbackNode, v125<=)
  0x01990002: "Wwise Motion Source", #AkMotion (used in CAkSound, v132>=)
  0x01990005: "Wwise Motion Source?", #AkMotion
  0x01FB0007: "Wwise Motion ?", #AkMotion

  0x044C1073: "Auro Headphone", #Auro

  #other companies (IDs can be repeated)
  0x00671003: "McDSP ML1", #McDSP
  0x006E1003: "McDSP FutzBox", #

  0x00021033: "iZotope Hybrid Reverb", #
  0x00031033: "iZotope Trash Distortion", #
  0x00041033: "iZotope Trash Delay", #
  0x00051033: "iZotope Trash Dynamics Mono", #
  0x00061033: "iZotope Trash Filters", #
  0x00071033: "iZotope Trash Box Modeler", #
  0x00091033: "iZotope Trash Multiband Distortion", #

  0x006E0403: "Platinum MatrixSurroundMk2", #PgMatrixSurroundMk2
  0x006F0403: "Platinum LoudnessMeter", #PgLoudnessMeter
  0x00710403: "Platinum SpectrumViewer", #PgSpectrumViewer
  0x00720403: "Platinum EffectCollection", #PgEffectCollection
  0x00730403: "Platinum MeterWithFilter", #PgMeterWithFilter
  0x00740403: "Platinum Simple3D", #PgSimple3D
  0x00750403: "Platinum Upmixer", #PgUpmixer
  0x00760403: "Platinum Reflection", #PgReflection
  0x00770403: "Platinum Downmixer", #PgDownmixer
  0x00780403: "Platinum Flex?", #PgFlex? [Nier Automata] 

  0x00020403: "Codemasters ? Effect", # [Dirt Rally (PS4)]

  0x00640332: "Ubisoft ?", # [Mario + Rabbids DLC 3]
  0x04F70803: "Ubisoft ? Effect", # [AC Valhalla]
  0x04F80806: "Ubisoft ? Mixer", # [AC Valhalla]
  0x04F90803: "Ubisoft ? Effect", # [AC Valhalla]

  0x00AA1137: "Microsoft Spatial Sound", #MSSpatial

  0x000129A3: "CPR Simple Delay", #CDPSimpleDelay
  0x000229A2: "CPR Voice Broadcast Receive ?", #CDPVoiceBroadcastReceive
  0x000329A3: "CPR Voice Broadcast Send ?", #CDPVoiceBroadcastSend
  0x000429A2: "CPR Voice Broadcast Receive ?", #CDPVoiceBroadcastReceive
  0x000529A3: "CPR Voice Broadcast Send ?", #CDPVoiceBroadcastSend

  0x01A01052: "Crankcase REV Model Player", #CrankcaseAudioREVModelPlayer

}, zeropad=8)

#046>= 062<=
AkCurveScaling_062 = wfmt.FormatterLUT({
  0x0: "None",
  0x1: "db_255", #~046<=, not implemented in other versions
  0x2: "dB_96_3",
  0x3: "Frequency_20_20000",
  0x4: "dB_96_3_NoCheck",
})
#065<=
AkCurveScaling_065 = wfmt.FormatterLUT({
  0x0: "None",
  0x1: "Unsupported",
  0x2: "dB_96_3",
  0x3: "Frequency_20_20000",
  0x4: "dB_96_3_NoCheck",
})
#072>=
AkCurveScaling_072 = wfmt.FormatterLUT({
  0x0: "None",
 #0x1: "Unsupported",
  0x2: "dB",
  0x3: "Log",
  0x4: "dBToLin", #088>=
  #0x8: "MaxNum", #088>>
})
AkCurveScaling = None

#112>= 140<=
AkRtpcType_140 = wfmt.FormatterLUT({
  0x0: "GameParameter",
  0x1: "MIDIParameter",
  0x2: "Modulator",
  #0x8: "MaxNum",
})
#144>= ("AkGameSyncType", same field name)
AkRtpcType_144 = wfmt.FormatterLUT({
  0x0: "GameParameter",
  0x1: "MIDIParameter",
  0x2: "Switch",
  0x3: "State",
  0x4: "Modulator",
  #0x5: "Count",
  #0x8: "MaxNum",
})
AkRtpcType = None

#048>=
AkCurveInterpolation = wfmt.FormatterLUT({
  0x0: "Log3",
  0x1: "Sine",
  0x2: "Log1",
  0x3: "InvSCurve",
  0x4: "Linear",
  0x5: "SCurve",
  0x6: "Exp1",
  0x7: "SineRecip",
  0x8: "Exp3", #"LastFadeCurve" defined as 0x8 too in all versions
  0x9: "Constant",
})

#112>=
AkTransitionRampingType = wfmt.FormatterLUT({
  0x0: "None",
  0x1: "SlewRate",
  0x2: "FilteringOverTime",
})

#062<=
AkPropID_062 = wfmt.FormatterLUT({
  0x00: "Volume",
  0x01: "LFE",
  0x02: "Pitch",
  0x03: "LPF",
  0x04: "Priority",
  0x05: "PriorityDistanceOffset",
  0x06: "Loop",
  0x07: "FeedbackVolume",
  0x08: "FeedbackLPF",
  0x09: "MuteRatio",
  0x0A: "PAN_LR",
  0x0B: "PAN_FR",
  0x0C: "CenterPCT",
  0x0D: "DelayTime",
  0x0E: "TransitionTime",
  0x0F: "Probability",
})
#065<=
AkPropID_065 = wfmt.FormatterLUT({
  0x00: "Volume",
  0x01: "LFE",
  0x02: "Pitch",
  0x03: "LPF",
  0x04: "Priority",
  0x05: "PriorityDistanceOffset",
  0x06: "Loop",
  0x07: "FeedbackVolume",
  0x08: "FeedbackLPF",
  0x09: "MuteRatio",
  0x0A: "PAN_LR",
  0x0B: "PAN_FR",
  0x0C: "CenterPCT",
  0x0D: "DelayTime",
  0x0E: "TransitionTime",
  0x0F: "Probability?",
  0x10: "Probability?",
  0x11: "DialogueMode?",
  0x12: "UserAuxSendVolume0?",
  0x13: "UserAuxSendVolume1?",
  0x14: "UserAuxSendVolume2?",
  0x15: "UserAuxSendVolume3?",
  0x16: "GameAuxSendVolume?",
  0x17: "OutputBusVolume?",
  0x18: "OutputBusLPF?",
})
#088<=
AkPropID_088 = wfmt.FormatterLUT({
  0x00: "Volume",
  0x01: "LFE",
  0x02: "Pitch",
  0x03: "LPF",
  0x04: "BusVolume",
  0x05: "Priority",
  0x06: "PriorityDistanceOffset",
  0x07: "Loop",
  0x08: "FeedbackVolume",
  0x09: "FeedbackLPF",
  0x0A: "MuteRatio",
  0x0B: "PAN_LR",
  0x0C: "PAN_FR",
  0x0D: "CenterPCT",
  0x0E: "DelayTime",
  0x0F: "TransitionTime",
  0x10: "Probability",
  0x11: "DialogueMode",
  0x12: "UserAuxSendVolume0",
  0x13: "UserAuxSendVolume1",
  0x14: "UserAuxSendVolume2",
  0x15: "UserAuxSendVolume3",
  0x16: "GameAuxSendVolume",
  0x17: "OutputBusVolume",
  0x18: "OutputBusLPF",
  #0x19: "NUM" #072 max
  #088>=
  0x19: "InitialDelay",
  0x1A: "HDRBusThreshold",
  0x1B: "HDRBusRatio",
  0x1C: "HDRBusReleaseTime",
  0x1D: "HDRBusGameParam",
  0x1E: "HDRBusGameParamMin",
  0x1F: "HDRBusGameParamMax",
  0x20: "HDRActiveRange",
  0x21: "MakeUpGain",
  0x22: "LoopStart",
  0x23: "LoopEnd",
  0x24: "TrimInTime",
  0x25: "TrimOutTime",
  0x26: "FadeInTime",
  0x27: "FadeOutTime",
  0x28: "FadeInCurve",
  0x29: "FadeOutCurve",
  0x2A: "LoopCrossfadeDuration",
  0x2B: "CrossfadeUpCurve",
  0x2C: "CrossfadeDownCurve",
  #0x2D: NUM #088 max
})
#112>= 113<=
AkPropID_113 = wfmt.FormatterLUT({
  0x00: "Volume",
  0x01: "LFE",
  0x02: "Pitch",
  0x03: "LPF",
  0x04: "HPF",
  0x05: "BusVolume",
  0x06: "Priority",
 #0x06: "StatePropNum", #same ID and used in priority methods too (decomp issue?)
  0x07: "PriorityDistanceOffset",
  0x08: "FeedbackVolume",
  0x09: "FeedbackLPF",
  0x0A: "MuteRatio",
  0x0B: "PAN_LR",
  0x0C: "PAN_FR",
  0x0D: "CenterPCT",
  0x0E: "DelayTime",
  0x0F: "TransitionTime",
  0x10: "Probability",
  0x11: "DialogueMode",
  0x12: "UserAuxSendVolume0",
  0x13: "UserAuxSendVolume1",
  0x14: "UserAuxSendVolume2",
  0x15: "UserAuxSendVolume3",
  0x16: "GameAuxSendVolume",
  0x17: "OutputBusVolume",
  0x18: "OutputBusHPF",
  0x19: "OutputBusLPF",
  0x1A: "HDRBusThreshold",
  0x1B: "HDRBusRatio",
  0x1C: "HDRBusReleaseTime",
  0x1D: "HDRBusGameParam",
  0x1E: "HDRBusGameParamMin",
  0x1F: "HDRBusGameParamMax",
  0x20: "HDRActiveRange",
  0x21: "MakeUpGain",
  0x22: "LoopStart",
  0x23: "LoopEnd",
  0x24: "TrimInTime",
  0x25: "TrimOutTime",
  0x26: "FadeInTime",
  0x27: "FadeOutTime",
  0x28: "FadeInCurve",
  0x29: "FadeOutCurve",
  0x2A: "LoopCrossfadeDuration",
  0x2B: "CrossfadeUpCurve",
  0x2C: "CrossfadeDownCurve",
  0x2D: "MidiTrackingRootNote",
  0x2E: "MidiPlayOnNoteType",
  0x2F: "MidiTransposition",
  0x30: "MidiVelocityOffset",
  0x31: "MidiKeyRangeMin",
  0x32: "MidiKeyRangeMax",
  0x33: "MidiVelocityRangeMin",
  0x34: "MidiVelocityRangeMax",
  0x35: "MidiChannelMask",
  0x36: "PlaybackSpeed",
  0x37: "MidiTempoSource",
  0x38: "MidiTargetNode",
  0x39: "AttachedPluginFXID",
  0x3A: "Loop",
  0x3B: "InitialDelay",
})
#118>= 125<=
AkPropID_126 = wfmt.FormatterLUT({
  0x00: "Volume",
  0x01: "LFE",
  0x02: "Pitch",
  0x03: "LPF",
  0x04: "HPF",
  0x05: "BusVolume",
  0x06: "MakeUpGain",
  0x07: "Priority",
 #0x07: "StatePropNum", #same ID and used in priority methods too (decomp issue?)
  0x08: "PriorityDistanceOffset",
  0x09: "FeedbackVolume",
  0x0A: "FeedbackLPF",
  0x0B: "MuteRatio",
  0x0C: "PAN_LR",
  0x0D: "PAN_FR",
  0x0E: "CenterPCT",
  0x0F: "DelayTime",
  0x10: "TransitionTime",
  0x11: "Probability",
  0x12: "DialogueMode",
  0x13: "UserAuxSendVolume0",
  0x14: "UserAuxSendVolume1",
  0x15: "UserAuxSendVolume2",
  0x16: "UserAuxSendVolume3",
  0x17: "GameAuxSendVolume",
  0x18: "OutputBusVolume",
  0x19: "OutputBusHPF",
  0x1A: "OutputBusLPF",
  0x1B: "HDRBusThreshold",
  0x1C: "HDRBusRatio",
  0x1D: "HDRBusReleaseTime",
  0x1E: "HDRBusGameParam",
  0x1F: "HDRBusGameParamMin",
  0x20: "HDRBusGameParamMax",
  0x21: "HDRActiveRange",
  0x22: "LoopStart",
  0x23: "LoopEnd",
  0x24: "TrimInTime",
  0x25: "TrimOutTime",
  0x26: "FadeInTime",
  0x27: "FadeOutTime",
  0x28: "FadeInCurve",
  0x29: "FadeOutCurve",
  0x2A: "LoopCrossfadeDuration",
  0x2B: "CrossfadeUpCurve",
  0x2C: "CrossfadeDownCurve",
  0x2D: "MidiTrackingRootNote",
  0x2E: "MidiPlayOnNoteType",
  0x2F: "MidiTransposition",
  0x30: "MidiVelocityOffset",
  0x31: "MidiKeyRangeMin",
  0x32: "MidiKeyRangeMax",
  0x33: "MidiVelocityRangeMin",
  0x34: "MidiVelocityRangeMax",
  0x35: "MidiChannelMask",
  0x36: "PlaybackSpeed",
  0x37: "MidiTempoSource",
  0x38: "MidiTargetNode",
  0x39: "AttachedPluginFXID",
  0x3A: "Loop",
  0x3B: "InitialDelay",

  #0xFF: "?", #seen in DMC5, value 1.0
})
# 128>=
AkPropID_128 = wfmt.FormatterLUT({
  0x00: "Volume",
  0x01: "LFE",
  0x02: "Pitch",
  0x03: "LPF",
  0x04: "HPF",
  0x05: "BusVolume",
  0x06: "MakeUpGain",
  0x07: "Priority",
  0x08: "PriorityDistanceOffset",
  0x09: "_FeedbackVolume", #removed
  0x0A: "_FeedbackLPF", #removed
  0x0B: "MuteRatio",
  0x0C: "PAN_LR",
  0x0D: "PAN_FR",
  0x0E: "CenterPCT",
  0x0F: "DelayTime",
  0x10: "TransitionTime",
  0x11: "Probability",
  0x12: "DialogueMode",
  0x13: "UserAuxSendVolume0",
  0x14: "UserAuxSendVolume1",
  0x15: "UserAuxSendVolume2",
  0x16: "UserAuxSendVolume3",
  0x17: "GameAuxSendVolume",
  0x18: "OutputBusVolume",
  0x19: "OutputBusHPF",
  0x1A: "OutputBusLPF",
  0x1B: "HDRBusThreshold",
  0x1C: "HDRBusRatio",
  0x1D: "HDRBusReleaseTime",
  0x1E: "HDRBusGameParam",
  0x1F: "HDRBusGameParamMin",
  0x20: "HDRBusGameParamMax",
  0x21: "HDRActiveRange",
  0x22: "LoopStart",
  0x23: "LoopEnd",
  0x24: "TrimInTime",
  0x25: "TrimOutTime",
  0x26: "FadeInTime",
  0x27: "FadeOutTime",
  0x28: "FadeInCurve",
  0x29: "FadeOutCurve",
  0x2A: "LoopCrossfadeDuration",
  0x2B: "CrossfadeUpCurve",
  0x2C: "CrossfadeDownCurve",
  0x2D: "MidiTrackingRootNote",
  0x2E: "MidiPlayOnNoteType",
  0x2F: "MidiTransposition",
  0x30: "MidiVelocityOffset",
  0x31: "MidiKeyRangeMin",
  0x32: "MidiKeyRangeMax",
  0x33: "MidiVelocityRangeMin",
  0x34: "MidiVelocityRangeMax",
  0x35: "MidiChannelMask",
  0x36: "PlaybackSpeed",
  0x37: "MidiTempoSource",
  0x38: "MidiTargetNode",
  0x39: "AttachedPluginFXID",
  0x3A: "Loop",
  0x3B: "InitialDelay",
  0x3C: "UserAuxSendLPF0",
  0x3D: "UserAuxSendLPF1",
  0x3E: "UserAuxSendLPF2",
  0x3F: "UserAuxSendLPF3",
  0x40: "UserAuxSendHPF0",
  0x41: "UserAuxSendHPF1",
  0x42: "UserAuxSendHPF2",
  0x43: "UserAuxSendHPF3",
  0x44: "GameAuxSendLPF",
  0x45: "GameAuxSendHPF",
  0x46: "AttenuationID", #132>=
  0x47: "PositioningTypeBlend", #132>=
  0x48: "ReflectionBusVolume", #135>=
  0x49: "PAN_UD", #140>=
  #0x4A: AkPropID_NUM
})
AkPropID_150 = wfmt.FormatterLUT({
  #0x0: "FirstRtpc",
  0x00: "Volume",
  0x01: "Pitch",
  0x02: "LPF",
  0x03: "HPF",
  0x04: "BusVolume",
  0x05: "MakeUpGain",
  0x06: "Priority",
  0x07: "MuteRatio",
  0x08: "UserAuxSendVolume0",
  0x09: "UserAuxSendVolume1",
  0x0A: "UserAuxSendVolume2",
  0x0B: "UserAuxSendVolume3",
  0x0C: "GameAuxSendVolume",
  0x0D: "OutputBusVolume",
  0x0E: "OutputBusHPF",
  0x0F: "OutputBusLPF",
  0x10: "UserAuxSendLPF0",
  0x11: "UserAuxSendLPF1",
  0x12: "UserAuxSendLPF2",
  0x13: "UserAuxSendLPF3",
  0x14: "UserAuxSendHPF0",
  0x15: "UserAuxSendHPF1",
  0x16: "UserAuxSendHPF2",
  0x17: "UserAuxSendHPF3",
  0x18: "GameAuxSendLPF",
  0x19: "GameAuxSendHPF",
  0x1A: "ReflectionBusVolume",
  0x1B: "HDRBusThreshold",
  0x1C: "HDRBusRatio",
  0x1D: "HDRBusReleaseTime",
  0x1E: "HDRActiveRange",
  0x1F: "MidiTransposition",
  0x20: "MidiVelocityOffset",
  0x21: "PlaybackSpeed",
  0x22: "InitialDelay",
  0x23: "Positioning_Pan_X_2D",
  0x24: "Positioning_Pan_Y_2D",
  0x25: "Positioning_Pan_Z_2D",
  0x26: "Positioning_Pan_X_3D",
  0x27: "Positioning_Pan_Y_3D",
  0x28: "Positioning_Pan_Z_3D",
  0x29: "Positioning_CenterPercent",
  0x2A: "Positioning_TypeBlend",
  0x2B: "Positioning_EnableAttenuation",
  0x2C: "Positioning_Cone_AttenuationOnOff",
  0x2D: "Positioning_Cone_Attenuation",
  0x2E: "Positioning_Cone_LPF",
  0x2F: "Positioning_Cone_HPF",
  0x30: "BypassFX",
  0x31: "BypassAllFX",
  0x32: "Available_0",
  0x33: "Available_1",
  0x34: "Available_2",
  0x35: "MaxNumInstances",
  0x36: "BypassAllMetadata",
  0x37: "PlayMechanismSpecialTransitionsValue",
  #0x38: "FirstNonRtpc",
  #0x37: "LastRtpc",
  0x38: "PriorityDistanceOffset",
  0x39: "DelayTime",
  0x3A: "TransitionTime",
  0x3B: "Probability",
  0x3C: "DialogueMode",
  0x3D: "HDRBusGameParam",
  0x3E: "HDRBusGameParamMin",
  0x3F: "HDRBusGameParamMax",
  0x40: "LoopStart",
  0x41: "LoopEnd",
  0x42: "TrimInTime",
  0x43: "TrimOutTime",
  0x44: "FadeInTime",
  0x45: "FadeOutTime",
  0x46: "FadeInCurve",
  0x47: "FadeOutCurve",
  0x48: "LoopCrossfadeDuration",
  0x49: "CrossfadeUpCurve",
  0x4A: "CrossfadeDownCurve",
  0x4B: "MidiTrackingRootNote",
  0x4C: "MidiPlayOnNoteType",
  0x4D: "MidiKeyRangeMin",
  0x4E: "MidiKeyRangeMax",
  0x4F: "MidiVelocityRangeMin",
  0x50: "MidiVelocityRangeMax",
  0x51: "MidiChannelMask",
  0x52: "MidiTempoSource",
  0x53: "MidiTargetNode",
  0x54: "Loop",
  0x55: "AttenuationID",
  #0x56: "NUM",
})
AkPropID_154 = wfmt.FormatterLUT({
  #0x0: "FirstRtpc",
  0x00: "Volume",
  0x01: "Pitch",
  0x02: "LPF",
  0x03: "HPF",
  0x04: "BusVolume",
  0x05: "MakeUpGain",
  0x06: "Priority",
  0x07: "MuteRatio",
  0x08: "UserAuxSendVolume0",
  0x09: "UserAuxSendVolume1",
  0x0A: "UserAuxSendVolume2",
  0x0B: "UserAuxSendVolume3",
  0x0C: "GameAuxSendVolume",
  0x0D: "OutputBusVolume",
  0x0E: "OutputBusHPF",
  0x0F: "OutputBusLPF",
  0x10: "UserAuxSendLPF0",
  0x11: "UserAuxSendLPF1",
  0x12: "UserAuxSendLPF2",
  0x13: "UserAuxSendLPF3",
  0x14: "UserAuxSendHPF0",
  0x15: "UserAuxSendHPF1",
  0x16: "UserAuxSendHPF2",
  0x17: "UserAuxSendHPF3",
  0x18: "GameAuxSendLPF",
  0x19: "GameAuxSendHPF",
  0x1A: "ReflectionBusVolume",
  0x1B: "HDRBusThreshold",
  0x1C: "HDRBusRatio",
  0x1D: "HDRBusReleaseTime",
  0x1E: "HDRActiveRange",
  0x1F: "MidiTransposition",
  0x20: "MidiVelocityOffset",
  0x21: "PlaybackSpeed",
  0x22: "InitialDelay",
  0x23: "Positioning_Pan_X_2D",
  0x24: "Positioning_Pan_Y_2D",
  0x25: "Positioning_Pan_Z_2D",
  0x26: "Positioning_Pan_X_3D",
  0x27: "Positioning_Pan_Y_3D",
  0x28: "Positioning_Pan_Z_3D",
  0x29: "Positioning_CenterPercent",
  0x2A: "Positioning_TypeBlend",
  0x2B: "Positioning_EnableAttenuation",
  0x2C: "Positioning_Cone_AttenuationOnOff",
  0x2D: "Positioning_Cone_Attenuation",
  0x2E: "Positioning_Cone_LPF",
  0x2F: "Positioning_Cone_HPF",
  0x30: "BypassFX",
  0x31: "BypassAllFX",
  0x32: "Available_0",
  0x33: "Available_1",
  0x34: "Available_2",
  0x35: "MaxNumInstances",
  0x36: "BypassAllMetadata",
  0x37: "PlayMechanismSpecialTransitionsValue",
  0x38: "AttenuationDistanceScaling",
  #0x39: "FirstNonRtpc",
  #0x38: "LastRtpc",
  0x39: "PriorityDistanceOffset",
  0x3A: "DelayTime",
  0x3B: "TransitionTime",
  0x3C: "Probability",
  0x3D: "DialogueMode",
  0x3E: "HDRBusGameParam",
  0x3F: "HDRBusGameParamMin",
  0x40: "HDRBusGameParamMax",
  0x41: "MidiTrackingRootNote",
  0x42: "MidiPlayOnNoteType",
  0x43: "MidiKeyRangeMin",
  0x44: "MidiKeyRangeMax",
  0x45: "MidiVelocityRangeMin",
  0x46: "MidiVelocityRangeMax",
  0x47: "MidiChannelMask",
  0x48: "MidiTempoSource",
  0x49: "MidiTargetNode",
  0x4A: "Loop",
  0x4B: "AttenuationID",
  #0x4C: "NUM",
})
AkPropID_168 = wfmt.FormatterLUT({
  #0x0: "FirstRtpc",
  0x00: "Volume",
  0x01: "Pitch",
  0x02: "LPF",
  0x03: "HPF",
  0x04: "BusVolume",
  0x05: "MakeUpGain",
  0x06: "Priority",
  0x07: "MuteRatio",
  0x08: "UserAuxSendVolume0",
  0x09: "UserAuxSendVolume1",
  0x0A: "UserAuxSendVolume2",
  0x0B: "UserAuxSendVolume3",
  0x0C: "GameAuxSendVolume",
  0x0D: "OutputBusVolume",
  0x0E: "OutputBusHPF",
  0x0F: "OutputBusLPF",
  0x10: "OutputBusHSF",
  0x11: "UserAuxSendLPF0",
  0x12: "UserAuxSendLPF1",
  0x13: "UserAuxSendLPF2",
  0x14: "UserAuxSendLPF3",
  0x15: "UserAuxSendHPF0",
  0x16: "UserAuxSendHPF1",
  0x17: "UserAuxSendHPF2",
  0x18: "UserAuxSendHPF3",
  0x19: "GameAuxSendLPF",
  0x1A: "GameAuxSendHPF",
  0x1B: "GameAuxSendHSF",
  0x1C: "ReflectionBusVolume",
  0x1D: "HDRBusThreshold",
  0x1E: "HDRBusRatio",
  0x1F: "HDRBusReleaseTime",
  0x20: "HDRActiveRange",
  0x21: "MidiTransposition",
  0x22: "MidiVelocityOffset",
  0x23: "PlaybackSpeed",
  0x24: "InitialDelay",
  0x25: "Positioning_Pan_X_2D",
  0x26: "Positioning_Pan_Y_2D",
  0x27: "Positioning_Pan_Z_2D",
  0x28: "Positioning_Pan_X_3D",
  0x29: "Positioning_Pan_Y_3D",
  0x2A: "Positioning_Pan_Z_3D",
  0x2B: "Positioning_CenterPercent",
  0x2C: "Positioning_TypeBlend",
  0x2D: "Positioning_EnableAttenuation",
  0x2E: "Positioning_Cone_AttenuationOnOff",
  0x2F: "Positioning_Cone_Attenuation",
  0x30: "Positioning_Cone_LPF",
  0x31: "Positioning_Cone_HPF",
  0x32: "BypassFX",
  0x33: "BypassAllFX",
  0x34: "Available_0",
  0x35: "MaxNumInstances",
  0x36: "BypassAllMetadata",
  0x37: "PlayMechanismSpecialTransitionsValue",
  0x38: "AttenuationDistanceScaling",
  #0x39: "FirstNonRtpc",
  #0x38: "LastRtpc",
  0x39: "PriorityDistanceOffset",
  0x3A: "DelayTime",
  0x3B: "TransitionTime",
  0x3C: "Probability",
  0x3D: "DialogueMode",
  0x3E: "HDRBusGameParam",
  0x3F: "HDRBusGameParamMin",
  0x40: "HDRBusGameParamMax",
  0x41: "MidiTrackingRootNote",
  0x42: "MidiPlayOnNoteType",
  0x43: "MidiKeyRangeMin",
  0x44: "MidiKeyRangeMax",
  0x45: "MidiVelocityRangeMin",
  0x46: "MidiVelocityRangeMax",
  0x47: "MidiChannelMask",
  0x48: "MidiTempoSource",
  0x49: "MidiTargetNode",
  0x4A: "Loop",
  0x4B: "AttenuationID",
  #0x4C: "NUM",
})
AkPropID = None
AkPropID_tids = {
    "AttachedPluginFXID", "AttenuationID"
}

#046>= 088<=
AkBank__AKBKSourceType_088 = wfmt.FormatterLUT({
    0x00: "Data/bnk", #just "Data" but added "bnk" for clarity
    0x01: "Streaming",
    0x02: "PrefetchStreaming",
      -1: "NotInitialized",
})
#112>=
AkBank__AKBKSourceType_112 = wfmt.FormatterLUT({
    0x00: "Data/bnk",
    0x01: "PrefetchStreaming",
    0x02: "Streaming",
})
AkBank__AKBKSourceType = None

#046>= 056<=
AkActionType_056 = wfmt.FormatterLUT({
  0x00000: "None",
  0x12020: "SetState",
  0x70010: "BypassFX_M",
  0x70011: "BypassFX_O",
  0x80010: "ResetBypassFX_M",
  0x80011: "ResetBypassFX_O",
  0x80020: "ResetBypassFX_ALL",
  0x80021: "ResetBypassFX_ALL_O",
  0x80040: "ResetBypassFX_AE",
  0x80041: "ResetBypassFX_AE_O",
  0x60001: "SetSwitch",
  0x61001: "SetRTPC",
  0x10010: "UseState_E",
  0x11010: "UnuseState_E",
  0x04011: "Play",
  0x05011: "PlayAndContinue",
  0x01010: "Stop_E",
  0x01011: "Stop_E_O",
  0x01020: "Stop_ALL",
  0x01021: "Stop_ALL_O",
  0x01040: "Stop_AE",
  0x01041: "Stop_AE_O",
  0x02010: "Pause_E",
  0x02011: "Pause_E_O",
  0x02020: "Pause_ALL",
  0x02021: "Pause_ALL_O",
  0x02040: "Pause_AE",
  0x02041: "Pause_AE_O",
  0x03010: "Resume_E",
  0x03011: "Resume_E_O",
  0x03020: "Resume_ALL",
  0x03021: "Resume_ALL_O",
  0x03040: "Resume_AE",
  0x03041: "Resume_AE_O",
  0x90010: "Break_E",
  0x90011: "Break_E_O",
  0x06010: "Mute_M",
  0x06011: "Mute_O",
  0x07010: "Unmute_M",
  0x07011: "Unmute_O",
  0x07020: "Unmute_ALL",
  0x07021: "Unmute_ALL_O",
  0x07040: "Unmute_AE",
  0x07041: "Unmute_AE_O",
  0x0A010: "SetVolume_M",
  0x0A011: "SetVolume_O",
  0x0B010: "ResetVolume_M",
  0x0B011: "ResetVolume_O",
  0x0B020: "ResetVolume_ALL",
  0x0B021: "ResetVolume_ALL_O",
  0x0B040: "ResetVolume_AE",
  0x0B041: "ResetVolume_AE_O",
  0x08010: "SetPitch_M",
  0x08011: "SetPitch_O",
  0x09010: "ResetPitch_M",
  0x09011: "ResetPitch_O",
  0x09020: "ResetPitch_ALL",
  0x09021: "ResetPitch_ALL_O",
  0x09040: "ResetPitch_AE",
  0x09041: "ResetPitch_AE_O",
  0x0C010: "SetLFE_M",
  0x0C011: "SetLFE_O",
  0x0D010: "ResetLFE_M",
  0x0D011: "ResetLFE_O",
  0x0D020: "ResetLFE_ALL",
  0x0D021: "ResetLFE_ALL_O",
  0x0D040: "ResetLFE_AE",
  0x0D041: "ResetLFE_AE_O",
  0x0E010: "SetLPF_M",
  0x0E011: "SetLPF_O",
  0x0F010: "ResetLPF_M",
  0x0F011: "ResetLPF_O",
  0x0F020: "ResetLPF_ALL",
  0x0F021: "ResetLPF_ALL_O",
  0x0F040: "ResetLPF_AE",
  0x0F041: "ResetLPF_AE_O",
  0x20081: "StopEvent",
  0x30081: "PauseEvent",
  0x40081: "ResumeEvent",
  0x50100: "Duck",
  0xA0000: "Trigger",
  0xA0001: "Trigger_O",
  0xA0010: "Trigger_E?", #not defined, found in Splatterhouse (PS3)-v048
  0xA0011: "Trigger_E_O?", #not defined, found in Splatterhouse (PS3)-v048, I Am Alive (PS3)-v056
  0xB0010: "Seek_E", #~052>=
  0xB0011: "Seek_E_O", #~052>=
  0xB0020: "Seek_ALL", #~052>=
  0xB0021: "Seek_ALL_O", #~052>=
  0xB0040: "Seek_AE", #~052>=
  0xB0041: "Seek_AE_O", #~052>=
  0x13010: "SetGameParameter", #~056>=
  0x13011: "SetGameParameter_O", #~056>=
  0x14010: "ResetGameParameter", #~056>=
  0x14011: "ResetGameParameter_O", #~056>=
}, zeropad=5)
#062>=
AkActionType_062 = wfmt.FormatterLUT({
  0x0000: "None",
  0x1204: "SetState",
  0x1A02: "BypassFX_M",
  0x1A03: "BypassFX_O",
  0x1B02: "ResetBypassFX_M",
  0x1B03: "ResetBypassFX_O",
  0x1B04: "ResetBypassFX_ALL",
  0x1B05: "ResetBypassFX_ALL_O",
  0x1B08: "ResetBypassFX_AE",
  0x1B09: "ResetBypassFX_AE_O",
  0x1901: "SetSwitch",
  0x1002: "UseState_E",
  0x1102: "UnuseState_E",
  0x0403: "Play",
  0x0503: "PlayAndContinue", #removed in v168
  0x0102: "Stop_E",
  0x0103: "Stop_E_O",
  0x0104: "Stop_ALL",
  0x0105: "Stop_ALL_O",
  0x0108: "Stop_AE",
  0x0109: "Stop_AE_O",
  0x0202: "Pause_E",
  0x0203: "Pause_E_O",
  0x0204: "Pause_ALL",
  0x0205: "Pause_ALL_O",
  0x0208: "Pause_AE",
  0x0209: "Pause_AE_O",
  0x0302: "Resume_E",
  0x0303: "Resume_E_O",
  0x0304: "Resume_ALL",
  0x0305: "Resume_ALL_O",
  0x0308: "Resume_AE",
  0x0309: "Resume_AE_O",
  0x1C02: "Break_E",
  0x1C03: "Break_E_O",
  0x0602: "Mute_M",
  0x0603: "Mute_O",
  0x0702: "Unmute_M",
  0x0703: "Unmute_O",
  0x0704: "Unmute_ALL",
  0x0705: "Unmute_ALL_O",
  0x0708: "Unmute_AE",
  0x0709: "Unmute_AE_O",
  0x0A02: "SetVolume_M",
  0x0A03: "SetVolume_O",
  0x0B02: "ResetVolume_M",
  0x0B03: "ResetVolume_O",
  0x0B04: "ResetVolume_ALL",
  0x0B05: "ResetVolume_ALL_O",
  0x0B08: "ResetVolume_AE",
  0x0B09: "ResetVolume_AE_O",
  0x0802: "SetPitch_M",
  0x0803: "SetPitch_O",
  0x0902: "ResetPitch_M",
  0x0903: "ResetPitch_O",
  0x0904: "ResetPitch_ALL",
  0x0905: "ResetPitch_ALL_O",
  0x0908: "ResetPitch_AE",
  0x0909: "ResetPitch_AE_O",
  0x0E02: "SetLPF_M",
  0x0E03: "SetLPF_O",
  0x0F02: "ResetLPF_M",
  0x0F03: "ResetLPF_O",
  0x0F04: "ResetLPF_ALL",
  0x0F05: "ResetLPF_ALL_O",
  0x0F08: "ResetLPF_AE",
  0x0F09: "ResetLPF_AE_O",
  0x2002: "SetHPF_M",
  0x2003: "SetHPF_O",
  0x3002: "ResetHPF_M",
  0x3003: "ResetHPF_O",
  0x3004: "ResetHPF_ALL",
  0x3005: "ResetHPF_ALL_O",
  0x3008: "ResetHPF_AE",
  0x3009: "ResetHPF_AE_O",
  0x0C02: "SetBusVolume_M",
  0x0C03: "SetBusVolume_O",
  0x0D02: "ResetBusVolume_M",
  0x0D03: "ResetBusVolume_O",
  0x0D04: "ResetBusVolume_ALL",
  0x0D08: "ResetBusVolume_AE",
  0x2103: "PlayEvent",
  0x1511: "StopEvent", #not in 144>=
  0x1611: "PauseEvent", #not in 144>=
  0x1711: "ResumeEvent", #not in 144>=
  0x1820: "Duck",
  0x1D00: "Trigger",
  0x1D01: "Trigger_O",
  0x1D02: "Trigger_E?", #not defined, found in Ori and the Will of the Wisps v134
  0x1D03: "Trigger_E_O?", #not defined, found in Doom 2016 v113
  0x1E02: "Seek_E",
  0x1E03: "Seek_E_O",
  0x1E04: "Seek_ALL",
  0x1E05: "Seek_ALL_O",
  0x1E08: "Seek_AE",
  0x1E09: "Seek_AE_O",
  0x2202: "ResetPlaylist_E",
  0x2203: "ResetPlaylist_E_O",
  0x1302: "SetGameParameter",
  0x1303: "SetGameParameter_O",
  0x1402: "ResetGameParameter",
  0x1403: "ResetGameParameter_O",
  0x1F02: "Release",
  0x1F03: "Release_O",
  0x2303: "PlayEventUnknown_O?", #v136 Troy, points to regular events
  0x3102: "SetFX_M", #144>=
  0x3202: "ResetSetFX_M", #144>=
  0x3204: "ResetSetFX_ALL", #144>=
  0x4000: "NoOp", #144>=
  0x1B00: "Trigger", #150>=
  0x1B01: "Trigger_O", #150>=
  0x3302: "SetBypassFXSlot_M", #150>=
  0x3303: "SetBypassFXSlot_O", #150>=
  0x3402: "ResetBypassFXSlot_M", #150>=
  0x3403: "ResetBypassFXSlot_O", #150>=
  0x3404: "ResetBypassFXSlot_ALL", #150>=
  0x3405: "ResetBypassFXSlot_ALL_O", #150>=
  0x3502: "SetBypassAllFX_M", #150>=
  0x3503: "SetBypassAllFX_O", #150>=
  0x3602: "ResetBypassAllFX_M", #150>=
  0x3603: "ResetBypassAllFX_O", #150>=
  0x3604: "ResetBypassAllFX_ALL", #150>=
  0x3605: "ResetBypassAllFX_ALL_O", #150>=
  0x3702: "ResetAllBypassFX_M", #150>=
  0x3703: "ResetAllBypassFX_O", #150>=
  0x3704: "ResetAllBypassFX_ALL", #150>=
  0x3705: "ResetAllBypassFX_ALL_O", #150>=
}, zeropad=4)
AkActionType = None

#046>= 088<=
AkMusicTrackRanSeqType = wfmt.FormatterLUT({
  0x0: "Normal",
  0x1: "Random",
  0x2: "Sequence",
})
#112>=
AkMusicTrackType = wfmt.FormatterLUT({
  0x0: "Normal",
  0x1: "Random",
  0x2: "Sequence",
  0x3: "Switch",
})

#112>= 125<=
AkBuiltInParam_126 = wfmt.FormatterLUT({
  0x0: "None",
  0x1: "Start/Distance",
  0x2: "Azimuth",
  0x3: "Elevation",
  0x4: "ObjectAngle",
  0x5: "Obsruction",
  0x6: "Occlusion",
})
#128>= 135<=
AkBuiltInParam_128 = wfmt.FormatterLUT({
  0x0: "None",
  0x1: "Start/Distance",
  0x2: "Azimuth",
  0x3: "Elevation",
  0x4: "EmitterCone",
  0x5: "Obsruction",
  0x6: "Occlusion",
  0x7: "ListenerCone",
  0x8: "Diffraction",
  0x9: "TransmissionLoss",
  #0xA: "Max",
})
AkBuiltInParam = None

#046>=
AkDecisionTree__Mode = wfmt.FormatterLUT({
  0x0: "BestMatch",
  0x1: "Weighted",
})

#046>=
AkGroupType = wfmt.FormatterLUT({
  0x0: "Switch",
  0x1: "State",
})

#046>=
AkOnSwitchMode = wfmt.FormatterLUT({
  0x0: "PlayToEnd",
  0x1: "Stop",
})

#046>=
AkSyncType = wfmt.FormatterLUT({
  0x0: "Immediate",
  0x1: "NextGrid",
  0x2: "NextBar",
  0x3: "NextBeat",
  0x4: "NextMarker",
  0x5: "NextUserMarker",
  0x6: "EntryMarker",
  0x7: "ExitMarker",
  0x8: "ExitNever", #088>>
  0x9: "LastExitPosition", #088>>
})

#046>= 135<=
AkVirtualQueueBehavior = wfmt.FormatterLUT({
  0x0: "FromBeginning",
  0x1: "FromElapsedTime",
  0x2: "Resume",
})

#046>= 135<=
AkBelowThresholdBehavior = wfmt.FormatterLUT({
  0x0: "ContinueToPlay",
  0x1: "KillVoice",
  0x2: "SetAsVirtualVoice",
  0x3: "KillIfOneShotElseVirtual", #later 088>>
})

#065>= 088<=
AkClipAutomationType_088 = wfmt.FormatterLUT({
  0x0: "Volume",
  0x1: "LPF",
  0x2: "FadeIn",
  0x3: "FadeOut",
})
#112>=
AkClipAutomationType_112 = wfmt.FormatterLUT({
  0x0: "Volume",
  0x1: "LPF",
  0x2: "HPF",
  0x3: "FadeIn",
  0x4: "FadeOut",
})
AkClipAutomationType = None

#046>=
AkPathMode = wfmt.FormatterLUT({
  0x0: "StepSequence",
  0x1: "StepRandom",
  0x2: "ContinuousSequence",
  0x3: "ContinuousRandom",
  0x4: "StepSequencePickNewPath", #from tests, not in enum (~v134)
  0x5: "StepRandomPickNewPath", #same
})

#112~ 125<=
AkRtpcAccum_125 = wfmt.FormatterLUT({
  0x0: "Exclusive",
  0x1: "Additive",
  0x2: "Multiply",
 #0x8: "MaxNum",
})
#128>=
AkRtpcAccum_128 = wfmt.FormatterLUT({
  0x0: "None",
  0x1: "Exclusive",
  0x2: "Additive",
  0x3: "Multiply",
  0x4: "Boolean",
  0x5: "Maximum",
  0x6: "Filter",
  #0x8: "MaxNum/Count",
})
AkRtpcAccum = None

#046>=
AkValueMeaning = wfmt.FormatterLUT({
  0x0: "Default",
  0x1: "Independent",
  0x2: "Offset",
})

#132>=
Ak3DPositionType = wfmt.FormatterLUT({
  0x0: "Emitter",
  0x1: "EmitterWithAutomation",
  0x2: "ListenerWithAutomation",
})

#128~~
Ak3DSpatializationMode = wfmt.FormatterLUT({
  0x0: "None",
  0x1: "PositionOnly",
  0x2: "PositionAndOrientation",
})

#046>=
#CAkEnvironmentsMgr::eCurveXType (indirect enum)
eCurveXType = wfmt.FormatterLUT({
  0x0: "CurveObs",
  0x1: "CurveOcc",
  0x2: "CurveDiff", #152>=
  0x3: "CurveTrans", #152>=
  #0x4: "MAX_CURVE_X_TYPES",
})

#046>=
#CAkEnvironmentsMgr::eCurveYType (indirect enum)
eCurveYType = wfmt.FormatterLUT({
  0x0: "CurveVol",
  0x1: "CurveLPF",
  0x2: "CurveHPF", #112>=
  #0x3: "MAX_CURVE_Y_TYPES",
})

#046>=
AKBKStringType = wfmt.FormatterLUT({
  0x0: "None",
  0x1: "Bank",
})

#046>=
RSType = wfmt.FormatterLUT({
  0x0: "ContinuousSequence",
  0x1: "StepSequence",
  0x2: "ContinuousRandom",
  0x3: "StepRandom",

   -1: "None", #implicit
})

#046>=
AkTransitionMode = wfmt.FormatterLUT({
  0x0: "Disabled",
  0x1: "CrossFadeAmp",
  0x2: "CrossFadePower",
  0x3: "Delay",
  0x4: "SampleAccurate",
  0x5: "TriggerRate",
})

#046>=
AkRandomMode = wfmt.FormatterLUT({
  0x0: "Normal",
  0x1: "Shuffle",
})

#046>=
AkContainerMode = wfmt.FormatterLUT({
  0x0: "Random",
  0x1: "Sequence",
})

#000~~ 045~~
AkRTPC_ParameterID_045 = wfmt.FormatterLUT({
  0x0: "Volume",
  0x1: "LFE",
  0x2: "Pitch",
  0x3: "LPF",
  0x4: "PlayMechanismSpecialTransitionsValue?",
 #0x5: "Unknown?", # not defined
  0x6: "Unknown?", # not defined (AC2: related to volume?)
  0x8: "Priority?",
  0x9: "MaxNumInstances?",
  0xA: "Positioning_Radius_LPF?",
  0xB: "Positioning_Divergence_Center_PCT?",
  0xC: "Positioning_Cone_Attenuation_ON_OFF?",
  0xD: "Positioning_Cone_Attenuation?",
  0xE: "Positioning_Cone_LPF?",
  0xF: "Unknown?",  # not defined (KOF12)
 #0x10: "Unknown?", # not defined
 #0x11: "Unknown?", # not defined
 #0x12: "Unknown?", # not defined
 #0x13: "Unknown?", # not defined
  0x14: "Position_PAN_RL?",
  0x15: "Position_PAN_FR?",
  0x16: "Position_Radius_SIM_ON_OFF?",
  0x17: "Position_Radius_SIM_Attenuation?",
  0x18: "BypassFX0?",
  0x19: "BypassFX1?",
  0x1A: "BypassFX2?",
  0x1B: "BypassFX3?",
  0x1C: "BypassAllFX?",
  0x1D: "FeedbackVolume?",
  0x1E: "FeedbackLowpass?",
  0x1F: "FeedbackPitch?",
})
#046>= 053<=
AkRTPC_ParameterID_053 = wfmt.FormatterLUT({
  0x0: "Volume",
  0x1: "LFE",
  0x2: "Pitch",
  0x3: "LPF",
  0x4: "PlayMechanismSpecialTransitionsValue",
  0x5: "Unknown?", # not defined (Wwise demos: related to speed, pitch?)
 #0x6: "Unknown?", # not defined
 #0x7: "Unknown?", # not defined
  0x8: "Priority",
  0x9: "MaxNumInstances",
  0xA: "Positioning_Radius_LPF",
  0xB: "Positioning_Divergence_Center_PCT",
  0xC: "Positioning_Cone_Attenuation_ON_OFF",
  0xD: "Positioning_Cone_Attenuation",
  0xE: "Positioning_Cone_LPF",
  0xF: "Unknown?",  # not defined (AC:B)
 #0x10: "Unknown?", # not defined
 #0x11: "Unknown?", # not defined
 #0x12: "Unknown?", # not defined
 #0x13: "Unknown?", # not defined
  0x14: "Position_PAN_RL",
  0x15: "Position_PAN_FR",
  0x16: "Position_Radius_SIM_ON_OFF",
  0x17: "Position_Radius_SIM_Attenuation",
  0x18: "BypassFX0",
  0x19: "BypassFX1",
  0x1A: "BypassFX2",
  0x1B: "BypassFX3",
  0x1C: "BypassAllFX",
  0x1D: "FeedbackVolume",
  0x1E: "FeedbackLowpass",
  0x1F: "FeedbackPitch",
 #0x20: MaxNumRTPC #046~
})
#056>= 065<=
AkRTPC_ParameterID_065 = wfmt.FormatterLUT({
  0x0: "Volume",
  0x1: "LFE",
  0x2: "Pitch",
  0x3: "LPF",
  0x4: "PlayMechanismSpecialTransitionsValue?", #AC3 in FxCustom
  0x5: "Unknown?", # not defined (DmC)
  0x6: "Unknown?", # not defined (DmC, related to volume in dB: BusVolume?)
 #0x7: "Unknown?", # not defined
  0x8: "Priority",
  0x9: "MaxNumInstances",
  0xA: "Positioning_Radius_LPF",
  0xB: "Positioning_Divergence_Center_PCT",
  0xC: "Positioning_Cone_Attenuation_ON_OFF",
  0xD: "Positioning_Cone_Attenuation",
  0xE: "Positioning_Cone_LPF",
  0xF: "Unknown?",  # not defined (AC3)
 #0x10: "Unknown?", # not defined
 #0x11: "Unknown?", # not defined
 #0x12: "Unknown?", # not defined
 #0x13: "Unknown?", # not defined
  0x14: "Position_PAN_RL",
  0x15: "Position_PAN_FR",
  0x16: "Position_Radius_SIM_ON_OFF", #056<=
  0x17: "Position_Radius_SIM_Attenuation", #056<=
  0x18: "BypassFX0",
  0x19: "BypassFX1",
  0x1A: "BypassFX2",
  0x1B: "BypassFX3",
  0x1C: "BypassAllFX",
  0x1D: "FeedbackVolume",
  0x1E: "FeedbackLowpass",
  0x1F: "FeedbackPitch",
 #0x20: MaxNumRTPC

 #0x3C: "?", #Quantum Conundrum (found near -96, some volume?), AC3
 #0x3D: "?", #DmC (found near -96, some volume?)
 #0x3E: "?", #same, AC3
})
#072==
AkRTPC_ParameterID_072 = wfmt.FormatterLUT({
  0x0: "Volume",
  0x1: "LFE",
  0x2: "Pitch",
  0x3: "LPF",
  0x4: "BusVolume",
  0x5: "PlayMechanismSpecialTransitionsValue",
 #0x6: "Unknown?", # not defined
 #0x7: "Unknown?", # not defined
  0x8: "Priority",
  0x9: "MaxNumInstances",
  0xA: "Positioning_Radius_LPF",
  0xB: "Positioning_Divergence_Center_PCT",
  0xC: "Positioning_Cone_Attenuation_ON_OFF",
  0xD: "Positioning_Cone_Attenuation",
  0xE: "Positioning_Cone_LPF",
  0xF: "UserAuxSendVolume0",
  0x10: "UserAuxSendVolume1",
  0x11: "UserAuxSendVolume2",
  0x12: "UserAuxSendVolume3",
  0x13: "GameAuxSendVolume",
  0x14: "Position_PAN_RL",
  0x15: "Position_PAN_FR",
  0x16: "OutputBusVolume",
  0x17: "OutputBusLPF",
  0x18: "BypassFX0",
  0x19: "BypassFX1",
  0x1A: "BypassFX2",
  0x1B: "BypassFX3",
  0x1C: "BypassAllFX",
  0x1D: "FeedbackVolume",
  0x1E: "FeedbackLowpass",
  0x1F: "FeedbackPitch",
 #0x20: MaxNumRTPC

 #0x3E: "?", #Metal Gear Rising (found near "DB" scaling, some volume?)
})
#088==
AkRTPC_ParameterID_088 = wfmt.FormatterLUT({
  0x0: "Volume",
  0x1: "LFE",
  0x2: "Pitch",
  0x3: "LPF",
  0x4: "BusVolume",
  0x5: "PlayMechanismSpecialTransitionsValue",
  0x6: "InitialDelay",
 #0x7: "Unknown?" # not defined
  0x8: "Priority",
  0x9: "MaxNumInstances",
  0xA: "PositioningType",
  0xB: "Positioning_Divergence_Center_PCT",
  0xC: "Positioning_Cone_Attenuation_ON_OFF",
  0xD: "Positioning_Cone_Attenuation",
  0xE: "Positioning_Cone_LPF",
  0xF: "UserAuxSendVolume0",
  0x10: "UserAuxSendVolume1",
  0x11: "UserAuxSendVolume2",
  0x12: "UserAuxSendVolume3",
  0x13: "GameAuxSendVolume",
  0x14: "Position_PAN_X_2D",
  0x15: "Position_PAN_Y_2D",
  0x16: "OutputBusVolume",
  0x17: "OutputBusLPF",
  0x18: "BypassFX0",
  0x19: "BypassFX1",
  0x1A: "BypassFX2",
  0x1B: "BypassFX3",
  0x1C: "BypassAllFX",
  0x1D: "FeedbackVolume",
  0x1E: "FeedbackLowpass",
  0x1F: "FeedbackPitch",
  0x20: "HDRBusThreshold",
  0x21: "HDRBusReleaseTime",
  0x22: "HDRBusRatio",
  0x23: "HDRActiveRange",
  0x24: "MakeUpGain",
  0x25: "Position_PAN_X_3D",
  0x26: "Position_PAN_Y_3D",
 #0x27~0x39: "Unknown?" # not defined/reserved
  #0x40: "MaxNumRTPC",
})
#112>= 113<=
AkRTPC_ParameterID_113 = wfmt.FormatterLUT({
  0x0: "Volume",
  0x1: "LFE",
  0x2: "Pitch",
  0x3: "LPF",
  0x4: "HPF",
  0x5: "BusVolume",
  0x6: "InitialDelay",
  0x7: "PlayMechanismSpecialTransitionsValue",
  0x8: "Priority",
  0x9: "MaxNumInstances",
  0xA: "PositioningType",
  0xB: "Positioning_Divergence_Center_PCT",
  0xC: "Positioning_Cone_Attenuation_ON_OFF",
  0xD: "Positioning_Cone_Attenuation",
  0xE: "Positioning_Cone_LPF",
  0xF: "Positioning_Cone_HPF",
  0x13: "GameAuxSendVolume",
  0x14: "Position_PAN_X_2D",
  0x15: "Position_PAN_Y_2D",
  0x18: "BypassFX0",
  0x19: "BypassFX1",
  0x1A: "BypassFX2",
  0x1B: "BypassFX3",
  0x1C: "BypassAllFX",
  0x1D: "FeedbackVolume",
  0x1E: "FeedbackLowpass",
  0x1F: "FeedbackPitch",
  0x20: "HDRBusThreshold",
  0x21: "HDRBusReleaseTime",
  0x22: "HDRBusRatio",
  0x23: "HDRActiveRange",
  0x24: "MakeUpGain",
  0x25: "Position_PAN_X_3D",
  0x26: "Position_PAN_Y_3D",
  0x27: "MidiTransposition",
  0x28: "MidiVelocityOffset",
  0x29: "PlaybackSpeed",
 #0x2A: "ModulatorRTPCIDStart", #?
  0x2A: "ModulatorLfoDepth",
  0x2B: "ModulatorLfoAttack",
  0x2C: "ModulatorLfoFrequency",
  0x2D: "ModulatorLfoWaveform",
  0x2E: "ModulatorLfoSmoothing",
  0x2F: "ModulatorLfoPWM",
  0x30: "ModulatorLfoInitialPhase",
  0x31: "ModulatorLfoRetrigger",
  0x32: "ModulatorEnvelopeAttackTime",
  0x33: "ModulatorEnvelopeAttackCurve",
  0x34: "ModulatorEnvelopeDecayTime",
  0x35: "ModulatorEnvelopeSustainLevel",
  0x36: "ModulatorEnvelopeSustainTime",
  0x37: "ModulatorEnvelopeReleaseTime",
  0x38: "UserAuxSendVolume0",
  0x39: "UserAuxSendVolume1",
  0x3A: "UserAuxSendVolume2",
  0x3B: "UserAuxSendVolume3",
  0x3C: "OutputBusVolume",
  0x3D: "OutputBusHPF",
  0x3E: "OutputBusLPF",
  0x3F: "MuteRatio", #113>=
})
#118==
AkRTPC_ParameterID_118 = wfmt.FormatterLUT({
  #ADDITIVE_PARAMS_START
  0x0: "Volume",
  0x1: "LFE",
  0x2: "Pitch",
  0x3: "LPF",
  0x4: "HPF",
  0x5: "BusVolume",
  0x6: "InitialDelay",
  0x7: "MakeUpGain",
  0x8: "FeedbackVolume",
  0x9: "FeedbackLowpass",
  0xA: "FeedbackPitch",
  0xB: "MidiTransposition",
  0xC: "MidiVelocityOffset",
  0xD: "PlaybackSpeed",
  0xE: "MuteRatio",
  0xF: "PlayMechanismSpecialTransitionsValue",
  #OVERRIDABLE_PARAMS_START
  0x10: "Priority",
  0x11: "MaxNumInstances",
  0x12: "Position_PAN_X_2D",
  0x13: "Position_PAN_Y_2D",
  0x14: "Position_PAN_X_3D",
  0x15: "Position_PAN_Y_3D",
  0x16: "Position_PAN_Z_3D",
  0x17: "PositioningType",
  0x18: "Positioning_Divergence_Center_PCT",
  0x19: "Positioning_Cone_Attenuation_ON_OFF",
  0x1A: "Positioning_Cone_Attenuation",
  0x1B: "Positioning_Cone_LPF",
  0x1C: "Positioning_Cone_HPF",
  0x1D: "BypassFX0",
  0x1E: "BypassFX1",
  0x1F: "BypassFX2",
  0x20: "BypassFX3",
  0x21: "BypassAllFX",
  0x22: "HDRBusThreshold",
  0x23: "HDRBusReleaseTime",
  0x24: "HDRBusRatio",
  0x25: "HDRActiveRange",
  0x26: "GameAuxSendVolume",
  0x27: "UserAuxSendVolume0",
  0x28: "UserAuxSendVolume1",
  0x29: "UserAuxSendVolume2",
  0x2A: "UserAuxSendVolume3",
  0x2B: "OutputBusVolume",
  0x2C: "OutputBusHPF",
  0x2D: "OutputBusLPF",
})
#120>= 134<=
AkRTPC_ParameterID_134 = wfmt.FormatterLUT({
  #ADDITIVE_PARAMS_START
  0x0: "Volume",
  0x1: "LFE",
  0x2: "Pitch",
  0x3: "LPF",
  0x4: "HPF",
  0x5: "BusVolume",
  0x6: "InitialDelay",
  0x7: "MakeUpGain",
  0x8: "FeedbackVolume", #128>=deprecated
  0x9: "FeedbackLowpass", #128>=deprecated
  0xA: "FeedbackPitch", #128>=deprecated
  0xB: "MidiTransposition",
  0xC: "MidiVelocityOffset",
  0xD: "PlaybackSpeed",
  0xE: "MuteRatio",
  0xF: "PlayMechanismSpecialTransitionsValue",
  0x10: "MaxNumInstances",
  #OVERRIDABLE_PARAMS_START
  0x11: "Priority",
  0x12: "Position_PAN_X_2D",
  0x13: "Position_PAN_Y_2D",
  0x14: "Position_PAN_X_3D",
  0x15: "Position_PAN_Y_3D",
  0x16: "Position_PAN_Z_3D",
  0x17: "PositioningType", #132>=PositioningTypeBlend
  0x18: "Positioning_Divergence_Center_PCT",
  0x19: "Positioning_Cone_Attenuation_ON_OFF",
  0x1A: "Positioning_Cone_Attenuation",
  0x1B: "Positioning_Cone_LPF",
  0x1C: "Positioning_Cone_HPF",
  0x1D: "BypassFX0",
  0x1E: "BypassFX1",
  0x1F: "BypassFX2",
  0x20: "BypassFX3",
  0x21: "BypassAllFX",
  0x22: "HDRBusThreshold",
  0x23: "HDRBusReleaseTime",
  0x24: "HDRBusRatio",
  0x25: "HDRActiveRange",
  0x26: "GameAuxSendVolume",
  0x27: "UserAuxSendVolume0",
  0x28: "UserAuxSendVolume1",
  0x29: "UserAuxSendVolume2",
  0x2A: "UserAuxSendVolume3",
  0x2B: "OutputBusVolume",
  0x2C: "OutputBusHPF",
  0x2D: "OutputBusLPF",
  0x2E: "Attenuation", #134=Positioning_EnableAttenuation
  #128>=
  0x2F: "UserAuxSendLPF0",
  0x30: "UserAuxSendLPF1",
  0x31: "UserAuxSendLPF2",
  0x32: "UserAuxSendLPF3",
  0x33: "UserAuxSendHPF0",
  0x34: "UserAuxSendHPF1",
  0x35: "UserAuxSendHPF2",
  0x36: "UserAuxSendHPF3",
  0x37: "GameAuxSendLPF",
  0x38: "GameAuxSendHPF",
  #~132
  0x3C: "Unknown/Custom?", #Spyro Ignited Trilogy (Switch)
  0x3D: "Unknown/Custom?", #same
  0x3E: "Unknown/Custom?", #same
  0x40: "Unknown/Custom?", #Bayonetta 2 (Switch), near volumes
  0x41: "Unknown/Custom?", #same
})
#135>=
AkRTPC_ParameterID_135 = wfmt.FormatterLUT({
  #ADDITIVE_PARAMS_START
  0x0: "Volume",
  0x1: "LFE",
  0x2: "Pitch",
  0x3: "LPF",
  0x4: "HPF",
  0x5: "BusVolume",
  0x6: "InitialDelay",
  0x7: "MakeUpGain",
  0x8: "Deprecated_FeedbackVolume", #140~~ Deprecated_RTPC_FeedbackVolume
  0x9: "Deprecated_FeedbackLowpass", #140~~ Deprecated_RTPC_FeedbackLowpass
  0xA: "Deprecated_FeedbackPitch", ##140~~ Deprecated_RTPC_FeedbackPitch
  0xB: "MidiTransposition",
  0xC: "MidiVelocityOffset",
  0xD: "PlaybackSpeed",
  0xE: "MuteRatio",
  0xF: "PlayMechanismSpecialTransitionsValue",
  0x10: "MaxNumInstances",
  #OVERRIDABLE_PARAMS_START
  0x11: "Priority",
  0x12: "Position_PAN_X_2D",
  0x13: "Position_PAN_Y_2D",
  0x14: "Position_PAN_X_3D",
  0x15: "Position_PAN_Y_3D",
  0x16: "Position_PAN_Z_3D",
  0x17: "PositioningTypeBlend",
  0x18: "Positioning_Divergence_Center_PCT",
  0x19: "Positioning_Cone_Attenuation_ON_OFF",
  0x1A: "Positioning_Cone_Attenuation",
  0x1B: "Positioning_Cone_LPF",
  0x1C: "Positioning_Cone_HPF",
  0x1D: "BypassFX0",
  0x1E: "BypassFX1",
  0x1F: "BypassFX2",
  0x20: "BypassFX3",
  0x21: "BypassAllFX",
  0x22: "HDRBusThreshold",
  0x23: "HDRBusReleaseTime",
  0x24: "HDRBusRatio",
  0x25: "HDRActiveRange",
  0x26: "GameAuxSendVolume",
  0x27: "UserAuxSendVolume0",
  0x28: "UserAuxSendVolume1",
  0x29: "UserAuxSendVolume2",
  0x2A: "UserAuxSendVolume3",
  0x2B: "OutputBusVolume",
  0x2C: "OutputBusHPF",
  0x2D: "OutputBusLPF",
  0x2E: "Positioning_EnableAttenuation",
  0x2F: "ReflectionsVolume",
  0x30: "UserAuxSendLPF0",
  0x31: "UserAuxSendLPF1",
  0x32: "UserAuxSendLPF2",
  0x33: "UserAuxSendLPF3",
  0x34: "UserAuxSendHPF0",
  0x35: "UserAuxSendHPF1",
  0x36: "UserAuxSendHPF2",
  0x37: "UserAuxSendHPF3",
  0x38: "GameAuxSendLPF",
  0x39: "GameAuxSendHPF",
  0x3A: "Position_PAN_Z_2D",
  0x3B: "BypassAllMetadata",
  #0x3C: "MaxNumRTPC,

  0x3D: "Unknown/Custom?", #AC Valhalla
  0x3E: "Unknown/Custom?", #AC Valhalla (found near "DB" scaling, some volume?)
  0x3F: "Unknown/Custom?", #AC Valhalla
})
#AkRTPC_ParameterID_150 = AkPropID_150 #not defined? same as a regular prop? internally AkRtpcPropID
AkRTPC_ParameterID = None

#118>=
AkRTPC_ModulatorParamID = wfmt.FormatterLUT({
  #ModulatorRTPCIDStart
  0x0: "ModulatorLfoDepth",
  0x1: "ModulatorLfoAttack",
  0x2: "ModulatorLfoFrequency",
  0x3: "ModulatorLfoWaveform",
  0x4: "ModulatorLfoSmoothing",
  0x5: "ModulatorLfoPWM",
  0x6: "ModulatorLfoInitialPhase",
  0x7: "ModulatorLfoRetrigger",
  0x8: "ModulatorEnvelopeAttackTime",
  0x9: "ModulatorEnvelopeAttackCurve",
  0xA: "ModulatorEnvelopeDecayTime",
  0xB: "ModulatorEnvelopeSustainLevel",
  0xC: "ModulatorEnvelopeSustainTime",
  0xD: "ModulatorEnvelopeReleaseTime",
  0xE: "ModulatorTimePlaybackSpeed", #132~~
  0xF: "ModulatorTimeInitialDelay", #132~~
  #0x10: "MaxNumModulatorRTPC",
})
#AkRTPC_ModulatorParamID_150 = AkRTPC_ModulatorParamID #not defined?

#112>=
AkModulatorPropID_112 = wfmt.FormatterLUT({
  0x0: "Scope",
  0x1: "Envelope_StopPlayback",
  0x2: "Lfo_Depth",
  0x3: "Lfo_Attack",
  0x4: "Lfo_Frequency",
  0x5: "Lfo_Waveform",
  0x6: "Lfo_Smoothing",
  0x7: "Lfo_PWM",
  0x8: "Lfo_InitialPhase",
  0x9: "Envelope_AttackTime",
  0xA: "Envelope_AttackCurve",
  0xB: "Envelope_DecayTime",
  0xC: "Envelope_SustainLevel",
  0xD: "Envelope_SustainTime",
  0xE: "Envelope_ReleaseTime",
  0xF: "Envelope_TriggerOn",
  0x10: "Time_Duration", #132~~
  0x11: "Time_Loops", #132~~
  0x12: "Time_PlaybackRate", #132~~
  0x13: "Time_InitialDelay", #132~~
  #0x14: "NUM",
})
AkModulatorPropID_150 = wfmt.FormatterLUT({
  0x0: "Scope",
  0x1: "Envelope_StopPlayback",
  0x2: "Lfo_Depth",
  0x3: "Lfo_Attack",
  0x4: "Lfo_Frequency",
  0x5: "Lfo_Waveform",
  0x6: "Lfo_Smoothing",
  0x7: "Lfo_PWM",
  0x8: "Lfo_InitialPhase",
  0x9: "Lfo_Retrigger",
  0xA: "Envelope_AttackTime",
  0xB: "Envelope_AttackCurve",
  0xC: "Envelope_DecayTime",
  0xD: "Envelope_SustainLevel",
  0xE: "Envelope_SustainTime",
  0xF: "Envelope_ReleaseTime",
  0x10: "Envelope_TriggerOn",
  0x11: "Time_Duration",
  0x12: "Time_Loops",
  0x13: "Time_PlaybackRate",
  0x14: "Time_InitialDelay",
  #0x15: "NUM",
})
AkModulatorPropID = None
AkModulatorPropID_tids = {
}

#065>>
AkJumpToSelType = wfmt.FormatterLUT({
  0x0: "StartOfPlaylist",
  0x1: "SpecificItem",
  0x2: "LastPlayedSegment",
  0x3: "NextSegment",
})

#046>=
AkEntryType = wfmt.FormatterLUT({
   0x0: "EntryMarker",
   0x1: "SameTime",
   0x2: "RandomMarker",
   0x3: "RandomUserMarker",
   0x4: "LastExitTime", #062>>
})

#046>= 088<=
AkPositioningType = wfmt.FormatterLUT({
  0x0: "Undefined",
  0x1: "2DPositioning",
  0x2: "3DUserDef",
  0x3: "3DGameDef",
})

#132>=
AkSpeakerPanningType = wfmt.FormatterLUT({
  0x0: "DirectSpeakerAssignment",
  0x1: "BalanceFadeHeight",
  0x2: "SteeringPanner", #140>=
})

#120>=
AkChannelConfigType = wfmt.FormatterLUT({
  0x0: "Anonymous",
  0x1: "Standard",
  0x2: "Ambisonic",
  0x3: "Objects", #140>=
  0xE: "UseDeviceMain", #140>=
  0xF: "UseDevicePassthrough", #140>=
})

#maybe needed? not directly used in code AkSoundEngine, maybe other for internal engine things, some repeats

# various positioning params
#048>= 135<=
#AkPositioning_ParameterID

# may to be used with "Loop" values and and AkProp's "Loop", could be added
# - loop = 0 means "loop infinite"
# - loop = 1 means "play once" = "don't actually loop" (can be set via editor, but usually not saven in .bnk)
# - loop = 2 means "play twice", etc
#1xx~~ 135<=2
AkLoopValue = wfmt.FormatterLUT({
  0x0: "Infinite",
  0x1: "NotLooping",
  #0xN: N times
})

# no idea
#AkPathStepOnNewSound = wfmt.FormatterLUT({
#  0x0: "StepNormal",
#  0x4: "StepNewSound",
#})


# seems related to "auto-defined soundbanks"
#144>=
AkBankTypeEnum = wfmt.FormatterLUT({
  0x00: "User",
  0x1E: "Event",
  0x1F: "Bus",
})

#144>=
AkFilterBehavior = wfmt.FormatterLUT({
  0x0: "Additive",
  0x1: "Maximum",
})

# #############################################################################
# PLUGIN ENUMS (prefixed since they are prone to collisions)

CAkToneGen__AkToneGenType = wfmt.FormatterLUT({
  0x0: "SINE",
  0x1: "TRIANGLE",
  0x2: "SQUARE",
  0x3: "SAWTOOTH",
  0x4: "WHITENOISE",
  0x5: "PINKNOISE",
})

CAkToneGen__AkToneGenMode = wfmt.FormatterLUT({
  0x0: "FIX",
  0x1: "ENV",
})

CAkToneGen__AkToneGenSweep = wfmt.FormatterLUT({
  0x0: "LIN",
  0x1: "LOG",
})

CAkStereoDelayFX__AkFilterType = wfmt.FormatterLUT({
  0x0: "NONE",
  0x1: "LOWSHELF",
  0x2: "PEAKINGEQ",
  0x3: "HIGHSHELF",
  0x4: "LOWPASS",
  0x5: "HIGHPASS",
  0x6: "BANDPASS",
  0x7: "NOTCH",
})

CAkStereoDelayFX__AkInputChannelType = wfmt.FormatterLUT({
  0x0: "LEFT_OR_RIGHT",
  0x1: "CENTER",
  0x2: "DOWNMIX",
  0x3: "NONE",
})

CAkSynthOne__AkSynthOneWaveType = wfmt.FormatterLUT({
  0x0: "Sine",
  0x1: "Triangle",
  0x2: "Square",
  0x3: "Sawtooth",
})

CAkSynthOne__AkSynthOneNoiseType = wfmt.FormatterLUT({
  0x0: "White",
  0x1: "Pink",
  0x2: "Red",
  0x3: "Purple",
})

CAkSynthOne__AkSynthOneOperationMode = wfmt.FormatterLUT({
  0x0: "Mix",
  0x1: "Ring",
})

CAkSynthOne__AkSynthOneFrequencyMode = wfmt.FormatterLUT({
  0x0: "Specify",
  0x1: "MidiNote",
})

CAkRoomVerbFX__FilterInsertType = wfmt.FormatterLUT({
  0x0: "OFF",
  0x1: "ERONLY",
  0x2: "REVERBONLY",
  0x3: "ERANDREVERB",
})

CAkRoomVerbFX__FilterCurveType = wfmt.FormatterLUT({
  0x0: "LOWSHELF",
  0x1: "PEAKING",
  0x2: "HIGHSHELF",
})

CAkParameterEQ__AkFilterType = wfmt.FormatterLUT({
  0x0: "LOWPASS",
  0x1: "HIPASS",
  0x2: "BANDPASS",
  0x3: "NOTCH",
  0x4: "LOWSHELF",
  0x5: "HISHELF",
  0x6: "PEAKINGEQ",
})

CAkConvolutionReverbFX__AkConvolutionAlgoType = wfmt.FormatterLUT({
  0x0: "DOWNMIX",
  0x1: "DIRECT",
})

CAkFDNReverbFX__AkDelayLengthsMode = wfmt.FormatterLUT({
  0x0: "DEFAULT",
  0x1: "CUSTOM",
})

CAkMeterFX__AkMeterScope = wfmt.FormatterLUT({
  0x0: "Global",
  0x1: "GameObject",
})

CAkMeterFX__AkMeterMode = wfmt.FormatterLUT({
  0x0: "Peak",
  0x1: "RMS",
})

CAkFlangerFX__Waveform = wfmt.FormatterLUT({ #DSP::LFO::Waveform
  0x0: "FIRST/SINE",
  0x1: "TRIANGLE",
  0x2: "SQUARE",
  0x3: "SAW_UP",
  0x4: "SAW_DOWN",
  0x5: "RND",
  #0x6: "NUM",
})

CAkFlangerFX__PhaseMode = wfmt.FormatterLUT({ #DSP::LFO::MultiChannel::PhaseMode
  0x0: "LEFT_RIGHT",
  0x1: "FRONT_REAR",
  0x2: "CIRCULAR",
  0x3: "RANDOM",
})

CAkGuitarDistortion__AkFilterType = wfmt.FormatterLUT({
  0x0: "LOWSHELF",
  0x1: "PEAKINGEQ",
  0x2: "HIGHSHELF",
  0x3: "LOWPASS",
  0x4: "HIGHPASS",
  0x5: "BANDPASS",
  0x6: "NOTCH",
})

CAkGuitarDistortion__AkDistortionType = wfmt.FormatterLUT({
  0x0: "NONE",
  0x1: "OVERDRIVE",
  0x2: "HEAVY",
  0x3: "FUZZ",
  0x4: "CLIP",
})

CAkHarmonizerFX__AkInputType = wfmt.FormatterLUT({
  0x0: "ASINPUT",
  0x1: "CENTER",
  0x2: "STEREO",
  0x3: "3POINT0",
  0x4: "4POINT0",
  0x5: "5POINT0",
  0x6: "LEFTONLY",
})

CAkHarmonizerFX__AkFilterType_0 = wfmt.FormatterLUT({
  0x0: "NONE",
  0x1: "LOWSHELF_0",
  0x2: "PEAKINGEQ_0",
  0x3: "HIGHSHELF_0",
  0x4: "LOWPASS_0",
  0x5: "HIGHPASS_0",
  0x6: "BANDPASS_0",
  0x7: "NOTCH_0",
})


# #############################################################################
# VERSION SETUP

def setup(version):
    #many of these enums are very similar but annoyingly put new values in the middle,
    #so versions without SDK to check are likely wrong. It's also hard to guess given
    #the huge number of parameters

    global AkCurveScaling
    if   version <= 62:
        AkCurveScaling = AkCurveScaling_062
    elif   version <= 65:
        AkCurveScaling = AkCurveScaling_065
    else:
        AkCurveScaling = AkCurveScaling_072

    global AkRtpcType
    if   version <= 140:
        AkRtpcType = AkRtpcType_140
    else:
        AkRtpcType = AkRtpcType_144

    global AkRTPC_ParameterID
    if   version <= 45:
        AkRTPC_ParameterID = AkRTPC_ParameterID_045
    elif version <= 53:
        AkRTPC_ParameterID = AkRTPC_ParameterID_053
    elif version <= 65:
        AkRTPC_ParameterID = AkRTPC_ParameterID_065
    elif version <= 72:
        AkRTPC_ParameterID = AkRTPC_ParameterID_072
    elif version <= 89:
        AkRTPC_ParameterID = AkRTPC_ParameterID_088
    elif version <= 113:
        AkRTPC_ParameterID = AkRTPC_ParameterID_113
    elif version <= 118:
        AkRTPC_ParameterID = AkRTPC_ParameterID_118
    elif version <= 134:
        AkRTPC_ParameterID = AkRTPC_ParameterID_134
    else:
        AkRTPC_ParameterID = AkRTPC_ParameterID_135

    global AkModulatorPropID
    if  version <= 145:
        AkModulatorPropID = AkModulatorPropID_112
    else:
        AkModulatorPropID = AkModulatorPropID_150

    global AkRtpcAccum
    if  version <= 125:
        AkRtpcAccum = AkRtpcAccum_125
    else:
        AkRtpcAccum = AkRtpcAccum_128

    global AkActionType
    if  version <= 56:
        AkActionType = AkActionType_056
    else:
        AkActionType = AkActionType_062

    global AkBank__AKBKSourceType
    if  version <= 89:
        AkBank__AKBKSourceType = AkBank__AKBKSourceType_088
    else:
        AkBank__AKBKSourceType = AkBank__AKBKSourceType_112

    global AkPropID
    if    version <= 62:
        AkPropID = AkPropID_062
    elif  version <= 65:
        AkPropID = AkPropID_065
    elif  version <= 89:
        AkPropID = AkPropID_088
    elif version <= 113:
        AkPropID = AkPropID_113
    elif version <= 126:
        AkPropID = AkPropID_126
    elif version <= 145:
        AkPropID = AkPropID_128
    elif version <= 150:
        AkPropID = AkPropID_150
    elif version <= 154:
        AkPropID = AkPropID_154
    else:
        AkPropID = AkPropID_168

    global AkBank__AKBKHircType
    if version <= 126:
        AkBank__AKBKHircType = AkBank__AKBKHircType_126
    else:
        AkBank__AKBKHircType = AkBank__AKBKHircType_128

    global AkBuiltInParam
    if version <= 126:
        AkBuiltInParam = AkBuiltInParam_126
    else:
        AkBuiltInParam = AkBuiltInParam_128

    global AkClipAutomationType
    if version <= 89:
        AkClipAutomationType = AkClipAutomationType_088
    else:
        AkClipAutomationType = AkClipAutomationType_112

    return
