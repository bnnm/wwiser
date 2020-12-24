# RIPPING WWISE AUDIO
The following sections explain various details of the Wwise engine and *wwiser*.


## WHAT IS WWISE AND HOW DOES IT WORK?
Very roughly, Audiokinetic Wwise is a complex audio engine with DAW-like features
that handles game audio. It integrates with standard C++ games, as well as common
game engines (Unity, Unreal Engine 4, Cocos2d, etc), through an API.

Games using Wwise can't just say *play file* `sound.wav`. Instead, one must use
their editor to make a project, import audio files, and create logical *objects*
and *events* like *PLAY_BGM01* (ID *264032621*). This "event" then may point to one
(or more) *actions*, then to an internal *sound* with parameters, that in turn
points to `sound.wav`.

The project is then compiled into one or multiple `.bnk` *Soundbanks*, and all
`.wav` are converted to `.wem` (stored inside banks, or streamed from a directory).
Finally, games must load a `.bnk` and set a call to ID *264032621* (or to string
*"PLAY_BGM01"*, internally converted to the ID) when something must happen. In-game,
the Wwise sound engine finds this ID and does whatever it's supposed to do (play
*BGM01*, in this case).

Since all audio is piped through the engine you can use the editor to define
rather complex behaviors that a game may need, for example:
- *PLAY_BGM_MAIN* that loops with loop points inside `.wem`
- *STOP_BGM_MAIN* that halts BGM_MAIN, but not other BGMs playing at the same time
- gradually change *BGM_MAIN*'s "bus" volume settings when game pauses
- *PLAY_SFX_SHOT1* that points to *sound_shot1*, in turn to `shot.wem`
- *PLAY_SFX_SHOT2* that points to *sound_shot2*, also `shot.wem`, but starts half
  into the file with higher pitch
- *PLAY_SFX_SHOT3* that calls *sound_shot1* then *sound_shot2* with some delay
- *PLAY_TITLE_VOICE*, that changes depending of the language selected
- *SET_SFX_BOMB* with certain 3D parameters, that can randomly be *sound_bomb1*
  (`bomb01.wem`) or *sound_bomb1* (`bomb02.wem`), each with random pitch,
  smoothing the sound with some curve.
- *PLAY_ACTOR_FOOTSTEP*, that varies with actor's current ground texture (an
  *actor_surface* variable must be updated by the game with value like *concrete*
  or *water*, when any actor changes steps on a different texture)
- single *PLAY_BGM* event that changes depending on a game variable, with
  *music=bgm1* plays *BGM1*, *music=bgm2* plays *BGM2*, and so on.
- play a song made of *track_bgm1_main* and *track_bgm1_loop*, both same or
  separate `.wem`, to create looping (without internal `.wem` loop points).
- set *PLAY_BGM_AMBIENT*, then layer *PLAY_BGM_BATTLE* (same duration) when game
  hits a battle and sets flag *battle_start*
- *PLAY_TONE_GENERATOR1* that plays not a `.wem`, but FX from an audio plugin that
  makes some "buzz" sound (FX plugins may be used in place of `.wem`).
- *PLAY_MIDI1* that plays not a `.wem`, but a midi
- play and loop *BGM_PART1*, then transition (on next beat) to segment *BGM_PART2*,
  when game sets a variable
- generate banks for different platforms and languages, that bundle some of the above

It's organized this way so that audio designers can create and refine events separate
from programmers, that only need to prepare hooks to those events, and Wwise does
all actual processing. This way sound can be defined by non-programmers, while game
programmers don't need to worry with audio details, just set "do something" events.
While the concept may initially seem strange, it's a solid way to handle audio for
modern games, that have thousands of sounds, dynamic music, and other complex needs.

Note that this way of indirect "event" calling is used in many other audio engines
too, like Microsoft's XACT (.xsb+.xwb), CRI's CRIWARE (`.acb+.awb`) or Firelight's
FMOD (`.fev+.fsb`). A base "cue" file (in this case `.bnk`) defines config and is
used to call waves (`.wem` here). Wwise places more emphasis in event definition
and separation of concerns, and has many features, but otherwise basic concepts are
mostly the same.


In short, because the engine is powerful and handles non-trivial audio features (that
otherwise would need lots of work to be implemented) it's used by many devs. But this
makes ripping audio from Wwise games harder, as often useful audio info (like loops)
is stored in `.bnk` rather than `.wem`, and files are named by IDs.

