# RIPPING WWISE AUDIO
The following sections explain various details of the Wwise engine and *wwiser*.


## WHAT IS WWISE AND HOW DOES IT WORK?
Very roughly, Audiokinetic Wwise is a complex audio engine with DAW-like features that handles game audio. It integrates with standard C++ games, as well as common game engines (Unity, Unreal Engine 4, Cocos2d, etc), through an API.

Games using Wwise can't just say *play file* `sound.wav`. Instead, one must use their editor to make a project, import audio files, and create logical *objects* and *events* like *PLAY_BGM01* (ID *264032621*). This "event" then may point to one (or more) *actions*, then to an internal *sound* with parameters, that in turn points to `sound.wav`.

The project is then compiled into one or multiple `.bnk` *Soundbanks*, and all `.wav` are converted to `.wem` (stored inside banks, or streamed from a directory). Finally, games must load a `.bnk` and set a call to ID *264032621* (or to string *"PLAY_BGM01"*, internally converted to the ID) when something must happen. In-game, the Wwise sound engine finds this ID and does whatever it's supposed to do (play *BGM01*, in this case).

Since all audio is piped through the engine you can use the editor to define rather complex behaviors that a game may need, for example:
- *PLAY_BGM_MAIN* that loops with loop points inside `.wem`
- *STOP_BGM_MAIN* that halts BGM_MAIN, but not other BGMs playing at the same time
- gradually change *BGM_MAIN*'s "bus" volume settings when game pauses
- *PLAY_SFX_SHOT1* that points to *sound_shot1*, in turn to `shot.wem`
- *PLAY_SFX_SHOT2* that points to *sound_shot2*, also `shot.wem`, but starts half into the file with higher pitch
- *PLAY_SFX_SHOT3* that calls *sound_shot1* then *sound_shot2* with some delay
- *PLAY_TITLE_VOICE*, that changes depending of the language selected
- *SET_SFX_BOMB* with certain 3D parameters, that can randomly be *sound_bomb1* (`bomb01.wem`) or *sound_bomb1* (`bomb02.wem`), each with random pitch, smoothing the sound with some curve.
- *PLAY_ACTOR_FOOTSTEP*, that varies with actor's current ground texture (an *actor_surface* variable must be updated by the game with value like *concrete* or *water*, when any actor changes steps on a different texture)
- single *PLAY_BGM* event that changes depending on a game variable, with *music=bgm1* plays *BGM1*, *music=bgm2* plays *BGM2*, and so on.
- play a song made of *track_bgm1_main* and *track_bgm1_loop*, both same or separate `.wem`, to create looping (without internal `.wem` loop points).
- set *PLAY_BGM_AMBIENT*, then layer *PLAY_BGM_BATTLE* (same duration) when game hits a battle and sets flag *battle_start*
- *PLAY_TONE_GENERATOR1* that plays not a `.wem`, but FX from an audio plugin that makes some "buzz" sound (FX plugins may be used in place of `.wem`).
- *PLAY_MIDI1* that plays not a `.wem`, but a midi
- play and loop *BGM_PART1*, then transition (on next beat) to segment *BGM_PART2*, when game sets a variable
- generate banks for different platforms and languages, that bundle some of the above

It's organized this way so that audio designers can create and refine events separate from programmers, that only need to prepare hooks to those events, and Wwise does all actual processing. This way sound can be defined by non-programmers, while game programmers don't need to worry with audio details, just set "do something" events when game does something. While the concept may initially seem strange, it's a solid way to handle audio for modern games, that have thousands of sounds, dynamic music, and other complex needs.

Note that this way of indirect "event" calling is used in many other audio engines too, like Microsoft's XACT (`.xsb+.xwb`), CRI's CRIWARE (`.acb+.awb`) or Firelight's FMOD (`.fev+.fsb`). A base "cue" file (in this case `.bnk`) defines config and is used to call waves (`.wem` here). Wwise places more emphasis in event definition and separation of concerns, and has many features, but otherwise basic concepts are mostly the same.

In short, because the engine is powerful and handles non-trivial audio features (that otherwise would need lots of work to be implemented) it's used by many devs. But this makes ripping audio from Wwise games harder, as often useful audio info (like loops) is stored in `.bnk` rather than `.wem`, and files are named by IDs.

*wwiser* translates `.bnk` files to a format closer to what one sees in the Wwise editor, meant to help understanding how the game is using Wwise.


## INPUT FORMAT
Wwise banks are a binary representation of project config (`.wwu`), read and translated to C++ classes by the engine. Banks only store values, with all fields sizes, types and names being implicit.

Some hypothetical big-endian bytes (not a real example) could be `0x12345678000000200002000101053f800000(...)`:
```
4 bytes, uint32, object_id [0x12345678]
4 bytes, uint32, object_size [0x00000020]
4 bytes, uint32, plugin id [0x00020001]
1 byte, int8, sub-list_count [0x01]
1 byte, uint8, sub-object1_type [0x05]
4 bytes, float, sub-object1_volume [0x3f800000]
(...)
```

*wwiser* would translate this binary data creating an internal representation, roughly:
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

This representation can then be parsed or printed in various ways. Do note the order shown in the viewer or content dump is not always 1:1 vs how the banks are stored, since a few values may need to be reordered around to make relationships clearer (see "offset"). Also, used names may seem inconsistent, but they mainly try to match Audiokinetic's (also inconsistent) names when possible.

Keep in mind this is just an approximation, as the Wwise engine may actually be doing something like this (also not real):
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

Most information in *wwiser* comes from studying Wwise SDKs and testing many games, so output should be very accurate (down to mimicking known internal class and field names).


## UNDERSTANDING WWISER OUTPUT
Wwise uses logical "objects" of various types that reference other objects. Some info and useful terms can be found in their online help:
*https://www.audiokinetic.com/library/edge/?source=Help&id=glossary*

Wwise is also easy to install and play around with, and has extensive documentation:
- *https://www.audiokinetic.com/library/edge/*
- *https://www.audiokinetic.com/courses/wwise101/*

