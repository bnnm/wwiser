# WWISE EDITOR NOTES

Info gathered from the editor, to help understanding model and overall behavior.


**recheck**
- ! multiple events with same ID are possible (editor gives "same id, may 
  have trouble to play", ex "british" + "bucconidae"), how to handle?
- music switch can have multiple playlist playing at the same time?
- pStateChunks for switching + syncs? (may be set as default?)


## gamesyncs
- "switches", "states", in key=value format
- there is also "game parameters" (have RTPC config) and "triggers" (no config)
- values are global for all banks and can't repeat names under same category
  - switch "music" and state "music" can be created, but 2 states "music" cannot
  - value names can be repeated
- gamesyncs can be organized in 'subfolders', but this isn't reflected in .bnk
- .bnk doesn't normally save a list of gamesyncs (but found in init.bnk in earlier versions)?


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
  - random step: plays one subtrack at random
  - sequence step: plays first subtrack; next time track is played next subtrack
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
- plays a list of objects inside a group
- defines groups with modes that change when track is played
  - sequence continuous: all objects, one after other
  - sequence step: picks one object, on next play OR loop picks another
  - random continuos: plays random until all objects are covered
  - random step: plays one random
- groups may have objects or other groups (with objects), at any position
- random types have weight (probability to play), from 0.001 to 100% (default 50)
- random types can use "standard"=allows repeats, or "shuffle"= doesn't
- random types can set "avoid repeat N" (see docs)
- each "group" has N objects
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
- can define path with no end object (audioNodeId=0=any)
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
  * Node
* when changing groups that point to other objects:
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

## switch container
- same as music switch, can contain subobjects
- can't define multiple groups, only 1
- older version of music switch also only do 1 group, and are basically the same as this
- may define initial delay (before starting to play)

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