*wwiser* translates `.bnk` files to a format closer to what one sees in the Wwise
editor, meant to help understanding how the game is using Wwise.


## INPUT FORMAT
Wwise banks are a binary representation of project config (`.wwu`), read and
translated to C++ classes by the engine. Banks only store values, with all fields
sizes, types and names being implicit.

Some hypothetical big-endian bytes (not a real example) could be
`0x12345678000000200002000101053f800000(...)`:
```
4 bytes, uint32, object_id [0x12345678]
4 bytes, uint32, object_size [0x00000020]
4 bytes, uint32, plugin id [0x00020001]
1 byte, int8, sub-list_count [0x01]
1 byte, uint8, sub-object1_type [0x05]
4 bytes, float, sub-object1_volume [0x3f800000]
(...)
```

*wwiser* would translate this binary data creating an internal representation,
roughly:
```
object name=AkHirc size=0x20
    field name=id value=264032621 type=u32 offset=0x00
    field name=size value=0x20 type=u32 offset=0x04
    field name=plugin value=0x00020001 type=u32 offset=0x08
        field name=plugin_type value=1 type=u16 valuefmt="0x0001 [Codec Plugin]"
        field name=plugin_id value=16 type=u16 valuefmt="0x0002 [ADPCM]"
    field name=list_count value=1 type=u8 offset=0x0c
    list name=events
        object name=AkPlayEvent
            field name=type type=u8 value=5 offset=0x0d valuefmt="0x05 [Play Event]"
            field name=volume type=f32 value=1.0 offset=0x0e
            field name=unknown type=gap value=0x0e offset=0x12
(...)
```
This representation can then be parsed or printed in various ways. Do note the
order shown in the viewer or content dump is not always 1:1 vs how the banks are
stored, since a few values may need to be reordered around to make relationships
clearer (see "offset"). Also, used names may seem inconsistent, but they mainly
try to match Audiokinetic's (also inconsistent) names when possible.

Keep in mind this is just an approximation, as the Wwise engine may actually be
doing something like this (also not real):
```
public class AkHirc {
    private AkU32 id;
    //size is implicit and only used to load
    private List<AkEvent> events = new List<AkEvent>();
    private AkBool internalFlagNotInBank;
    private AkEvent *pointerAlsoNotInBank;
    ...

    public void addEvent(AkEvent event);
    ...
}

public class AkEvent {
    protected AkUniqueId targetId;
    ...
}

public class AkPlayEvent : AkEvent {
    //type only used to create the appropriate subclass
    private float volume;
    ...
}
```


## UNDERSTANDING WWISER OUTPUT
Wwise uses logical "objects" of various types that reference other objects. Some
info and useful terms can be found in their online help:
*https://www.audiokinetic.com/library/edge/?source=Help&id=glossary*

Wwise is also easy to install and play around with (if a bit buggy and crash-prone),
and has extensive documentation: *https://www.audiokinetic.com/library/edge/*,
*https://www.audiokinetic.com/courses/wwise101/*. For best results load the simple
*integration demo*, change stuff and generate banks, then open with *wwiser*.

A bank is divided in various "chunk" sections, notably:
- *BKHD*: main bank header with version and minor global config
- *HIRC*: object hierarchy, where most Wwise objects reside
- *DATA*: internal `.wem` (full in-memory files, or pre-fetch data for streaming)
- *DIDX*: media index, pointing of internal `.wem`
- *STMG/ENVS/FXPR*: global settings and objects (like volumes)