For best results load the simple *integration demo*, change stuff and generate banks then open them with *wwiser*.

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
- *sound/music switch*: plays objects depending on group+state variables
- *bus*: common sound config (audio is routed through buses)
- *dialogue event*: an specialized event with config for dialogue
- *actor-mixer*: a logical group of sounds, used for quick config (not playable)
- *LFO/envelope/time mod*: a modificator

The overall structure is somewhat similar to a DAW (think Reaper/FL Studio/Sonar/etc) in that defines buses to route audio, interactive tracks that mix stems, "actor mixers" with container groups of sounds (sfx, voices), usable audio assets...

As described before, one has to create a bunch of objects (like events calling actions that play sounds) to achieve anything in Wwise, but ultimately some `wem` will be played with config. It's pretty flexible, so it may be easier to undertand by thinking of Wwise as a clip player at points in a timeline. One may define these (events ommited):
- *track00* that on 0s plays *clip00a* (`intro.wem`) for full 10s, then at 10s plays *clip00b* (`main.wem`) for 120s (total 130s, played -seemingly- sequentially, but not actually looping here).
- *segment01* that plays *track01a* with *clip01a* on 0s, and *track01b* with *clip01b* on 10s (total 130s, another way to simulate the above)
- *track02* that on 0.1s plays intro, then on 9s plays main (total 129.1s, intro's last 1s and loop's first 1s actually overlap and play at the same time, crossfading with pre-defined volume curves).
- *playlist03* that plays *segment02* / intro + *segment03* / main, setting main to loop N times (this is often used to simulate loops or make songs of dynamic stems)
- *sound04* that plays `full.wem` using defined loop points of 10s..130s (simplest way to loop, but less flexible for the sound designer)

All that may seem strange, but since Wwise is tuned to play many `shot.wem` during gameplay, a bunch of extra clips used to fake loops/stems isn't too taxing. Main difference between sounds and music tracks/segments is that the former may loop by itself and has some pre-applied effects (better performance), while the later is played as stems and may apply real time effects (more flexible, but needs playlists to loop).

Some objects depend on game variables, called "*game syncs*". These are defined as *key=value*, and are either *states* (global values) or *switches* (global or per "character"). So one can have a *music state* that plays *bgm01* when *music=act1*, and plays *bgm02* when *music=act2*. Or multiple groups like play *bgm01_heavy* when *music=act1* and *action=heavy*. Often, switch combos are used to avoid the need to create one event per bgm.

Games first must load `init.bnk`, that contains global config, then one or more `.bnk`. Sometimes there are multiple bank per level/area (BGM/VO/SFX/...) but you can have a single bank with everything too. Bigger banks need more memory, but can be pre-loaded once, so devs and sound designers must fine-tune this (Wwise has profiling tools to monitor performance).

Once loaded, games may call events, or set variables. Common API calls are:
- `AK::SoundEngine::PostEvent(id/name, ...)`: fire (queue) events when needed, using IDs from generated constants (in `Wwise_IDs.h`), or sometimes by name.
- `AK::SoundEngine::SetSwitch/SetParam(group id/name, value id/name, ...)`: changes a variable. Variables can also be changed through events.
- `AK::SoundEngine::RenderAudio`: call on the main game loop to get sound.

Some API calls can be directed to a single "game object" to fine-tune emitted sounds. The API lets you interact with some elements without using events, too: `StopAll`, `SetRTPCValue`, `SeekOnEvent`, and so on. But main logic goes through the above. Also see: *https://www.audiokinetic.com/library/edge/?source=SDK&id=namespaces.html*

All objects have a *ShortID* (`sid`), or may target other *ShortIDs* (`tid`). Targets may be from other banks too (like an object in `bgm.bnk` overriding bus config from `init.bnk`). The way objects interact follows certain rules though, common "paths":
- `event > action > sound > .wem`
- `event > action > random-sequence > sound(s) > .wem`
- `event > action > switch > switch/segment/sound > ...`
- `event > action > music segment > music track(s) > .wem(s)`.
- `event > action > music random-sequence > music segment(s) > ...`
- `event > action > music switch > switch(es)/segment(s)/random-sequence(s) > ...`

While `event > action > music track`, or `event > sound` would be impossible. Sometimes banks contain unused objects that aren't pointed by anything (like a `random-sequence > segment > track` without `event > action`), or objects pointing to non-existant objects. Banks can be empty too.

With all this in mind usually we want *events* that call *play actions*, and follow those paths to see which `.wem` are used.

Note that early Wwise files don't use `.wem` extension (which was introduced in v62+ around mid-2011) but rather `.ogg/xma/wav`, though the format itself is the same.


## PCK
If you have `.pck` (a Wwise virtual filesystem package) rather than `.bnk` or `.wem` you need to extract them first to use with *wwiser*.

