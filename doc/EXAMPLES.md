# USAGE EXAMPLES

Info about how games use Wwise in more unusual cases, for reference.

Path info (`event > play > ...`) isn't meant to be complete, as most games mix the usual paths.


## Wwise demo (PC)
- mixes sample rates in layers
- musicranseqs loop parts


## Xenoblade Definitive Edition (Switch)
```
BGM.bnk
    event > play > sound

    event > play > switch > sound
```
- sets loop flag and source has loop points
  - a few sources don't, but are meant to full loop instead
- doesn't set loop flag if file isn't meant to loop, file has no loop points
- doesn't use anything more complex than that


## Pokemon Sword & Shield (Switch)
```
[809510367] BGM.bnk
    event > play > mranseq > mranseq item > segment > track-start
                           \ mranseq item > segment > track-loop
                             * loop=0
[428932901] BGM.bnk
    event > play > sound

[1727994439] BGM.bnk
    event > play > mswitch > mranseq > segment > track-start
                           |         \ segment > track-loop
                           | ..
                           \ mranseq > segment > track-start
                                     \ segment > track-loop

[2009572835]
    event > stop > ...
          \ play (delay) > mranseq > ...
                                   \ ...

[2558687437]
    event > play > mswitch > 0
                           \ ...
```
- plays songs as one musicranseq with start+loop (different files), sets loop flag for track-loop
- clips don't set trims and are used as-is
- some musicranseqs mix 2 different sample rates, automatically handled by the engine (no flags)
- has play events pointing to non-existing ids
- some switches point to object 0


## John Wick Hex (PC)
```
Carpark.bnk, Cutscenes.bnk
    event > play > sound

Hex_Lair.bnk
    event > play > ranseq (random) > sound

[1174468113, 1604223825] Generic.bnk
    event > play > ranseq (random) > sound
          \ play > switch > ranseq (random) > sound

[2932040671 ~ 81749228] Generic.bnk
    event > play > segment > track
                           \ track + switch > subtrack [empty/playable]
                                            \ subtrack [789874677]

[1330618445] Generic.bnk
    event > play > ranseq (random) + pitch > sound

[2932040671 ~ 917788652] Generic.bnk
    event > play        > mranseq   > mranseq item > segment > track
            * delay=1.0   * loop=0    * loop=4               \ track
                                    > mranseq item > segment > track
                                      * loop=2
```
- uses internal sounds (banks), may set full loops
- uses ranseqs for sfx (gunshots, steps, etc)
- uses ranseq + ranseq for gunshot + echo (sound1 shorter than sound2, no delay?)
- uses subtracks + switch to make normal/action song variation
- subtracks may be empty (plays silence)
- some tracks play super-extended playtime with loop count
- sets sLoopCount in ranseq but doesn't loop?
- may apply pitch or other effects
- mswitch groups contain volumes

## Metal Gear Rising (PS3)
```
[156657127] BGM.bnk
    event > play > switch (song select) > mranseq > item (1 loops) > segment > track (wem1: 0s..20s)
                                                  | item (1 loops) > segment > track (wem1: 20s..116s)
                                                  \ item (N loops) > segment > track (wem1: 26s..116s)

[248769270] BGM.bnk
    event > play > mranseq > segment > track [123.wem]
                           |         > track [321.wem]
                           \ segment > track [321.wem]
                                     > track [123.wem]

[2329483676 ~ 606973843] BGM.bnk
    event > play > mranseq > item (l=1) > segment > track
                           | item (l=0) > segment > track
                           | item (l=1) > segment > track
                           | item (l=0) > segment > track
                           | ...
```
- uses "single trimmed wem to fake looping", but may need multiple segments to loop (not simulable with loop points)
- some of the looping parts have wem IDs not sorted (since they are ordered by segment/track ID)
- some files have many infinite loops defined, but can only play first one
- overlapped (layered) parts in transitions use very short fades (0.01s) so change between segments is smoother
  - in effect just trying to mask potential clips
```
    (...src...\___
              | <--- transition point
           ___/...dst...)
```

