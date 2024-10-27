# WWISE EDITOR NOTES

Info gathered from the editor, to help understanding model and overall behavior.


**recheck**
- ! multiple events with same ID are possible (editor gives "same id, may 
  have trouble to play", ex "british" + "bucconidae"), how to handle?
- music switch can have multiple playlist playing at the same time?
- pStateChunks for switching + syncs? (may be set as default?)

## sections and hierarchies
- editor divides information into:
  - audio devices: audio bus can be routed to these (standard output, no output, controller audio, etc)
  - master-mixer hierarchy: buses go here
  - action-mixer hierarchy: "sound module" objects go here (actor-mixers, akswitch, aksound, etc)
  - interactive music hierarchy: "music module" objects go here (musicswith, musicsegment, etc)
  - events/dynamic dialogue: actions go here (play x, seek x)
  - game syncs: definitions of states/switches/game parameters/triggers go here
  - share sets: other odd objects go here (effects, attenuations, modulations, etc)
  - soundbanks: definitions of which objects go which banks go here (by default all)
- playable sound/music objects apply config from its own hierarchy
- playable audio objects go through 1 main bus or N aux-bus, applying certain params and config from that hierarchy
- hierarchies are just a way to organize objects; playable objects don't depend on this
  - event > aksound is possible, even if aksound if children of other object or is at the top of the hierarchy
- within each hierarchy objects can be children of certain objects, or reside on top:
  - sound: actor-mixer, switch, layer, ranseq, sfx/voice
    - all can be on top
    - actor-mixer can contain any (including actor-mixers)
    - switch/layer/ranseq can contain each other, or sfx/voice
    - sfx/voice has no children
  - music: musicswitch, musicranseq, musicsegment, musictrack
    - musicswitch, musicranseq, musicsegment can be on top
    - musicswitch can contain musicswitch, musicranseq, musicsegment
    - musicranseq can contain musicsegment
    - musictrack must be children of musicsegment

## files
- you can import audio (.wav) into a project and use freely as is
- by default uses .wav, but can be converted to .wem ("convert all audio files" in project menu)
  - objects with non-converted audio have blue names
- .wem are given same name as .wav + some ID
  - ID seems to be some kind of salted CRC, and not a GUID/ShortID, as same .wav renamed can be
    imported multiple times, and gets a different ID sometimes, but also may use an old one.
  - `Drum_D79FB2B7.wem`, `Drum2_10C4C929.wem`, `drum_a_10C4C929.wem`, `drum_b_10C4C929.wem`, `drum_c_D79FB2B7.wem`


## gamesyncs
- "switches", "states", in key=value format
- there is also "game parameters" (have RTPC config) and "triggers" (no config)
- defined in actor mixer hierarchy or "game syncs"
- sets a default value
  - if objects uses a regular value and it's deleted, all objects remove associations or point to default
- values are global for all banks and can't repeat names under same category
  - switch "music" and state "music" can be created, but 2 states "music" cannot
  - value names can be repeated
- gamesyncs can be organized in 'subfolders', but this isn't reflected in .bnk
- .bnk doesn't normally save a list of gamesyncs (but found in init.bnk in earlier versions)?
- differences:
  - states: global (same for all objects), may associate parameters to states (like, state sets volume to -10), may change over time
  - switches: local (switch states per gameObject), no parameters, immediate changes
- switches can be changed with:
  - AK::SoundEngine::SetSwitch(group, value, gameObject)
  - SetSwitch event
  - RTPCs (map value to switch, like 0 = stealth, 1 = action)
- if an event is triggered by a gameObject, it uses that object's current switches + global states


## events/actions/etc
- ids can small numbers like "40"
- single event can play multiple actions, simultaneously
- play actions have a probability to play (100=play, 50%=may or not play, even a single action)
- play actions may set a delay time
- play actions enter with a fade-in curve, defaults to linear and must define "fade time" to be used
  - values saved in ActionInitialValues/prop bundle with "DelayTime", "TransitionTime", "Probability"
  - curve saved as "PlayActionParams" 
- type "post event" may be used as "play" for event (simultaneous, also with delay)
- type resume may not be used to play a non-paused file
- some events change other object's config (pitch, volume, etc)
- trigger actions play stingers

## sounds
- adds a .wav source as a sfx, then can be adjusted
- may leave "wav loop points" (default) or override and use "project loop points"
  - double clip on sfx source to adjust config
- may set loop flag, sets "loop" prop
  - 0=infinite, 2+=loop N times, 1=loop flag not set (play 1 time)
  - if set to loop but file has no loop points it just repeats
- when overriding loops may set loop start/end as a value or dragging marker 
  - loop end defaults to audio end
  - creates standard "smpl" chunk (only if loop flag is enabled)
- audio can be trimmed by dragging left/right corners, and other changes (fades/etc)
  - this seems to just pre-trim the final .wem (not in real-time)

## voices
- a special type of sound, same but may define a wav/file per language
  - internally it's still a sound, with "bIsLanguageSpecific" flag set
- when making .bnk it creates one per language (not possible to have one with multiple languages)
- adding one voice automatically makes that bank a language bnk
- if a voice is only defined for one language, other languages use it as-is
- languages are added in the project "language" config
- languages may be named freely (no need to follow standard), name is hashed

## music tracks
- tracks can be empty (no sources but saved on segment / bnk), usable as silence
- adds N .wav as a clip, then can be adjusted
  - on explorer, right click over track > import 
- all clips are always played
- clips become AkTrackSrcInfo that may point to the same AkBankSourceData
- may define N sources aka clips
  - if files overlap there is curve mixing is auto added (can be changed)
    - added as 2 AkClipAutomation: fadeout (3 points) + fadein (2 points)
  - if files don't overlap they can be considered segmented with padding in between
- clips may have different number of channels in the same track 
  - presumably auto upmixed to highest
- clips can be moved in the track lane (can't go before 0s, can go forward to any point)
  - final duration is loosely defined by clips+segment, see below
- clips can be dragged in left/right corners to alter audio:
  - left forward >> or right backwards << to trim beginning or end audio
  - left backward << or right forward >> (past audio) to trigger a "repeated part"
  - "repeated part" is part of the end, ex. [..end|start.. clip ..end|start..]
- repeated parts begin from actual audio start, not trimmed clip start
- repeated parts may over many loops, but have delimited ends (not actually looping forever)
- repeated parts can only do beginning to end, original loop points seem ignored
- can't move or add a repeat part before 0 (must move forward first)
- adding "repeated parts" sets loop flag = 0 (infinite)
  - technically it's a looped file with altered begin/end
- editor has snap points and modes (seconds/beats/etc) for easy dragging, but no particular effect in bank
- final clip duration is calculated with 4 values
  - fSrcDuration: original/real audio duration, used as a base for next values
  - fPlayAt: >0 puts clip forward in the track lane, <0 same but needs trims (see below)
  - fBeginTrimOffset: >0 removes audio from beginning, <0 adds "repeated part" of audio end to beginning
  - fEndTrimOffset: <0 removes audio from end, >0 adds "repeated part" of audio beginning to end
- clip values are reassigned in non-obvious ways when moving clips past certain thresholds
  * move clip to 2s > PA=2s, BTO=0s, ETO=0s
  * trim begin 1s > PA=2s, BTO=1s, ETO=0s (audio starts at 2+1=3s)
  * trim end 1s > PA=2s, BTO=1s, ETO=-1s (audio starts at 2+1=3s)
  * move clip to 0s > PA=-1s, BTO=1s, ETO=-1s (audio starts at -1+1=0s)
    * moves audio actual start to -1s THEN trims 1s, so aligned trimmed start is 0
  * restart clip (PA=0s, BTO=0s, ETO=0s)
  * add repeat end 1s > PA=0s, BTO=0s, ETO=1s
  * move 2s > PA=2s, BTO=0s, ETO=1s
  * add repeat begin 1s > PA=2s, BTO=-1s, ETO=1s (audio starts at 2-1=1s)
  * move clip to 0 > PA=1s, BTO=-1s, ETO=1s
    * can't move a clip before 0
  * restart clip (PA=0s, BTO=0s, ETO=0s)
  * move clip 7s (past ~5s of audio fSrcDuration) > PA=7s, BTO=0s, ETO=0s
  * add repeat begin 6s (so it loops 2+ times and clip lasts 6+5s) > PA=7s, BTO=-6s, ETO=0s
  * trim end 10s (so it removes ~2 times leaving ~1s) > PA=7s, BTO=6s, ETO=-10s
- track may set subtracks except on normal mode, must have 1
  - in bnk "numSubTrack" becomes N
- subtracks are just normal tracks, with its own clips
  - in bnk, all clips are saved as AkTrackSrcInfo, with trackID setting subtrack number
  - subtrack may be empty with no associated clips (but still used as reference)
- tracks have a mode that affect how subtracks are used
- modes work like this
  - normal: plays single subtrack normally (removes other subtracks if selected)
  - random step: plays random subtrack, on next call plays another (cannot loop) 
  - sequence step: plays first subtrack, on next call plays next (cannot loop)
  - switch: plays subtracks (probably multiple at the same time) associated to switches
- final segment duration is changed to last clip of all subtracks
  - so playing one random with a last clip ending earlier plays silence until segment end
- tracks may define calls to events, that work like simple clips with fPlayAt and no trims/duration
  - saved as a special AkTrackSrcInfo, with sourceID=0, eventID=(sid of CAkEvent)

## segments
- may define N tracks (plays all tracks with their clips at the same time)
- may define N markers, at least start/end (can't be deleted), set to some fPosition
- segments can be empty (no tracks), plays silence until end marker
- new markers don't seem to be saved unless used?
- markers aren't autoadjusted, must be dragged/snapped manually
- moving start marker forward moves sound start (can't move 0)
  - internally just adjusts all time positions
  - moving start to 100s, fPosition becomes 100s and clips move +100s, so in effect start is always 0
- moving end marker has no particular effect other than affecting final duration (see below)
- segment fDuration is set to:
  - end marker position when it's after last clip position
  - last clip end when end marker is earlier than that
    - last clip end among all tracks in that segment
  - can't have end marker less than last clip and duration bigger than last clip
- segment plays full fDuration, having silence in parts without clips
- end markers are used in playlists to signal when to jump next, but may keep playing for fDuration
- may not loop by itself, must use playlists (per docs)
- may set stingers that transition and play other segments (used by trigger action)
- order of tracks (and clips) is as defined in editor (not reordered), no particular effect
- adding multiple tracks doesn't add crossfades (unlike clips)

## playlist container (musicranseq)
- adds objects to playlist, but not used until added to a "group"
  - objects may be segments/playlists/switches?
  - AkMusicRanSeq saves the segments in children list, but aren't in the playlist
- plays a list of objects inside a group (only segments)
  - there is a special "event track" that technically plays anything, but it's handled differently
- defines groups with modes that change when track is played
  - sequence continuous: plays all objects in sequence, on loop/next call restarts
  - sequence step: plays one object from first, on loop/next call plays next object
  - random continuous: plays all objects randomly, on loop/next call restarts
  - random step: plays one object at random, on loop/next call plays another object
  - loop above means set on playlist/group level (loop on children level "traps" the sequence)
- groups may have segments or other groups (with objects), at any position
- random types have weight (probability to play), from 0.001 to 100% (default 50)
- random types can use "standard"=allows repeats, or "shuffle"= doesn't
- random types can set "avoid repeat N" to affect which objects are picked on loops/next play
- each "group" has N segments
- group and objects have loop settings (1=once/none, 0=infinite, N=loops)
  - loop meaning varies per mode
- combining all object stems + loops created a whole song
- playlist next segments starts after reaching end marker (default), configurable to others
  - prev segment audio still plays for its fDuration (possibly layered)
- loop/play example with group with objects A B (C):
  - sequence continuous:
    - loop group=2, A=1, B=1: plays A B A B
    - loop group=1, A=2, B=1: plays A A B
    - loop group=1, A=0, B=2: plays A A A A A ...
  - sequence step:
    - loop group=1, A=1, B=1: plays A, next time (like re-triggering 10s later) plays B
    - loop group=1, A=2, B=1: plays A A, next time B
    - loop group=3, A=2, B=1: plays A A B A A, next time B A A B
  * if groups have groups they are used just like A/B, but only if they have objects
  - random continuous
    - loop group=-, A=1, B=1, C=1 (standard): plays A C A B, next time/loop plays C C A B
    - loop group=-, A=1, B=1, C=1 (shuffle):  plays A C B, next time/loop plays C A B
    - loop group=-, A=2, B=1, C=1 (standard): plays B C B A A, next time/loop plays A A A A C C B
    - loop group=-, A=2, B=1, C=1 (standard): plays B C A A, next time/loop plays A A C B
  - random step 
    - loop group=2, A=1, B=1, C=1 (standard): plays B, next time OR looping plays A
    - loop group=6, A=1, B=1, C=1 (standard): plays A, A, C, A, C, C
    - loop group=6, A=1, B=1, C=1 (shuffle):  plays B, A, C, (shuffle done), C, A, B
- segment/tracks with playevents are handled like a newly layered bgm outside current playlist
  - loop group=-, A=1 (event), B=1: plays A (layers some event), on exit cue plays B
    - if event is looped it keeps playing in the background regardless of playlist (even after playlist ends)
  - loop group=-, A=2 (event), B=1: plays A (layers some event), plays A (layers some event again), plays B
    - 2 layers going on at the same time, plus the main playlist continues normally
  - track's playevent can't be an event that has a track with playevent (no self/circular refs)

## music switch container
- sets group+variable(s) to select one object depending
  - ex: music=exploring > bgm01
- groups can be states or switches
- groups of the same type can't repeat names, but values can or different types 
  - music(state)=on, heavy(state)=on > ok
  - music(state)=on, music(state)=on > ko
  - music(state)=on, music(switch)=on > ok
  - music(switch)=on, music(switch)=on > ko
- creates a "path", but seems just a combo of variables with some minor logic
  - becomes a "AkDecisionTree"
  - can repeat objects in different paths, can't set 1 path with N objects
- allows a "generic path" (*) as default too
  - Node's key=0
- allows a special "none" value that doesn't need to be added to the group, but is treated as such
  - Node's key=(hash of "none")
- groups are added in defined order as Arguments's AkGameSync
- may add N groups, but must use all to define, only once per group, in defined order
- ex. with "music" + "action": 
  - "music=exploring" + "action=low" > bgm01_low = ok
  - "action=low" + "music=exploring" > bgm01_low = not possible
  - "music=exploring" > bgm01 = not possible
  - "music=exploring" + "music=action" > bgm01_action = not possible
- groups can be reordered (so "action=low" + "music=exploring" now becomes ok)
- changes can be aligned after another switch is triggered
- needs at least one group for "*" path to work
  (just the group needs to exist, not needed to add as path)
- can define path with no end object (audioNodeId=0=any, sometimes audionodeId=1=none)
- ex.
  - group: music=* 
      Node key=0, children=...
       Node key=0, audioNodeId=(sid)
  - group: music=exploring
      Node key=0, children=...
       Node key=(exploring), audioNodeId=(sid)
  - group: music=exploring, playerhealth=none
      Node key=0, children=...
       Node key=(exploring), children=...
         Node key=(none), audioNodeId=(sid)
  - group: music=*, playerhealth=none
      Node key=0, children=...
       Node key=0, children=...
         Node key=(none), audioNodeId=(sid)
  - group: music=exploring, playerhealth=none + music=*, playerhealth=*
      Node key=0, children=...
       Node key=0, children=...
         Node key=0, audioNodeId=(sid)
       Node key=(exploring), children=...
         Node key=(none), audioNodeId=(sid)
- also works with values in between: music=exploring, playerhealth=*, action=heavy
- when changing groups that point to other objects:
  - old sound stops at next defined sync point then new
    - if object is the same, it keeps playing, unless bIsContinuePlayback is unset (stops + restars)
  - may use a transition segment or fadeout
  

## random/sequence container
- same as music ranseq, can contain subobjects
- may define object transitions (ex. delay between objects)
  - only in continuous mode, in values ms
- may define initial delay (before starting to play)
  - as a AkProp in float time
- may define loop random modifies: min (must be negative) or max (positive)
  - picks a value in that interval?
- modes are very similar to playlist but are set as main mode + submode flag
  - sequence + continuous: plays all objects in sequence, on loop/next call restarts
  - sequence + step: plays one object from first, on next call plays next object / cannot loop
  - random + continuous: plays all objects randomly, on loop/next call restarts
  - random + step: plays one object at random, on next call plays another object / cannot loop
  - loop above means flag set on ranseq level (loop flag on children level "traps" like playlists)
  - even though steps cannot loop (loop=1), sometimes sets loop=0 when "avoid repeating last X" is set (still don't seem to loop)
    - on sequence step, "avoid repeating" it's kept as set but not used

## switch container
- same as music switch, can contain subobjects
- can't define multiple groups, only 1
- older version of music switch also only do 1 group, and are basically the same as this
- may define initial delay (before starting to play)

## stingers
- a special type of musicsegment that plays a short audio on top of current track
- set on musicranseq, musicswitch or musicsegments in `pStingers`
- stingers have an associated `trigger` (that starts them) and a musicsegment (what they play)
- same trigger may be reused (like `fight_end` could trigger an special segment in different battle BGM)
- when multiple objects have the same trigger seems only plays latest one?
  - ex. musicranseq with trigger001 immediate > musicsegment with trigger001 next bar
    - only second trigger001 seems to play, deleting it plays first one

## transitions
- both are defined and used in music switch and music ranseq to set how to jump between 2 music segments
- a transition defines a "source" segment ID (segment that exits) and "destination" segment (segment to be entered)
  - may also define a "transition" segment in-between (similar to setting directly in the playlist, just to fine tune)
- segment can be -1 = any, used for any segment if no better rule is found
- segment can be 0 = none/not playing, usually for playlist starts (0 to first sid)
- playlists must always define -1 to -1 (default, can't be deleted)
- exit/entry points can be set as:
  - entry/exit cue: uses segment's entry/exit markers
  - immediate/next beat/next bar/next cue/etc: syncs depending on current position
- a musicranseq is fixed to use entry/exit, others are for switches
  - so once segment reaches exit cue, engine can to jump to next segment in playlist
  - if there is a transition segment, it's played first
- musicranseq looping works in the marker region (it's just using entry/exits)
  - once segment reaches exit, engine jumps to entry using the same logic
  - it also uses the transition segment
- when dst is another playlist may set entry segment (switch only?)
- transitions also set whether to play after source's exit and before destination's entry
  - source's after exit and destination's entry audio overlap in this case
  - looping also follows this (since it's just exit/entry to itself)
  - playing before entry seems only allowed when using entry markers
    * doc: "The pre-entry of a destination will only play if the destination begins at its entry cue"
  - `bPlayPostExit/bPlayPreEntry`: 0=don't play, other=do play
- ex. 1 clip of 10s, start at 3s, end at 7s, loops forever, may play like this:
```
- don't play before, don't play after
  |3..7|
       |3..7|
            |3..7| ...

- don't play before, play after:
  |3..7|..10)
       |3..7|..10)
            |3..7|..10) ...

- play before, don't play after:
  (0..|3..7|
       (0..|3..7|
            (0..|3..7| ...

- play before, play after
  (0..|3..7|..10)
       (0..|3..7|..10)
            (0..|3..7|..10) ...
```
- Transitions can also set entry/exit fade curves (on entry: fade-in, on exit: fade-out)
  - `transitionTime`: fade duration (in ms)
  - `iFadeOffset`: position ("time difference between marker and the fade") (in ms)
  - `eFadeCurve`: curve type (linear=/, logaritmic, etc)
  - sometimes segment has playpostexit + very short fade so make smoother entries
    - ex. MGR: 100ms fade, position 100ms
- in editor is set with a "play post-exit/pre-entry" + "fade-out/fade-in" checkboxes
- in the fade editor, you set "time", "offset" and "curve"
- must set at least a non-zero value in either for the fade to work, otherwise it's ignored
  - time=0, offset=0 > ignored
  - time=0, offset=1s > abruptly stops the post-exit after 1s seconds
  - time=1s, offset=0 > fades right after post-entry
- linear curve is the default
- curve duration starts *before* exit or *after* entry:
```
- source's exit fade-out (modifies src):
                ( dst pre |    dst body    | ...
    ... |    src body     | src post )

                      \...:                 #time=2s, offset=0s
                        \...:               #time=2s, offset=1s
                          \...:             #time=2s, offset=2s
                                            #(negative offset not possible here)


- destination's entry fade-in (modifies dst):
    ... |    src body     | src post )
                ( dst pre |    dst body    | ...

                      :.../                 #time=2s, offset=-2s
                        :.../               #time=2s, offset=-1s
                          :.../             #time=2s, offset=0s
                            :.../           #time=2s, offset=1s
                               :.../        #time=2s, offset=2s

```

## RTPCs and graphs
- Define some types to set what is exactly affected and how
- Then define a bunch of "points" to make a graph (X/Y axis).
- You get a math function-like graph, usually pass X (external value), get Y (resulting value)
  - for example, may define a X=hit_points, Y=volume: when hit_points=30 graphs sets volume to 50%
  - config is set on RPTC (main) level, X=rtpcType, Y=ParamID.
- each point defines an easing/interpolation function to the next point, that alters how Y evolves
- Setting 2 points makes basically a sub-graph and combining points makes a full graph
- RTPC example, making a weird fade-in:
  * meaning of X could be "hit_points", and meaning of Y could be "volume %" (set on RPTC level)
  - point A: x=0,  y=0,  interp=linear
  - point B: x=10, y=50,  interp=curve
  - point C: x=20, y=100, interp=linear
  - (A,B): from hit_points 0..10 you get volume 0..50. At hit_points 5, volume is 25% (linear)
  - (B,C): from hit_points 10..20 you get volume 50..100. At hit_points 15, volume is ~65% (non-linear)
  - less and A (-1) and more than C (30) presumably use their min/max values.
```
          Y=volume
       100
          |         -
          |       --
        50|    ---
          |  /
          | /
          |/_________
          0    10    20 x=hit_points
```
- Definition:
  - may define multiple, separate RTPCs per object, clicking on the graph to add more points
  - must define game parameter first, with min/max/default, before usage
  - then in object (RPTCs can be attached to almost everything), set an Y from the allowed list, then X from parameters
    - X's min/max depends on defined values
    - Y's min/max depends on the selected variable
    - X's default is used to show value in editor, and saved to Init.bnk in RTPCRamping.fValue (used?)
    - X can be a special LFO/envelope/time modulator rather than gamesync
  - can define as many points as needed (considering performance)
  - "volume" Y can use "linear" (eScaling=0) or "db" volume (eScaling=2).
  - selectable curves: Logarithmic (Base 3), Sine (power fade in), Logarithmic (Base 1.41), Inverted S-Curve, Linear, Constant, S-Curve, Exponential (Base 1.41), Reciprocal Sine (power fade out), Exponential (Base 3)
    - logs, sin in, inv-scurve are "fast" curves (take less time to ramp up)
    - exps, sin out, scurve are "slow" curves (take more time to ramp up)
    - constant is a special setting that keeps value same as 1st point (no curve and ignores 2nd point)
  - in editor can set a value of X to get simulated value of Y
- RPTCs can be linked to game variables then to switches/states
  - for example `enemy_awareness` could link to exploration/action music via switches
  - also may use "slew rates" so that changes between states aren't inmediate 
    - so even if values keep quickly changing, transition takes some time for more natural results
- objects limit RTPC properties from the full list
  - aksound/switch/ranseq/actormixer: most
  - aksound with external/blend: less
  - mswitch/mranseq: most
  - msegment/mtrack: less
- event/actions don't have standard properties nor RTPCs (internally are properties but behave differently)

## Clip automations
- attached directly to MusicTrack's clips, a special type of RTPC
- used to fade or apply effects in a clip
- makes a point graph like RTPCs, but X is always "time" in the clip
- in the clip, drag little triangle on the top left and right to add a fade-in and fade-out
  - just like dragging the little block on the bottom left/right changes clip times
  - internal points: fade ins 2 (0=0%...N=100% volume), fade outs 3 (0=100%..N=100%..M=0% volume)
  - can change curve type, but not points
- press the lowpass/highpass/volume button to activate graphs for those
  - add more points by double clip (like a regular RTPC), can change curve type between points
  - volume bar on top/100% = disabled (not written), same with lowpass/highpass on bottom
- time is relative to the clip and not track/segment, after applying trims/padding
  - with clip of 0..13s
  - add a fade-in 0..5s: X=0..5
  - move clip so it starts at 1: no change on X
  - trim start 1s: no change on X
  - padding start 1s: no change on X
  - add a fade-out 10..13s: X=10..13
  - trim end 1s: X=9..12
  - padding start 1s: X=11..14
  * in some (early?) games negative X values exists when combined with trims/fplayat/etc
- added by default when 2 clips overlap (autoadjusted fade-out + fade-in) but can be changed
  - with multiple clips, automation is attached to one defining "uClipIndex" where index is AkTrackSrcInfo (not AkBankSourceData.
  - if there are sub-tracks, uClipIndex + AkTrackSrcInfo are absolute so no difference

## Buses
- Audio in Wwise is routed through "buses" that apply volume/effects/etc.
- There is always a "Master Audio Bus", and you can define other buses
  - main: same as Master Audio Bus, objects can route to other main buses instead (so only those bus parameters)
    - has various volume/config/etc (see below)
  - children bus (sub-bus): same, but routes audio through main bus
    - sub-buses may change output config and parameters just like parent
    - sub-bus volume=-10db, main bus volume=+10db means no change.
  - auxiliary buses: special bus that "copies" audio, used for custom behaviors within game
    - a sub-bus may define N aux-buses to route
      - probably for different emitters, or custom stuff like beat analysis
    - aux buses may change output config, but can only increase volume (other options seem ignored?)
    - there are "user defined" and "game defined", unsure about diffs
    - aux-buses seem intended to apply effects like reverb (base sound + proximity aligned bus)
    - seems aux-buses may ultimately go to output
- sub-buses may have sub-buses and aux-buses children, while aux-buses may have aux-buses
- buses also define output device (system sound, etc) and parameters like output channel config
  - probably does up/downmixing depending on this config
- Bus properties:
  - audio volume: main output
  - voice volume: pre-applied to audio before any routing (some kind of quick global per-object setting?)
    - despite the name this affects audio objects
  - pitch/low pass/high pass: filters
  - "output" bus volume / low pass / high-pass: only on sub-buses
  - aux-buses doesn't have "base" voice/pitch/low pass, but does have "output"
- Object may define output bus (main or sub, not aux)
  - SFX objects may always change bus
  - Music object may need to click "override parent" first
  - internally seems to just set overrideID
- They may also define (separate from output bus) aux-bus
- Buses have config like other objects: states (to change volume/pitch), RTPCs, etc
- Bus output config: a bus may decide to change channel output config
  - same as parent: just passes to parent (only applies effects)
  - same as main mix: applies default config (like 2.0)
  - Audio Objects: uses 3D spatial config (for actors that exist in 3D space, defined elsewhere)
  - 1.0/2.0/../N.n: up/downmixes to that
  * For example, if sub-bus downmixes to 1.0 and main has 2.0 (upmixes), output is 2.0 but from 1.0 audio = double mono
- The overall pipeline combines children buses to a final bus then output
- overriding and final bus:
  - a "top-most" object must set a bus
  - editor allows to change bus without checking "override parent" (since there is no parent)
  - internally always sets `OverrideBusId=NNN` to the final bus, usually Master Audio Bus
  - any children of this object (like musicswitch > musicsegment) inherits parent's bus (`OverrideBusId=0`)
  - editor can check "override parent" and set another bus
    - by default it autoselect "Master Audio Bus" when checked, regarless of parent
- in latest version buses can be of different types, depending on when/how buffers are mixed
- aux buses can be defined per object (up to 4) and override parent (has a flag) 
  - if object has no parent override flag is not set



## Volumes
```
sound > (volumes) > bus > bus > ... > bus > output
                  |                 |
                  \ aux > ... > bus /
                  \ aux > ... > bus /

```
- Pipeline details of how audio is modified
  - sound: default sound
  - global (all channels) volumes:
    - voice volume (buses's voice volume seems to be pre-applied at this level too)
    - normalization, make up gain, HDR and other sub-types, API `SetScalingFactor`, etc
  - per channel volumes: 2d positioning, panning, API, etc
  - "dry path": bus "Output Volume" + RTPC, API `SetGameObjectOutputBusVolume`, etc
    - also "Parent Bus without effects inserted: Volume" ??? (pre-aplies parent volume?)
  - "wet path": distances, user defined aux seng volumes (+RTPC)
    - only for aux buses
  - non-mixing bus: bus volume, positioning
    - also "Parent Bus without effects inserted: Volume" ??? (pre-aplies parent volume?)
    - repeat per parent buses until main
  - output mixing
- final volume output is the addition of all volumes, except aux busses that 
  - aux-buses go in parallel so 
- "Voice Volume" = Slider + RTPC + State + Set Voice Volume action
- "Bus Volume" = Slider + RTPC + State + Set Bus Volume action
- editor can show volume info by going to profile view, pressing "capture data", playing the file and stopping/clicking in the line
  - since volumes may change on realtime with RTPC/states you can record for a while, but for simple tests
- volume types on audio objects:
  - `[Volume]`: "voice volume" slider, main volume of the object
  - `[MakeUpGain]`: "make-up gain" slider, special volume that doesn't count for some calcs but still is pre-applied before passing on
  - `[OutputBusVolume]`: "bus volume", a volume associated to the bus itself
    - separate from main volume b/c sometimes you need a bus with some extra volume but the aux-bus with another (I'd think they could just lower aux volume but...)
  - `[UserAuxSendVolumeX]`: same but for the aux volume X
  - `[ReflectionBusVolume]`: special volume for a separate "reflection" aux bus
    - also separate b/c it's better for the reflection plugin etc
- volume types on bus objects:
  - `[BusVolume]`: main "bus volume" slider
  - `[Volume]`: "voice volume" slider, applied before *receiving*
  - `[OutputBusVolume]`: same as before, applied before *passing*
  - `[UserAuxSendVolumeX]`: same as before
  - `[ReflectionBusVolume]`:  same as before
- final volume of a sfx > sub > master relationship is calculated like this:
  - audio object:
    - `Volume`=-3 > `MakeUpGain`=-2 > `OutputBusVolume`=-1  (0 + -6 = -6 before passing)
  - sub-bus:
    - `Volume`=1 > `BusVolume`=2 > `OutputBusVolume`=3  (-6 + +6 = 0 before passing)
  - main bus:
    - `Volume`=-5 > `BusVolume`=-4 (0 + -9 = -9 to output)
  - order doesn't really matter since it's just adding totals
  - if there was an aux-bus, it'd just apply its settings as another path
- plugins like PeakLimiter or Gain also apply on each step
  - associated in BusInitialFxParams > FXChunk, then pointing to CAkFxShareSet
- if multiple voices sound at once (ex. aklayer) each voice calculates final volumes separately
  - as each one may have any final result, depending on factors
- language bank also has a "makeup gain" setting, but it just applies that to each aksound

## properties and performance
- unsure at what point volumes are actually applied over buffer samples:
  - on each object's samples: less efficient (1 by one) but more simple
  - at mixing time if possible (hoisting common values): more efficient but more complex to set up, may end up doing more passes
  - doc on actor-mixer: 
    - effects: "effects is processed on real time per object and will take cpu"
    - properties: "saves memory and cpu" (referring to states/rtpcs, since values can be precomputed?)
- effects are applied once per bus, and per each object

- on advanced profiler 
  - buses have a "mix count" depending on number of simultaneous voices going there
  - voices have: voice volume, bus volume and total volume (bus + voice)
- bus mix count:
  - single voice 1, 2 voices 2
  - 2 voices with one aux send: 3 (since aux bus also end in the main bus)
- presumably:
  - first, voice volumes are applied over samples (total volume from object voice volumes + selected bus's voice volumes)
  - then, if a voice goes to bus, its bus volume is applied

## actor mixer
- a way to group N sound types and apply values config
- contains any sound engine types (ranqseq, switch, layer,sound, more actor-mixers, etc) but not music engine types (musicsegment, musictrack, etc)
- it's not referenced directly, but a way to apply values to several objects at once
  - an aksound children of an actor mixer would apply their own volume/pitch/etc then the actor mixer's volume/pitch/etc
- an actor-mixer isn't referenced directly, but it's config is applied
  - an event would call the aksound, and then that aksound would apply its own and its parent's properties
- since objects can only have one parent, it's parent must also be part of the actor mixer to apply its config
  - actor mixer > aksound: ok
  - actor mixer > akswitch > aksound: ok
  - actor mixer > aksound1 + akswitch > aksound1: ko

## inheriting properties
* >> "About Properties in the Project Hierarchy"
- most objects can set values like: volume, pitch, lpf, hpf, etc
- pipeline is similar to how bus volumes are applied, or rather, bus volumes would apply like this:
  - start with a bottom-most playable object (aksound, musictrack)
  - apply its own values
  - seek parent (`DirectParentID=N`)
  - apply parent's values
  - repeat seek + apply parent until `DirectParentID=0`
- values are inherited even if parent object isn't part of the play queue
  - musicswitch volume=-10 > musicsegment = -5
  - play event calls directly musicsegment
  - final volume is -15 (applies parent)
- each object has 1 associated bus, that also apply
  - that bus in turn applies its parent's config, also applied to aksound
  - can be top-most parent's (defaults to Master Audio Bus) or can be overriden with `OverrideBusId` at any moment of the chain
  - each bus itself (CAkBus) follows its parents to get a final volume
    - can't use an aux-bus
- objects can also have N alt aux-buses, that are similar but don't apply main bus's config
- on each step needs to take into account:
  - basic params (volume, pitch, lpf, hpf)
  - current RTPCs values (if set)
  - param-states
- built-in params (ex. volume) apply directly
  - ex. with a akswitch > aksound
  - when playing the aksound directly, it applies all parent's config
    - *doesn't* only apply the aksound's config ignoring parents
  - when playing the akswitch directly, it applies child's config
    - in this case the switch ultimately 
  - basically doesn't matter how file is played to apply config
- playback params only apply when applying that object:
  - `InitialDelay`: ex. akswitch 2s delay, aksound 1s delay:
    - playing the aksound starts audio after 1s
    - playing the akswitch starts audio after 2+1s
  - it's possible to set RTPC to these values but not recommended
  - for this reason, non-action objects like actor-mixer can't set initial delay
- in effect
  - built-in parameters are precalculated and applied to each sound directly
  - playback-parameters are post-calculated depending on usage
- "absolute properties": properties passed down from parent to child, but only apply once
  - buses, effects, positioning, advanced settings (playback limits/priority)
- "relative properties": properties that are cumulative from parent to child
  - volume, pitch, lpf, hpf
  - after adding, properties are capped: volume -200..+200, pitch -2400, etc

## properties
- volume, pitch, etc, set directly via editor and used as explained above
- properties may set "enable randomizer" to select between values at play
  - volume -5 and +5 will play some value in between on each play
  - offset after base values, so with volume=-96db and +-5 random, you get -99/-91db
- enable "all properties" tab to (seemingly) include properties that are useless
- possible to set custom properties (defined via bank/project)
  - not referenced anywhere, auto-set
  - if last valid PropID in v128+ is 0x49, custom IDs start at 0x4A
- during propery calculations, props can be modified by a "driver" (a "cause of change" in Wwise terms)
  - music segment envelopes
  - attenuations based on game positions
  - other attenuations (HDR, occlusion...)
  - ducking
  - events setting values (like "SetVolume" events)
  - fades
  - pauses/mutes
  - randomizers
  - RTPCs/StateChunks

## states tab
- object may tie an state to some property (volume, pitch, bus volume, initial delay, etc)
- music objects may also set sync type (on next cue, next bar, etc)
- seems it always inherits parent, even if parent isn't called?
  - ex. akswitch > aksound
  - akswitch sets state with lower volume
  - play event calls aksound directly
  - when state is set, parent akswitch volume lowers, but aksound is also affected

## Positioning
- objects may change their virtual position
  - similar to panning L<>R but more complex
- by default inherits parent unless set to override

## Effects
- objects may set custom, complex plugin FX
  - like echo, pitch shift, etc
- saved into `NodeInitialFxParams/BusInitialFxParams` > `pFXChunk` > `FXChunk`
- by default inherits parent unless set to override
  - if override, check one, then uncheck override, overriden effect isn't saved into bnk
- there is a limit of 4 per object (since they are more complex?)
- can be "rendered" to pre-bake the effect into the .wem
  - FXChunk exists with `bIsRendered=1`, but no fxID set
- can be bypassed with a flag (`bitsFXBypass`: 00001=first, 00010=2nd, .... 10000 = all)
  - flag can be controlled via RTPCs
  - if disabled via overriden just plays base audio (doesn't inherit parent or anything)
- can set statechunks/rtpcs, but only on their vars
  - internally become common flags: Wwise Gain's "full band gain" is "volume", and "LFE gain" is "LFE"
- can define a "share set" that is common config, or use default "custom" that is for that object
  - custom = CAkFxCustom (has guidname)
  - shared = CAkFxShareSet (has hashname), sets bIsShareSet flag
  - internally work the same and have same fields

## MIDI
- wwise supports MIDI objects as BGM
- can be defined to play using Wwise Synth, or with a sampler by importing individual .wav notes