Use this BMS script should produce accurate output:`https://raw.githubusercontent.com/bnnm/wwiser-utils/master/scripts/wwise_pck_extractor.bms


## WWISE FILES AND NAMES
Wwise gives a 32-bit *ShortID* to all objects and files. This means games using it never have `sound.wem` but instead `264032621.wem` (this ID is always printed as a regular unsigned number, not in hex format).

In the Wwise editor all objects are given readable names, but final *ShortIDs* are generated like this:
- **SoundBanks, Events, Game Syncs**: FNV hash of the lowercase name in the editor (must start with letter/underscore, may contain letters, numbers and underscores).
- **Other objects** (*Actions, Sounds, Music, Bus, etc*), `.wem`: 30-bit FNV hash of the 128-bit GUID bytes assigned by the editor.

While that's the official word, some objects like certain buses or language names with parentheses may use the first method too. The hash algorithm is standard FNV-1 32b and is provided by Audiokinetic in the docs. It isn't too robust, so certain hashed names may end ip the same (like "*british*" and "*bucconidae*"). The editor warns to rename or may cause problems, so it shouldn't happen.

The above means you only get ShortIDs (numbers) references in `.bnk` and `.wem`. But sometimes games include companion files that *wwiser* can use to get names:
- **SoundbankInfo.xml**: editor info about Wwise's generated files, mainly event names and `.wem` original filenames.
- **(bankname).txt**: a text file with tab-delimited fields listing IDs and editor names. On rare cases the list may be missing some newlines here and there, you may need to fix it manually.
- **Wwise_IDs.h**: C++ header with names and IDs of Wwise objects.
- **wwnames.txt**: an artificial list of possible Wwise names (see *reversing names* below).
- **wwnames.db3**: an artificial, pre-generated database of possible Wwise names.

While a game may not include any of the above, events and variables sometimes follow simple and common patterns, like *"music"* + *"on"*, *"play_bgm01"*, and so on. It's possible to make a manual name list, called `wwnames.txt` (see below).

A few games may use **SoundbankInfo.json**, **(bankname).xml** and **(bankname).json** (also handled here). The editor optionally can generate those, but are less common.


## NAME LIST AND REVERSING NAMES
When a game doesn't have companion `.xml` with names, you can make a name list and put it in `wwnames.txt` and *wwiser* will use it, as long as those names are actually used. For example, include the word `init` in `wwnames.txt`, and when *wwiser* finds ID *1355168291* it will print `init` nearby.

Guessing which names are actually used isn't easy, so instead sometimes it's possible to extract and create a list of strings from (decompressed) game files and executables, with software like `strings2.exe` or IDA. This often gets you many usable names even if companion files like *SoundbankInfo.xml* don't exist, or even if they do exist but some names are missing (particularly useful to get game variables).

You may need to clean up the generated list (ex. `field_bgmi` instead of `field_bgm`). *wwiser* does some processing to the list to increase chances of finding good names though (for example `name="bgm01"` will become `name` and `bgm01`), and invalid names are automatically ignored.

You can also create names from related words, like you may find `play_bgm01` and the game use that, but also may use `bgm01` (without `play_`) somewhere else, so it's worth trying variations.

Watch out for false positives though, since Wwise name hashing is very collision-prone. `init` becomes ID *1355168291*, but `hez2vro` also does.

See https://github.com/bnnm/wwiser-utils for a guide and utils to help with reversing names.

### Regenerating wwnames.txt name list with missing IDs
*wwiser* has an option to re-save names and IDs based on currently loaded banks, which can be used to get a "clean" `wwnames.txt` and get a list of used names missing IDs (see *wwiser-utils* project for tips to reverse into names those missing IDs). By default it writes an ordered list divided in sections by name type and usage.

For best results you try loading all banks before making the list, in particular `init.bnk` is needed to detect certain RTPC IDs.

### Name flags
You can add some special flags to `wwnames.txt` that alter some minor behaviors (not quite full program options). Just write the following text lines inside (flags aren't stable and may change without warning or behave erratically in some cases though).

#### `#@no-fuzzy`
Disables "fuzzy matching". By default *wwiser* tries to match derived names, like `play_bgm01` may try to use `play_bgm02`. In rare cases (mainly when there are a lot of IDs/names) it may derive names that don't make much sense, like `play_bgm0g`, so this flag disables this fuzzy derivation.

#### `#@no-save-missing`
Doesn't write missing IDs.

#### `#@no-save-companion`
Doesn't write IDs already in companion files.

#### `#@no-classify`
By default names and IDs grouped by bank, which makes it easier to check for wrong names target missing IDs, but lists are bigger and names repeated per bank. Setting this will create a simpler list.

#### `#@classify-path`
Same as default but includes banks with paths.

#### `#@hashtypes-missing <types>`
When generating a clean list (`wwiser *.bnk -sl`) all missing IDS are printed under `### MISSING (type) NAMES` headers. This option limits missing types to those in the list (mainly to target and reverse certain IDs in `words.py` companion helper script)

#### `#@repeats-update-caps`
When names in *wwnames* have repeated names (already added from bank names or .xml for example) they are ignored. With this flag wwnames overwrite previous names. This basically can be used to control caps when names/caps from `.bnk` or `Wwise_IDs.h` are unwanted.

For example, when loading a `BGM_Blah.bnk` and having `bgm_blah` in *wwnames*, *wwiser* will normally use first one (`BGM_Blah`), and with this flag set it'll use last one (`bgm_blah`).

#### `#@sort-always`
For events that change depending of parameters (`play_bgm (music=m01)`, `play_bgm (music=m02)`, etc) *wwiser* sorts the variables so `.txtp` with names come first. However some objects are pre-sorted in bnk. This flags also sorts pre-sorted names, that may result in better names.

#### `#@sort-weight (param) (weight)`
Sorting variables (see above) is done alphabetically, and "any" (`var=-`) goes first. This flag alters how sorting is done by giving `value` in `key=value` params weight (default weight is 100). Examples:
```
    group=value 10           # exact match
    group*=value* 20         # partial match
    group=- 999              # by default "any" has highest
    value 20                 # same as *=value
    * 300                    # change default weight
```

This is mainly for some games where changing order results in better `.txtp` names

** Spider-Man: Web of Shadows **
By default "-" (any) is given highest priority since most games repeat txtp (`var=-`, `var=bgm1`, `var=bgm2` may output the same). In WoS, default makes output a bit hard to follow.
``` 
mx_sym_boss                        << (music_intensity=-), not written in txtp name
mx_sym_boss (music_intensity=low)  << dupe of the above, skipped
mx_sym_boss (music_intensity=high)
mx_sym_boss (music_intensity=mid)
```

We can lower `(music_intensity=-)` priority like this:
```
#@sort-always
#@sort-weight - 999
```

Now should generate like:
```
mx_sym_boss (music_intensity=low)
mx_sym_boss (music_intensity=high)
mx_sym_boss (music_intensity=mid)
mx_sym_boss                        << dupe of low
```