## Girl Cafe Gun (Mobile)
```
    event > play > sound
    event > play > switch > sound
          \ play > sound
    event > play > musicranseq > segment > track
    event > play > musicswitch > musicranseq > segment > track
                               | ..
                               \ musicranseq > segment > track
```
- some musicranseq only have one
- track sets loop flag for full loops (musicranseq also sets it?)
- some CAkSwitch use StateChunk/SwitchList/rParams (related to gamesyncs)
- check CAkSwitch (ex. 4033386954)


## The King of Fighters XIII (PS3)
```
[778418041]
    event > play > switch > ...
                          \ sound + sound

```
- one switch has 2 sounds nodes at once with some delay (rare)
- all songs set full loops? (even jingles)


## Devil May Cry 5 (PC)
```
[4065654621]
event > play > switch > (switch 1 to 1) > mranseq > segment > track (part1/base)
                      |                           \ segment > track (part2/loop)
                      \ (switch 1 to 2) > mranseq > segment > track (part2/base)
                                                  \ segment > track (part2/loop)
                      ...

[403462024 ~ 42629278]
event > play > (switches) > mranseq > segment [no tracks]
                                    \ segment > track
                                    \ ...

[3804249813 ~ 292765665 ~ 756717375]
event > ... > mranseq >  segment
                      |  ...
                      :  segment [unused]
                      |  ...
                      \  segment
```
- dynamic BGM is done with switches + transitions
  - base loop type 1 > switch change > loop type 2 > switch change > loop type 2 > ...
  - switches define transitions: entry/exit points + "on beat", that the engine properly delays/adjust
  - may also use a transition segment between mranseqs
- sections are directly accesible if proper switches are set
- many variables (+30)
- has empty stingers that don't actually point to another segment, and trigger ID isn't defined
- uses empty segments as padding
- has unused transition? segments (in children but not used) 

## Doom 2016 (PC)
```
   event > play > musicranseq > (complex mix) > music segment > music track

[560608461]
   event > play > ...
         | play > ...
         \ play (delay + transition) > layer (ranged mods) > ...


[1124879513]
   event > trigger > (segment depending on track that is on)
   
[521106783]
  (unused) mswitch > ...

[897823236]
  (unused) mranseq > ...


```
- may call triggers, that refer by tid to current mranseq's triggers
  (in bank, event calling trigger may exist before mranseqs)
  - basically 1 trigger > N "finish stinger" tracks
- musicranseqs have CAkStingers with a trigger ID (presumably triggered with CAkActionTrigger)
  and a music segment
- has multiple unused objects
- musicranseq playlists (ex. 729873617) mix parts like
```
    Continuous Random (A ~ B ~ C .. O)
      None A: Music Segment
      None B: Music Segment
      None C: Music Segment
      None D: Music Segment
      ...
      None O: Music Segment
    * final mix could play: C F H .. D > (loop) > J H K ... A > ...
```
- musicranseq playlists (ex. 649268705) mix parts like
```
    Continuous Sequence (A + B + C)
      Step Random A (A1 or A2)
        None A1: Music Segment
        None A2: Music Segment
      Step Random B (B1 or B2)
        None B1: Music Segment
        None B2: Music Segment
      Step Random C (C1 or C2 or C3)
        Step Random C1 (C1A or C1B or C1C)
          None C1A: Music Segment
          None C1B: Music Segment
          None C1C: Music Segment
        Step Random C2 (C2A or C2B or C2C or C2D)
          None C2A: Music Segment
          None C2B: Music Segment
          None C2C: Music Segment
          None C2D: Music Segment
        Continuous Sequence C3 (C3A + C3B)
          Step Random C3A (C3A1 or C3A2)
            None C3A1: Music Segment
            None C3A2: Music Segment
          Step Random C3B (C3B1 or C3B2 or C3B2 or C3B2)
            None C3B1: Music Segment
            None C3B2: Music Segment
            None C3B3: Music Segment
            None C3B4: Music Segment
            None C3B5: Music Segment
    * final mix could play (if let looped): A1 + B2 + C1A > (loop) >  A2 B1 C2C > (loop) > A2 B2 C3A2 C3B5
```

## Doom Eternal (PC)
```
[1699343283 ~ 747382736]
event > ... > mranseq > segment
                      | ...
                      \ segment [210678175]
                        * duration=0, entry=0, exit=0
```
- some playlist entries don't actually play anything