Quick rundown of common HIRC objects (also see Audiokinetic's glossary):
- *state*: changes a game variable
- *sound*: points to a `.wem` (inside bank or external) with some config
- *action*: a 'change', such as play sound, seek sound, set pitch, etc
- *event*: a sequence of actions (like stop sound, or set state then play)
- *music track*: combo of (usually trimmed) `.wem` "clips" played with some config
- *music segment*: a combo of music tracks to create a listenable chunk
- *sound/music random-sequence*: AKA *playlist*, a list played sequentially or randomly
- *sound/music switch*: plays objects depending on group+state game variables
- *bus*: common sound config (audio is routed through buses)
- *dialogue event*: an specialized event with config for dialogue
- *actor-mixer*: a logical group of sounds, used for quick config (not playable)
- *LFO/envelope/time mod*: a modificator

The overall structure is somewhat similar to a DAW (think Reaper/FL Studio/Sonar/etc)
in that defines buses to route audio, interactive tracks that mix stems, "actor
mixers" with container groups of sounds (sfx, voices), usable audio assets...

As described before, one has to create a bunch of objects (like events calling
actions that play sounds) to achieve anything in Wwise, but ultimately some `wem`
will be played with config. It's pretty flexible, so it may be easier to undertand
by thinking of Wwise as a clip player at points in a timeline. One may define these
(events ommited):
- *track00* that on 0s plays *clip00a* (`intro.wem`) for full 10s, then at 10s plays
  *clip00b* (`main.wem`) for 120s (total 130s, played -seemingly- sequentially, but
  not actually looping here).
- *segment01* that plays *track01a* with *clip01a* on 0s, and *track01b* with *clip01b*
  on 10s (total 130s, another way to simulate the above)
- *track02* that on 0.1s plays intro, then on 9s plays main (total 129.1s, intro's
  last 1s and loop's first 1s actually overlap and play at the same time, crossfading
  with pre-defined volume curves).
- *playlist03* that plays *segment02* / intro + *segment03* / main, setting main to
  loop N times (this is often used to simulate loops or make songs of dynamic stems)
- *sound04* that plays `full.wem` using defined loop points of 10s..130s (simplest
  way to loop, but less flexible for the sound designer)

All that may seem strange, but since Wwise is tuned to play many `shot.wem` during
gameplay, a bunch of extra clips used to fake loops/stems isn't too taxing. Main
difference between sounds and music tracks/segments is that the former may loop by
itself and has some pre-applied effects (better performance), while the later is played
as stems and may apply real time effects (more flexible, but needs playlists to loop).

Some objects depend on game variables, called "*game syncs*". These are defined as
*key=value*, and are either *states* (global values) or *switches* (global or per
"character"). So one can have a *music state* that plays *bgm01* when *music=act1*,
and plays *bgm02* when *music=act2*. Or multiple groups like play *bgm01_heavy* when
*music=act1* and *action=heavy*. Often, switch combos are used to avoid the need to
create one event per bgm.

Games first must load `init.bnk`, that contains global config, then one or more
`.bnk`. Sometimes there are multiple bank per level/area (BGM/VO/SFX/...) but you
can have a single bank with everything too. Bigger banks need more memory, but
can be pre-loaded once, so devs and sound designers must fine-tune this (Wwise has
profiling tools to monitor performance).

Once loaded, games may call events, or set variables. Common API calls are:
- `AK::SoundEngine::PostEvent(id/name, ...)`: fire (queue) events when needed,
  using IDs from generated constants (in `Wwise_IDs.h`), or sometimes by name.
- `AK::SoundEngine::SetSwitch/SetParam(group id/name, value id/name, ...)`: changes
  a variable. Variables can also be changed through events.
- `AK::SoundEngine::RenderAudio`: call on the main game loop to get sound.

Some API calls can be directed to a single "game object" to fine-tune emitted sounds.
The API lets you interact with some elements without using events, too: `StopAll`,
`SetRTPCValue`, `SeekOnEvent`, and so on. But main logic goes through the above.
Also see: *https://www.audiokinetic.com/library/edge/?source=SDK&id=namespaces.html*

All objects have a *ShortID* (`sid`), or may target other *ShortIDs* (`tid`). Targets
may be from other banks too (like an object in `bgm.bnk` overriding bus config from
`init.bnk`). The way objects interact follows certain rules though, common "paths":
- `event > action > sound > .wem`
- `event > action > random-sequence > sound(s) > .wem`
- `event > action > switch > switch/segment/sound > ...`
- `event > action > music segment > music track(s) > .wem(s)`.
- `event > action > music random-sequence > music segment(s) > ...`
- `event > action > music switch > switch(es)/segment(s)/random-sequence(s) > ...`

While `event > action > music track`, or `event > sound` would be impossible.
Sometimes banks contain unused objects that aren't pointed by anything (like a
`random-sequence > segment > track` without `event > action`), or objects pointing
to non-existant objects. Banks can be empty too.

With all this in mind usually we want *events* that call *play actions*, and follow
those paths to see which `.wem` are used.

Note that early Wwise files don't use `.wem` extension (which was introduced in v62+
around mid-2011) but rather `.ogg/xma/wav`, though the format itself is the same.


## WWISE FILES AND NAMES
Wwise gives a 32-bit *ShortID* to all objects and files. This means games using
it never have `sound.wem` but instead `264032621.wem` (this ID is always printed
as a regular unsigned number, not in hex format).