** Elden Ring **
By default it generates a bunch of txtp with `FieldBoss_Lvxx` names first, then some more readable `MidBoss_(name)` names later, that are considered dupes. This reorders names a bit to prioritize MidBoss names:
```
#@sort-weight MidBoss* 10
#@sort-weight MultiHostile* 15
#@sort-weight FieldStrong* 20
#@sort-weight FieldBoss* 20
#@sort-weight c* 25
#@sort-weight * 100
```


## TXTP GENERATION
Since Wwise has a bunch of complex features that make playing `.wem` directly a hassle (like music segments made of multiple tracks to mimic looping), *wwiser* can create TXTP files for *vgmstream* (*https://github.com/vgmstream/vgmstream*) to play audio simulating Wwise. TXTP is a custom text format that tells *vgmstream* how to play audio in complex ways.

TXTP is a simple text file, so you can open it and see how audio is configured. Format is custom (see vgmstream's TXTP.md docs), but it also prints comments with extra info and a simplified tree of how Wwise plays the whole thing that may be useful to understand what's going on.

Simply load all banks (using *load dir...*), use *Generate* option and *wwiser* will make a bunch of `.txtp` files that are playable with *vgmstream*. It's recommended to load `init.bnk` (sometimes `1355168291.bnk`) to improve volume output in some cases.


### Basic output
By default it will try to create `.txtp` for all *usable* cases (mainly *events* with audio, including combos per "variables"). Pay attention to the log, as it prints about important, non obvious details you may need to tweak (detailed later).

`.txtp` are created in the `(base loaded folder)/txtp/` folder, and will need `.wem` and `.bnk`. Their location is autodetected from base folder too (`.txtp` will reference files in previous folders) but if a `.wem` is not found it'll default to `txtp/wem/`.

The more banks you load the more `.txtp` you may get, so don't be surprised if you get thousands of files. Modern games simply have *many* sounds.

#### Output folders 
When loading many `.bnk` you may get thousands of files. To manage this you can include certain variables in the *output dir*
- `{bnk}` / `{bank}`: the bank's name (translated from `(number).bnk` if possible)
- `{bnk-fn}` / `{bank-fn}`: the bank's filename (not-translated)
- `{lang}` bank's language
- `{path}` bank's subpath

For example using `txtp/{bnk}-{lang}` as the ouptput dir may create `txtp/BGM-sfx/*.txtp` and `txtp/Voices-en/*.txtp`.

Note certain options are a bit errating when using this (to be improved?).


### Output names
Given how Wwise uses events, game variables and other features, generated filename may be a mix of parts to make full sense. For example:
- `play_bgm01.txtp`: simple event with known name (from companion files)
- `play_bgm [music=bgm01].txtp`: event that depends on one variable
- `play_bgm [music=bgm02].txtp`: same event with a different value = different song
- `play_shot {r}.txtp`: event with sections that randomly play one of multiple `.wem`
- `BGM-0010-event.txtp`: autogenerated names for games without companion files with names
- `BGM-0012-event [3991942870=1784458356].txtp`: same + unknown variable names
   - can probably be reversed to get actual names

`.txtp` names are taken from *loaded banks*'s companion files if found. Load related banks (like `init.bnk`) too to ensure all needed names are loaded.

#### Name marks
Watch out for filenames with:
- `{r}`: has random parts marked like `R3>1` ("from 3 items select first")
- `{s}`: has crossfading parts marked like `##fade`
- `{m}`: uses multi-loops where multiple places set to `#@loop`
- `{e}`: uses "external IDs" set by game at runtime so can't guess file, usually voices
- `{!}`: some kind of unplayable issues (missing/unsupported audio)
- `{l=(lang)}`: when "localized" audio is found and language is selected or there are multiple language banks

*wwiser* adds those marks to tell you those files may need special care, and will be detailed below. Some optional settings also add extra marks to the name, too.


### Log and warnings
The log will output some stuff that you may need to manually tweak. Most notably are WARNINGs about missing objects.

You may get `find+load banks with events?`. Most likely the `.bnk` you loaded doesn't have events, so *wwiser* can't make `txtp`. You need to find and load other banks, that could be inside some bigfile (like `.pck` or maybe compressed engine files). If you did load some bgm-sounding bank, that may not be enough.

Typically, there is a bank per section (such as, *BGM.bnk*, *SFX.bnk* and so on), and that's enough. But sometimes games split and load multiple banks per area. For example one bank may contain common events, other with area objects (non-event) and finally a media bank (memory `.wem`). If you try to generate with only the area bank you may get nothing and a WARNING. However if only the common bank is loaded without the area objets or the media bank, you may get a few `.txtp` but also an error about missing objects.

You need to load all related banks at once then generate to ensure everything works correctly, as *wwiser* can't guess how the game loads banks (this is managed in-game). If all fails just load every bank, but that usually means tons of `.txtp` (there are filtering options, explained below).

Sometimes after loading everything you may still get WARNINGs about missing audio. First, make sure you *really* have every bank, as some games hide them inside compressed files. Then, sometimes there is no way to fix those errors and can be ignored, since a `.bnk` may simply contain garbage (Wwise does little clean-up when creating it, for some reason), though *wwiser* tries minimize those missing errors.

#### Missing memory audio
A special case is Unreal Engine 4's Wwise plugin. Often Wwise games load bnks in RAM with `.wem` inside ("memory audio", instead of loose `.wem` that are streamed audio). *wwiser* could warn about this *missing memory audio* if not found. However, recent versions of UE4+Wwise have a special "Event-Based Packaging" that creates many small .bnk with (usually) a single event, and instead puts memory/streamed/prefetch `.wem` audio in `.uasset` files. This case can't be fully detected, so those `.wem` should be extracted and used like regular `.wem`.

### TXTP errors
Sometimes when you try to open the files just won't play. *wwiser* is reasonably accurate, but typical issues are:

#### Install *vgmstream*
TXTP is a custom format tailored for *vgmstream* (a library that plays video-game music), and is a simple(-ish) text file that tells it how to play music. This means you need some form of *vgmstream* (CLI converter, *foobar2000/winamp/audacious/etc* plugin, and so on) installed.

You also need a recent version of *vgmstream*, as sometimes *wwiser*'s `.txtp` output may depend on latest features. Get *vgmstream* here: https://vgmstream.org/

#### Move wem and bnk
Each `.txtp` calls one or several audio files, in `.wem` and `.bnk`. Existing `.wem` should be autodetected from the base folder. You can open the `.txtp` file in a text editor and see what `.wem/bnk` are being used.

The output log (see above) tells you when you need to move `.bnk` or `.wem`, plus there is an option to automatically move `.wem` to output dir.

#### Missing media and features
Sometimes the .txtp is generated, but marked with a `{!}`. See below *Missing mark {!}* for an explanation on possible causes.


#### Limit file names
If the `.txtp` names are a bit too long, try moving them to a shorter dir. Windows has a path length limit, so extremely long paths (`C:\(folder)\(folder with a long name)\(more long folders)\(long name).txtp`) will fail.

*wwiser* tries to truncate files names that look too long (based on output folder), but there is also an option to make shorter names too.


### Unused audio
If log complains about unused audio there is an option to make `.txtp` for those. Set it only after trying to load other banks though, as results will be better that way. Detection depends on loaded banks, so it may classify "unused" something that is actually used in other bank. "Unused" option may end up generating nothing (leftover empty objects or dupes) though.

Sometimes unused `.wem` (not referenced by any bank) exist too, so keep an eye to move manually. It's not unusual that banks and wems have this kind of unfinished stuff.


### Unreachables
Rarely a music track may define `.wem` that it can't access. This seems possible in Wwise by making a "switch track" and defining .wem variations per state but then disabling the "switch" mode.

Currently there is no way to know this other than opening the affected `.txtp` and see if it has `#unreachable` (to be improved). It's marked to the *cleaner* option doesn't remove those `.wem`.


### Dupes and name order 
Some Wwise events and variable combos end up generating the same results, like paths point to the same thing, or simply repeated commands like `play_bgm01` and `play_bgm01_ex` that end up being the same song. *wwiser* automatically ignores duplicates.

Named events are prioritized, so `play_bgm01` (event with known name) goes before `bgm-0010-event` (unknown). In rare cases you may get worse/undesirable names, like `gallery_mode_bgm01` before `play_bgm01` (dupe). You can alter this order by setting filters (explained later). `.bnk` loading order also matters (try loading `bgm.bnk` and such first).

There is an option to allow dupes, created marked with `{d}`. Mainly useful for testing and when checking name order (use the "log" setting to check dupe relations too). This option may end up creating *tons* more files though.

Note that some events that aren't exactly the same but *very* similar (for example, sound starts with some delay) are considered dupes, but some cases do sound 100% the same yet aren't, as they are too complex to detect (see *wwiser-utils* for clean-up scripts).


### Wem extensions
Older games may use other extensions like `.wav/xma/ogg`, this is ok and taken into account.

Note that the Wwise engine automatically loads `(number).wem` (or `.ogg/wav/xma` in old versions) as needed. In rare cases devs can feed `(name).wem` manually (called an *external*), but note the extension is always enforced (as confirmed by official docs). Thus, *wwiser* only uses `.wem/ogg/wav/xma`.


### Missing features
The generator, vgmstream, and TXTP can't handle all Wwise features at the moment, so it's a good idea to keep the original `.bnk`, `.wem` and companion files around just in case you need to make `.txtp` again when TXTP are updated with new features.

Main Wwise features missing are:
- overlaps: when a songs changes section or loops, Wwise allows to play "post-exit" and "pre-entry" audio simultaneously, but `.txtp` just ignores those for now, making some transitions sound less smooth
- different sample rates: Wwise can freely combine sample rates, but vgmstream needs to be updated to support this (some parts of the song will sound too fast)
- switch transitions: songs can dynamically change sections in real time via passed parameters in Wwise, but the generator only uses pre-set parameters (no real time editing)
- transition objects: switches may define transition `.wem` when one value changes to other (generates separate `.txtp` per transitions)
- auto parameters: generator automatically makes combinations of parameters to create most possible songs, but some combos that play multiple songs simultaneously aren't created at the moment (made as separate songs, can be created by passing all parameters manually).
- songs with random files/variations: selected from a list and may change dynamically in Wwise (like on every loop), can only play pre-selected values (configurable/editable).
- multi-loops: Wwise can loop each element independently (since it's just "repeating" parts rather than "looping"), but .txtp doesn't (can be manually simulated).
- effects: Wwise can apply effects like pitch, panning, filters and so on, none are simulated
- plugins: Wwise can alter output (including volume) from multiple bank parameters, not simulated either
- special audio: songs with unusual features like midis/tone generator plugins can't play (too complex)
- crossfades: Wwise games sometimes silence or crossfade files while playing the rest (configurable)

Other limitations:
- object's values changed in real time through events (like volume) only apply certain cases (configurable)
- actions like setting certain switch value before playing music inside an event are ignored (just autosets all values for that event)
- multiple play actions with probability (ex. play A 100% of the time + play B 50% of the time) just play all actions


### Random mark {r}
Events may play "random" parts. This usually means different footsteps, or random music stems (such as an "intro" and "outro" section) that change every time the game plays them.

vgmstream can't quite simulate those, so currently *wwiser* just writes the random list and selects first one. For example written as `-R3>1`, meaning "from the previous 3 random parts, select first". You can edit that and write `-R3>2` to manually select 2nd, and so on.

There is an option to make `.txtp` per "base" group. This works for simple, single randoms (will make `name {r1}`, `name {r2}`...), but not if the file has many random parts, or mixed more unusually.


### Crossfade mark {s}
In some cases parts of the song silence or change volume based on a in-game variable (gamevar). By default all plays at default volume (may play incorrectly all at once), but you can pass multiple "gamevars" values, as `key=value`. For example `bgm_srank_param=0.0` would silence some beat layer, while `4.0` will start to add it, and `7.0` would peak. This is described later detail in the "passing variables" section.

Inside the `.txtp` crossfade parts are marked with `##fade` near `.wem`, and gamevar info is down in the comment tree. You can also silence those by put `?` in front of `.wem`, or `#v 0` before `##fade`.


### Statechunk mark {s}
In rare cases `{s}` means the volume is altered/silenced via states, which should be handled automatically by making one `.txtp` per state that changes volumes, to a point.

Sometimes default `.txtp` marked with `{s}` and without state applied is also meant to be playable. For example a game may define a base song that plays all, then silence some audio layer with one state don't need to be touched. However other games may not need this and default  `.txtp` playing all at once makes no sense. *wwiser* can't autodetect all invalid cases so you can pass a flag to skip those defaults (or just remove the offending `.txtp`).

 *wwiser* doesn't mark certain possible `{s}` combos that may be useful to make. Some games use tons of those states that end up altering audio in the same way: `bgm_cutscene`, `scene_intro`, `in_menu`, `bus_fader`, `bgm_layer` and so on all could apply silence on different *audio objects*, with end result often being the same. `bgm_layer=mid/low` variations could be useful to generate in this case, but it's hard to autodetect it. Check the "passing variables" section for tips to handle these cases.


### Multi-loops mark {m}
In Wwise multiple parts may loop  independently (like some short croak sfx + longer river sfx), which isn't simulated at the moment. You can edit and extend `#B` times near `#@loop` manually to simulate them, though.


### Missing mark {!}
This indicates some kind of problem. Typically missing memory bank (try loading more banks first), or an unsupported Wwise feature.

Missing memory bank means the needed `.wem` are inside a bank, but you haven't loaded such bank. *wwiser* can detect this but doesn't know which bank would have those thems. Simply find and load those missing banks and the `{!}` should disappear.

Unsupported features are usually programatically generated audio (such as a sine wave, a "whoosh" wind sfx, and so on), or Wwise midi (that is mostly silent and used for syncronization rather than sound). Those will play as silence (parts are marked as `?`) rather than failing, since often it doesn't matter much.

If the `.txtp` includes a huge number of sounds it may also be marked, as *vgmstream* currently has some max limits. Open the `.txtp` with a text editor, and if you see a long list of `.wem` this may be the culprit. This needs to be fixed in *vgmstream*, but is currently a bit complex to do so. You can also edit the `.txtp` so it doesn't reach those limits (see vgmstream's TXTP docs, but basically you need to comment a bunch of wems and tweak groups' totals).


### External mark {e}
Normally Wwise plays ID *123456789* by loading `123456789.wem`. There is an special *external ID* (called "cookie") feature that allows programmer to manually map cookie ID *123456789* to file `tape01.wem`. This is (rarely) used to have a single *event* play different `wem` configured by the programmers in code (rather than using events/states).

You can simulate this and create files per external by making an `externals.txt` list (put it with the banks). Normally *wwise* creates `play_char01 {e}` and such events with externals. Open the file and find the external ID printed inside as `##external (number) ...`.

Take those IDs and in `externals.txt` , write a *cookie ID* followed by N lines pointing to files, per ID:

```
123456789
vo/vo_char01_001.wem
vo/vo_char01_002.wem
vo/vo_char01_003.wem

234567890
vo/vo_char02_001.wem
vo/vo_char02_002.wem
vo/vo_char02_003.wem

...
```

Then when generating again it should create `play_char01 {e=vo_char01_001}` `play_char01 {e=vo_char01_002}` and so on.


### File limits and tags
Because `.txtp` names are a mix of things that simulate Wwise state (such as multiple variables), filenames can be too long for Windows/Linux to handle. In those cases files will be trimmed, but you can set an option to print the full name in `!tags.m3u` (a tag list for *vgmstream*). There is an option to pass "renames" too.

Somewhat related, inside *SoundbanksInfo.xml* you may find the original `.wem` names. You can set an option to attach 
`.wem` filenames to the `txtp`, but since Wwise may play many `wem` at once this tends to be rather useless (creates gigantic filenames). *wwiser* also needs the original ID filename (not renamed) to locate `wem`. Instead, you can set an option to make `!tags.m3u` for original `.wem` files.


### Passing volumes
Because volumes in Wwise are a complex mix of external and internal settings, default generated volume may be a bit low. You can change it by setting the "master volume" option. For example `6.0dB` to double volume, or `50%` to halve it.

Set `*` instead to auto-normalize volume (default). This will increase or decrease overall volume per file, trying to keep it as close as base volume. Or, set `0` to leave volumes as originally set in Wwise. Normalizing also helps to ignore dupe events that are the same but just change volume slightly (like `play_bgm (bgm=standard)`, `play_bgm (bgm=quiet)`), so disabling it may also get some more dupe events.


### Passing variables
By default *wwiser* makes combinations of events and variables to get as many useful `.txtp` as possible. This simulates how a game would change Wwise's internal state to get various sounds.

Because the tool can only guess so much, in some cases you need to pass internal state manually to improve output (mainly for txtp marked with `{s}`, see above), in the form of lists of `key=value`.

#### Types
There are three lists that can be modified, for each type of internal state:
- gamesyncs: *state* and *switch* "paths" that change which song plays
  - Default: tries all possible combinations (skips a few that are unlikely to happen)
  - example: `(bgm_song=music_field) [bgm_vocal=off]` = plays field music without vocals
- statechunks: *states* that apply properties (like different volumes per state)
  - Default: tries combos for typical audio types (skips others that often silence the whole song, but a few may be useful)
  - example: `(bgm_layer=low)` = silences one layer when set
- gamevars: *game parameter* values that alter some part of the song (also usually volumes)
  - Default: does nothing (hard to decide on useful combos)
  - example: `{current_hp=30.0}` = lowers volume and a filter when HP is low

Each game uses these differently, so there is no standard way to handle. Technically statechunks and gamesync's states are the same thing, but are kept separate here for flexibility.

#### Format
List format is: `(state-key=value) [switch-key=value] {gamevar-key=value}`, where `(..)`=state, `[..]`=switch, `{..}`=gamevar. You don't need to include `()` in the statechunk list or `{}` in the gamevar list though, it's just for consistency. Spaces are optional too (`(state=value)[switch=value]` is ok). "Default" is the behavior when nothing is passed.

*keys* can be Wwise numbers (short IDs) or original text (internally converted to ID). *values* in states and switches work like that too, while gamevars need a decimal value (range depends on the gamevar). Example: `bgm=field` or `412724365=514358619` are the same.

You can pass multiple lists by separating with a `/`, or separate values with `,` for a similar effect:
- `(bgm_song=music_field) [bgm_vocal=off] / (bgm_song=music_field) [bgm_vocal=on]`: makes 2 txtp for field, with and without vocals
- `(bgm_layer=low,mid)`: same as `(bgm_layer=low) / (bgm_layer=mid)`, makes 2 txtp for each layer type

There are some special values:
- `state/switch=-`: "any", can be used in some paths (gamesyncs only, in statechunk "any" has no meaning)
- `gamevar=-`: default value if defined and loaded (usually in init.bnk), otherwise ignored
- `gamevar=min/max`: auto sets min/max values
- `*=(value)`: sets all gamevars to that (`{*=min}` to change all at once)
- `gamevar=(huge number)`: auto clamped to min/max values

#### Tips
If you open any generated `.txtp` with a text editor, you can see some extra info at the bottom that tells you about possible variables:
```
123456789.wem #i

# AUTOGENERATED WITH WWISER v20220416
#
# (full txtp name)
# * gamesyncs: (used gamesyncs)
# * statechunks: (used statechunks)
# * gamevars: (used gamevas)
#
# PATH
# (generated Wwise object following the gamesync path)
#
# STATECHUNKS
# (list of possible statechunks)
#
# GAMEVARS
# (list of possible gamevars)
```
Use that info as a base for your lists.

When passing variables beware of:
- passing incomplete gamesyncs paths may result in nothing playing (`[bgm_vocal=off]` only may not be enough)
- repeated variables uses last one's value
- vars that don't apply may be ignored (passing `{_dummy=1.0}` is ok but affects nothing)
- passing many values with commas may result in lots of `.txtp` (`(bgm=a,b,c) (layer=e,f)` is multiplicative and creates 6 lists)
- passing many lists may increase dupes (*wwiser* just tries to generate with each list set, that may make the same things)

### Passing filters
By default *wwiser* generates all `.txtp` that are considered "usable". This mainly means events, prioritizing those with known names. You can use a list of "filters" to alter this, passing multiple `(filter) (filter) ...` to generate only certain *Wwise objects*.

Filter types:
- `(number)`: by object ID (event, or any kind of usable part)
- `(classname)`: by object class (any kind of usable part)
- `(name)`: by object event name (wildcards are allowed)
- `(bankname).bnk`: by bank name
- `(bankname)-(index)`: by object index/position in bank

Filter prefixes:
- (no prefix): affect "outer" objects
- `@`: affect "inner" nodes (part of an "outer" object")
  - may use text to filter source nodes by guidname (since they don't have hashname)
- `~`: affect "unused" nodes (any objects not referenced)
- `/` or `-`: exclude (`/` is needed for the command line)

Examples:
- `123456`: make only object with that ID (could be an ID of an *event*, or "music segment" and similar objects)
- `CAkMusicSegment`: .txtp only from "music segment" objects
- `play_bgm_001`: only event .txtp that are named like that
- `music.bnk`: only event .txtp in said bank
- `music-1234`: create object number 1234 from `music` bank
- `play_bgm_*`: only event .txtp that start with `play_bgm_`
- `/play_sfx_*`: same, alt since command line gets confused by `-`
- `@/12345`: exclude sub-node used inside generated objects (filters txtp parts)
- `@12345`: not working (in effect would filter everything)
- `@*bgm*`: include nodes that have "bgm" in their guidname
- `@/*bgm*`: extclude nodes that have "bgm" in their guidname
- `~12345`: include unused node (when filtering nodes)
- `~/12345`: exclude unused node (use only when using *Skip normal*, otherwise gets odd results)

Some tricks you can do with filters:
- Testing: if you have a big `.txtp` with lots of groups, you can pass a single ID and output just the part you want.
- Ignore sfx: maybe you have `common.bnk` with lots of sfx but a handful of jingles. Pass `jingle_*` (if named) or an event ID list to only read those while ignoring other sfx events, or pass `/play_sfx_*` to ignore SFX directly (if you have names).
- Load many banks: sometimes games separate and load `.bnk` in non-obvious ways. You could just load everything then filter by `music.bnk` to get music but ensure all needed banks are there (ignoring sfx or voice banks).
- Skip layered sounds, like SFX noise pasted on top of music, using sub-node filters
- Alter `.txtp` order: set *generate rest* and apply filters to force filtered names to generate first (alters detected dupes)

*Generate rest* option is useful to alter name order. Some games have several events that do the same thing, for example `jukebox01` then `music01_fields` (dupe). The later, being a dupe, would be ignored but the name is more descriptive and preferable. To fix this, you can filter by `music*` *and* pass the option to *"generate rest of files after filtering"*. This reorders so `music01_fields` goes first, then `jukebox01` (now a dupe = ignored).

When using the "generate unused" option and filtering nodes, by default no "unused" nodes are created for technical reasons (everything that didn't make it into a `.txtp` is considered unused, including anything filtered). You can manually include unused objects by including "unused" filters with a `~` prefixes.

You can set *Skip normal* to ignore all regular (non-unused) `.txtp`. It's a bit special in that everything is generated but simply not written, so totals reflect this. This allows to write unused only, and also apply "exclude unused" filters.


### Passing renames
Games with many variables may end up generating `.txtp` with *very* long filenames. Often those variables aren't related to music, or could be shortened and still make sense. For those cases you can tell *wwiser* how to rename parts of the `.txtp`, in the form of `text-in:text-out`.

For example with:
- `play_bgm (ST_PLAYERSTATE=ST_PLAYER_ALIVE) (ST_READY=ST_READY_ON) (ST_MISSION_STATE=ST_M01)`
- `play_bgm (ST_PLAYERSTATE=ST_PLAYER_DEAD) (ST_READY=ST_READY_OFF)`

And these renames (note that order matters):
- `(ST_PLAYERSTATE=ST_PLAYER_ALIVE):`
- `ST_PLAYERSTATE=:PLAYER=`
- `(ST_READY=*):`
- `ST_MISSION_STATE=:MISSION`
- `ST_:`
- `ST_(.+)_MISSION:ST_MISSION` #regex (detected by use of +*^$.)

You would get:
- `play_bgm (MISSION=M01)`
- `play_bgm (PLAYER=PLAYER_DEAD)`

While you can mutate anything to anything, I recommend shortening but respecting the original naming style (mainly removing superflous stems and useless states, avoiding making up text). If *really* want to make up names, like changing `123456789` to `BGM01` (*not recommended*), try adding some identifiable mark like `#` (`#BGM01`), as original Wwise names can't use `#`.

As a "quick delete" hack, if a `text-out` is `<skip>` (such as `ST_SILENT=:<skip>`), any `.txtp` matching that rename will not be written out.


## ENCRYPTED BNK HEADERS
In very rare cases `.bnk` headers are slightly encrypted, meaning *wwiser* can't handle them as-is and will throw an error like `encrypted bank version (needs xorpad.bin)`. You can supply *wwiser* a decryption key named `xorpad.bin` (put near the `bnk`). Fortunately the encrypted part is very simple and easy enough to figure out by inspection (for known games, at least) if you have some basic understanding of hex editting and xor operations.

This encryption seems to be an optional but rarely used feature of Wwise, and can be seen by decompiling and looking at parts that initialize and read `BKHD`. It's not a key over data but xor'ing applied field by field in the init code.

Example from Limbo's Wwise demo: 
- `424B4844 34000000 2144985C DCF3835F 02CBF4DE B724A036` (encrypted header)
- `00000000 00000000 B144985C 7065B909 3C9684C9 A724A036` (`xorpad.bin` key)
- `424B4844 34000000 90000000 AC963A56 3E5D7017 10000000` (result of xor'ing both)

Resulting encrypted fields are:
- `424B4844`: `dwTag`, always `BKHD`. Not encrypted so key has 0s
- `34000000`: `dwChunkSize` (little endian on PC), also not encrypted
- `90000000`: `dwBankGeneratorVersion`, only field actually needed by *wwiser*. Its value can be guessed by knowing the release date (see `wdefs.py` for Wwise version <> bank version), and just trying to read the `.bnk` with different versions until *wwiser* stops throwing errors
- `AC963A56`: `dwSoundBankID`, bank's hash. Not important but can be derived from its name: if you have `l_testbank.bnk`, `fnv.exe -n l_testbank` gives 1446680236 / 0x563a96ac (see wwiser-utils for `fnv.exe`)
- `3E5D7017`: `dwLanguageID`, in this case hash of `SFX` (most common, `Engligh(US)` is also common)
- `10000000`: `dwProjectID`, a reference ID.

Since only the bank version is needed, you can use `00000000 00000000 XXXXXXXX 00000000 00000000 00000000` and tweak XXXXXXXX so it results in some sensical values, until it works. Technically more fields could be encrypted so `xorpad.bin` may need to be bigger though.

Note that devs could instead encrypt the whole `.bnk` using standard encryption like AES, this is unrelated to Wwise and not covered by this program.

## LOADING REPEATED BANKS
By default *wwiser* allows loading the same bank ID+lang in different dirs multiple times, or the same bank in the same dir with different names (same bank in the same dir is ignored). Real *Wwise* games probably don't do that, plus the engine should ignore repeated IDs, but *wwiser* has some leniency for usability or odd games.

The most notable case is game updates, where newer `.bnk` may be put in a separate dir or `.pck`. Manually loading newer banks is time consuming, so when loading multiple dirs *wwiser* just accepts everything. This works fine when dumping contents or wwnames (dupes are taken into account), but affects TXTP generation.

Repeated banks may have the same IDs but different contents. For example a *music-switch* object in v1.0 may have 10 cases (10 `.txtp`), while v1.1 has 12 cases (12 `.txtp`), but the other way around could be possible. *wwiser* can only use either v1.0 or v1.1, but can't guess which *music-switch* is the newer/better one.

By default it favors bigger banks first (usually v1.1) while still allowing both. This can be overridden to ignore repeated banks (first only, last only, biggest, etc) for fine tuning. In comple cases you may need to experiment and see if other mores make more `.txtp`. There is nothing stopping tricky devs of reusing a bank ID with completely different contents though, so use with care.


## KNOWN ISSUES
Bank format may change a bit between major Wwise SDK versions, adding new features or moving fields around. *wwiser* should handle almost all but there are bugs left:
- earliest versions used in *Shadowrun (X360)* and *Too Human (X360)* partially supported
- parameters for custom plugins not always parsed (uncommon and time-consuming to add)
- some versions' field names and descriptions may be incorrect (missing SDKs)
- viewer doesn't work in older (IE11<) browsers
- some functions may not properly handle repeated IDs on different objects (unlikely and unsure how Wwise handles this)

New bank versions must be manually added. If you find an unsupported version, or the tool outputs "errors" (overreads) and "skips" (underreads) please report.

Providing some missing Wwise SDKs would help development a lot: `2012.1`, `2011.3`, lower or equal than `2009.2`. Any sub-version is ok (`2012.1.1` or `2012.1.2` work the same).

Also, output format is not considered stable, so resulting bank representations (xml/view/txtp) may change anytime without notice.