## Mass Effect 2 (X360)
```
[3309883760 ~ 714836408] Wwise_CritPath1_Music.bnk
event > ... > mranseq > segment
                      | ...
                      \ segment [514300449]
                        * duration=1.0, entry=0, exit=0
```
- some playlist entries have duration, but not entry/exit

## Wipeout Omega Collection (PS4)
```

    event > play > mranseq > segment > track
                                     | track
                                     | ...
                                     \ track
```
- uses N tracks per segment to layer multichannel songs (not looped)
- tracks are trimmed as they end in long-ish silence
- some tracks use panning?


## Polyball (PC)
```
[1222713843 ~ 545197717] Level_Music_Otherworld.bnk
    event > ... > mranseq > 
```
- uses transition objects in musicranseq (rare)

## Trine 2 (PC)
```
music.bnk
event > play > ...
        * TTime

[627717201 ~ 697585740] sound_effects.bnk
event > play > ...
        * tDelay
```
- defines fade-in and delays

## I Am Alive (PS3)
```
[1414351620] 2858921253.bnk
event > play > segment > track
        * tDelay
```
- plays segments directly


## GTFO (PC)
```
[406901569 ~ 456829687] music.bnk
event > play > ...
        * DelayTime=8.0
```
- has delay (not initial delay)

## Doom 2016 Alpha (PC)
```
[327238192 ~ 579819651] sfx.bnk
event > play > ...
      \ play > ...
        * DelayTime=1.5
```
- has delay (not initial delay)

## Tony Hawk Shred (Wii)
```
[591766813] env_delta.bnk
    event > play > layer > sound [plugin]
                         | ...
                         \ sound
```
- uses plugins


## Magatsu Wahrheit (Mobile)
```
[2435259060] BGM_00_EV.bnk
    event > play > mswitch > mranseq   > mranseq item > segment > track (x3)
                             * loop=0  \ mranseq item > segment > track (x3)
                                         * loop=0

[4170566524] BGM_00_EV.bnk
    event > play > mswitch > mranseq   > mranseq item > segment > track (x3)
                             * loop=0  \ mranseq item > segment > track (x3)
                                       | * loop=0
                                       \ mranseq item > segment > track (x3)

[1619779996] BGM_01_EV.bnk + BGM_01_ME.bnk
   event > ... > sound (points to media index in ME)
```
- some events set multiple loop infinites (only innermost would be used)
- some events set loop infinite, but have a song end after it (never plays)
- some events in EV.bnk (events only) point to ME.bnk (media only) media
- most layers use sounds with MakeUpGain = -96dB to silence parts, rather than regular volume

## Ori and the Will of the Wisps (PC)
```
[266604379] motay.bnk
    event > play > ranseq > sound
                   * idelay

[2281690816] wisp.bnk
    event > play > layer > sound
                         \ sound
                           * idelay

[663920761 ~ 889284586] musicCommon.bnk + persistent_eventsOnly.bnk
    event > ... > mranseq > (mranseq item) > segment > track
                  * loop=0   * loop=0

[307919088]
    event > play > mranseq > segment > track
                   * loop=0

[663920761 ~ 151294023] musicCommon.bnk + persistent_eventsOnly.bnk
    event > play > sound
          \ play > ranseq > sound
                   * random (only 1)
                   * loop=0 

[422551738 / 867165422] musicCommon.bnk + persistent_eventsOnly.bnk
    event > play > sound
          \ trigger > (trigger-id to call stinger in current mranseq) > segment > track

[185087937] act1WellspringGlades.bnk + persistent_eventsOnly.bnk
    event > play > layer > sound
                         | * loop=0
                         \ sound
                           * loop=0
                           * volume=-96, pan, etc

[2416701321] act1WellspringGlades.bnk + persistent_eventsOnly.bnk
    event > play > layer > sound
                         | * loop=0
                         \ ranseq    > sound
                           * loop=0  | ...
                           * pitch   \ sound
                           * etc

[663920761 ~ 881187774] musicCommon.bnk + persistent_eventsOnly.bnk
    event > play > mranseq > segment > track
                   * loop=0
                   * self-transition + overlap

[663920761 ~ 743818448] musicCommon.bnk + persistent_eventsOnly.bnk
    event > play > (mswitches) > mranseq > segment > track > clip
                                                           \ event        > setstate
                                                             * at fPlayAt
```
- loads multiple banks (mainly *persistent_eventsOnly.bnk* as base + other)
- events can be used before they appear in the ordered bank (objects calls eventId)
- sets multiple infinite loops in some mranseqs (would loop the innermost one)
- sets multiple infinite loops in sounds, and random groups, and others
- loops single elements
- combines start sound + looping random (not actually random), where loop doesn't include sound
  - hard to simulate as a loop