In the Wwise editor all objects are given readable names, but final *ShortIDs*
are generated like this:
- **SoundBanks, Events, Game Syncs**: FNV hash of the lowercase name in the editor
  (must start with letter/underscore, may contain letters, numbers and underscores).
- **Other objects** (*Actions, Sounds, Music, Bus, etc*), `.wem`: 30-bit FNV hash of the
  128-bit GUID bytes assigned by the editor.

While that's the official word, some objects like certain buses or language names
with parentheses may use the first method too. The hash algorithm is standard
FNV-1 32b and is provided by Audiokinetic in the docs. It isn't too robust, so
certain hashed names may end ip the same (like "*british*" and "*bucconidae*").
The editor warns to rename or may cause problems, so it shouldn't happen.

The above means you only get ShortIDs (numbers) references in `.bnk` and `.wem`.
But sometimes games include companion files that *wwiser* can use to get names:
- **SoundbankInfo.xml**: editor info about Wwise's generated files, mainly event
  names and `.wem` original filenames.
- **(bankname).txt**: a text file with tab-delimited fields listing IDs and
  editor names. On rare cases the list may be missing some newlines here and there,
  you may need to fix it manually.
- **Wwise_IDs.h**: C++ header with names and IDs of Wwise objects.
- **wwnames.txt**: an artificial list of possible Wwise names. Sometimes, for
  games that call events by names rather than IDs, it's possible to extract
  and create a list of strings from (decompressed) game files, with software
  like `strings2.exe` or IDA, basically getting all usable names even if the above
  files don't exist (particularly useful to get game variables or busses). You may
  need to clean up the generated list (ex. `field_bgmi` instead of `field_bgm`).
  Lines are sub-divided as needed to increase chances (ex. `name="bgm01"` will read
  `name` and `bgm01`) and invalid names are automatically ignored. Watch out for
  false positives though, since Wwise name hashing is collision-prone.
- **wwnames.db3**: an artificial, pre-generated database of possible Wwise names.
  While a game may not include any of the above, events and variables sometimes
  follow simple and common patterns, like *"music"* + *"on"*, *"play_bgm01"*, and
  so on. This database saves common names that banks may use, and is placed
  together with *wwiser*.

They'll be automatically used if found in the bank dir (except *wwnames.db3*, that
must reside in *wwiser*'s dir).

A few games may use **SoundbankInfo.json**, **(bankname).xml** and **(bankname).json**.
The editor optionally can generate those, but are less common so aren't parsed at
the moment.