- may start a sound and trigger a stinger to stop previous sound
  - different mranseqs use the same trigger-ids to call same segment
- some objects use pitch changes
- multiple banks save the same .wem in different media index, but same ID

## No Straight Roads (PC)
```
[1155779205 ~ 147930590]
    event > ...  > segment > track      > subtrack 1 > 1.wem
                             * random   | subtrack 2 > 1.wem
                                        \ subtrack 3 > 1.wem

[~ 369525547]
    event > ... > msegment > mtrack > (key1=1) subtrack1 > ...
                           > mtrack > (key2=2) subtrack2 > ...
                           > mtrack > (key1=3) subtrack3 > ...
```
- tracks have random type but point to the same object
- has tracks that changes (switch variables that are only accesible on change)
  - usually all point to the same thing
- has vocal songs in multiple languages (set as localized banks)
- uses variable 0x27 [FadeOutTime]
- has a lot of strange usage of features to achieve effects in twisted ways (inexperienced?)
  - ex. creates many sequential clips to loop a track of few seconds, that is also silenced most of the time
  - this is rather cheap in Wwise (ie. N nodes = 1 playlist of same things) but makes lots of VGMSTREAMs in .txtp,
    reaching the max segment limit and failing to open


## Bayonetta 2 (Switch)
```
[~ 247994730 ~]
    event > ... > mswitch > (key1=valA) mswitch > (key1=0) mranseq > ...
                                                > (key1=valA) mranseq > ...
                                                > (key1=valB) mranseq > ...
                                                ...
```
- has dynamic changes (switch variables that are only accesible on change)
  - usually all point to the same thing

## Tetris Effect (PC)
```
[1638535919] SB_16_HawaiiTribal_BGM_01.bnk
    event > ... > segment > track [vorbis]
                          > track [midi]
                           ...
                          > track [vorbis]
```
```
[831639979] SB_20_SeaGoddess_BGM_01.bnk
    event > ... > segment > track [6ch]
                          > track [2ch + plugin + bus]
                ...
                > segment > track [6ch]
                          > track [2ch + plugin + bus]
```
- uses wmid mixed with .wem (drums)
- uses multiple 2ch vocals that use a peak meter FX plugin, and are re-routed to another bus with no channels defined
  - presumably only used to read peak values and aren't output
  - extra vocals set volume

## Detroit: Become Human (PC)

```
* Play_C05_INGAME_MUSIC (C05_Music_State=C05_OnChase_Part_3)
[129941368] BNK_C05_Music.bnk
    event > ... > mranseq       > item ..
                  * seq.step    > item ..
                  * loop 


[.. > 799010033 !!!] BNK_C06_Music.bnk
mswitch > - item x11 !!!

[.. > 799010033 !!!] BNK_C06_EdenClub.bnk
mswitch > - item x5 !!!
```
- has an infinite looping step sequence, in effect a regular sequence
- different banks contain *same object IDs* but with *different number of children*
  - in theory not possible, unless they make one bank, modify the object and make another bank (or copy projects)
  - probably never loaded at the same time (not allowed by Wwise?)


## Nier Automata (PC)
```
* BGM_PauseBoss_Opera_In
[594371225] BGM.bnk
    event > ... > mranseq       > item ..
                  * seq.step    > item ..
                  * loop        > item ..
                                ..
                                > item ..

* BGM_GameCenter_In
[3040688901] BGM.bnk
    event > ... > mranseq       > item .. * loop
                  * rnd.cont    > item .. * loop
                                > item .. * loop
                                ..
                                > item .. * loop
```
- has an infinite looping step sequence, in effect a regular sequence
- has a non-looping random continuous that ends in a infinite loop, in effect a shuffle of N songs
- uses lower volumes for extra quieter song variations (`BGM_Layer=Middle` > `BGM_Layer=Quiet`)

## Mario Kart: Home Circuit (PC)
```
[2196894807 > 133443069]
    event > ... > mranseq       > item .. * loop
                  * seq.step    ..
                                > item .. * loop

[3079605662]
    event > play > sound
          > play > sound
                   * loop

[3041644995]
    event > play > sound [no loop, wem loops]

[2526619286]
    event > play > layer > sound [no loop, wem loops]
                         > switch > sound [no loop, wem loops]
```
- has multiloops (with all looping or only 1)
- has step sequence that ends in a infinite loop, in effect "change-per-play" N songs
- plays non-looping song with internal loop but doesn't set loop at all nor disable them (loop=1)
- has CAkSound with Wwise Motion Generator in regular ranseq
  - not audio, see Wwise demo v128>= Motion.bnk
- uses Wwise Silence with various durations

## Nimbus (PC)
```
[2891093359]
    event > play > ranseq       > sound
                   * normal     > sound
                   * loop
```
- has a simple ranseq that loops same track? doesn't seem to change between loops

## Battle Chasers: Nightwar (PC)
```
[3675240519]
    event > play > ranseq  > sound [2ch]
                   * loop  > sound [1ch]
```
- mixes 2ch + 1ch (mono being silent and used as simple padding)

## Assassin's Creed: Valhalla (PC)
- mixes 2ch + 1ch (mono being silent and used as simple padding)
- has transitions in playlists
- uses Wwise Tone plugin in various events

## Assassin's Creed 2 (X360)
```
    event > play > sound [bgm]
                 > layer > sound [crowd 1]
                         > ...
                         > sound [crowd N]
```
- plays BGM with "music" sound + "crowd" sfx looping layer silenced via RTPC, in *every* BGM
- has CAkFeedbackNode with Wwise Motion Generator in regular ranseq (ex. 5297032)
  - not audio, see Wwise demo v125<= Motion.bnk

## Spider-Man: Web of Shadows (multi)
```
* mx_combat (act=act3) (spidey_suit=-) (music_intensity=high)
[3124666157 > 122709253] common_music.bnk / 3380667234.bnk
    event > ... > mranseq   > item
                  * loop    ..
                            > item  > ... > 189662451.wav [clicks]
```
- has a buggy/imprecise transitions, where it jumps early and ~3ms/145 samples are cut off
  - this matters in some songs where some source files have a click at the end
  - rarely and randomly, songs play fully instead of jumping early on real systems, resulting in a click
  - bank version ~v34 PC, also heard in PS3 version
  - sometimes may also extend/jump late?

## Halo Wars (X360)
```
* play_in_game (In_game=world_intros) [1617394438=music_harvest]
[3671131488 > 791593293] 3991942870.bnk
    event > ... > msegment > mtrack [loops due to trims]
                           > mtrack [loops due to trims]
```
- has non-looping sections that use layers with loop #E (could fool txtp?)
- most songs use sequence step + N subsongs
- uses Wwise Silence with various durations

## Nimbus (PC)
```
[2891093359]
    event > ... > ranseq        > sound 1
                  * continuous  > sound 2
                  * loop
```
- has random + continuous + loop, in effect behaving like a sequence
  - confirmed in videos

## DmC (PC)
```
[2427747105 > 540417778]
    event > ... > mranseq   > item    > msegment
                            > item    > item    > msegment
                              * loop  > item    > item > msegment
                                        * loop  > item > msegment
                                                > item > msegment
                                                > item > msegment
    
```
- has loop traps inside inner sequences (not easily handled)

## Gunslinger Stratos Reloaded (PC)
```
3991942870 music: BusVolume=-18.0
``` 
- most BGM sets around +7dB volume, but override bus to use one with lower volume
  - also defines RTPC "MusicVol_Parameter" controlling bus volume
- some BGM define both volume and makeupgain for a resulting 7-9dB