## TXTP GENERATION
As explained above, Wwise has a bunch of complex features that make playing `.wem`
directly a hassle (like music segments made of multiple tracks to mimic looping).
*wwiser* can create TXTP files for *vgmstream* (*https://github.com/losnoco/vgmstream*)
to play audio simulating Wwise.

By default it will try to create .txtp for all common "usable" cases (mainly events
with audio). If the event uses variables it'll try to make one .txtp per value combo.
You can manually pass a list of variables in this format:
 `(state-key=value) [switch-key=value] ...`
Banks may also contain unused audio that can be included with an option.

*keys* and *values* can be Wwise IDs, or original text (internally converted to ID),
objects that need variables will check the passed list to decide what to generate.
Note that manual variables need to include all needed key+values, or nothing may be
created (Wwise objects may use a default value for a variable not found, but this
isn't currently simulated). Value `-` means "any", and can be used in some objects.

Some variable combos end up generating the same file (multiple paths point to the
same thing), but the generator automatically ignores repeated .txtp (same output).
It's even possible that a game has different objects that end up generating the
same result (for example cloned objects with minor parameter changes that don't
affect audio). When using manual variables you can end up with repeats though.

Files are written in a `txtp/` subfolder, and `.wem` must go to `txtp/wem/` (unless
configured). `.txtp` may reference data inside `.bnk`, so banks need to go to *wem*
subfolder too (also configurable to assume external `.wem`). You can set that all
`.wem` referenced in `.bnk` are moved automatically (`bnk` aren't moved automatically
since there are less and it's harder to test/regenerate .txtp otherwise).

Sometimes unused `.wem` (not referenced by any bank) exist, so keep an eye to move
manually. The generator may complain about missing things; this usually means that
other related banks must be loaded together. However it's not unusual that banks
have unfinished objects that don't actually play anything, or point to unused audio
(somehow `.bnk` aren't quite cleaned-up by the editor).

Given how Wwise uses events, game variables and other features, generated filename
may be a mix of parts to make full sense. For example:
- `play_bgm01.txtp`: simple event with known name (from companion files)
- `play_bgm [music=bgm01].txtp`: event that depends on one variable
- `play_bgm [music=bgm02].txtp`: same event with a different value = different song
- `play_shot01 {r}.txtp`: event with sections that randomly play one of multiple
  `.wem`, often used to select different footsteps or random music stems (first
  file in a section is pre-selected, others must manually be selected)
- `dynamic_bgm01 {s}.txtp`: song with parts that depend on states. Sometimes many
  `.wem` play at once, but are silenced/enabled using variables (you need to manually
  silence songs here).
- `play_ambience {m}.txtp`: event with sections that loop independently (like some
  short croak sfx + longer river sfx), which isn't simulated at the moment.
- `complex_bgm1 {!}.txtp`: with some kind of problem (like missing `.wem`, or
  missing features, file may play incorrectly or be unplayable)
- `BGM-0001-event.txtp`: autogenerated names for games without companion files
- `BGM-0002-event [3991942870=1784458356].txtp`: event with unknown variable names
  (can probably be reversed to actual names and re-generate, with some effort)

`.wem` filenames aren't used unless configured, since one event may use several,
and event names usually make more sense or are better ordered than filenames. Keep
in mind the generator aims to simulate the Wwise engine, that never plays `.wem`
directly.


The generator nor TXTP can't handle all Wwise features at the moment, so it's a good
idea to keep the original `.bnk`, `.wem` and companion files around just in case you
need to make .txtp again when the generator/TXTP are updated with new features.

Some list of features not simulated at the moment (also see README):
- Looping Wwise songs can randomly select values during loops (with 'weight' value),
  while .txtp must pre-select one.
- can't apply volumes (complex mix of parts that are hard to measure)
- can't apply most effects (like pitch or filters)
- fade-ins aren't handled (ex. multiple play events)
- object's values changed in real time through events (like volume) aren't applied
- object's values changed in real time through actor-mixers (a hierarchy or group of
  similar objects, like gunshots) aren't applied
- actions like setting certain switch value before playing music inside an event
  are ignored (just autosets all values for that event)
- plays switches with static values (games may change and transition dynamically)
- switch objects may define transition points (may with helper .wems) when one value
  changes to other (only generates .txtp per state without transitions)
- playlist object may define custom transition points between segments
- songs that dynamically silence songs just play all at once (crossfades with RTPCs in
  Devil May cry 5, states that set -96db volume in Metal Gear Rising, etc)
  - manually set `#@volume 0.0` to unneeded `.wem`
- sounds that don't use `.wem` but midi or a plugin (like tone generator) play silence
- multiple play actions with probability (ex. play A 100% of the time + play B 50% of
  the time) just play all actions
- overlapping clips don't apply crossfades
- generation for unusual cases may fail

.txtp duplicates are ignored, though there is an option to allow them. Mainly for
testing and uncommon cases where some ignored names are preferable to other (use
the "log" setting to check dupe relations). The option may end up creating 500% more
files, only use when needed.

Note that `.bnk` loading order matters. Two banks could contain different names but
point to the same .wem, and only the first name is created, so changing the loaded
order could (rarely) create different .txtp names.


## KNOWN ISSUES
Bank format may change a bit between major Wwise SDK versions, adding new features
or moving fields around. *wwiser* should handle almost all but there are bugs left:
- earliest versions used in *Shadowrun (X360)* and *Too Human (X360)* not supported
- parameters for many custom plugins not parsed (uncommon and time-consuming to add)
- some versions' field names and descriptions may be incorrect (missing SDKs)
- viewer doesn't work in older (IE11<) browsers
- some functions may not properly handle repeated IDs on different objects (unlikely
  and unsure how Wwise handles this)

New bank versions must be manually added, but you can skip the version check.
If you find an unsupported version, or the tool outputs "errors" (overreads)
and "skips" (underreads) please report.

Providing some missing Wwise SDKs would help development a lot: `2012.1`, `2011.3`,
lower or equal than `2009.2`. Any sub-version is ok (`2012.1.1` or `2012.1.2` work
the same).

Also, output format is not considered stable, so resulting bank representations
(xml/view/txtp) may change anytime without notice.
