# TODO
Low priority TODOs

## general
- fix todo-s 

## parser
- support Shadowrun, Too Human txtp
- clean bitflags in parser (some change between versions)
- make as list: uNumSrc, srcID/etc, Children, etc
- v36<= eTransitionMode/_bIsUsingWeight etc recheck
- akprops per version have a "max", and after it other props are "custom" per game: define of custom prop start

## model
- 'var' type may go over omax, should adjust max loops
- attr list may return non-ordered to speed-up find()?
- improve printing of floats (problem: hard to detect accuracy)
  - `-4.76837158203125e-07` > `0.000000476837158203125`

## gui
- show ico https://stackoverflow.com/questions/18537918/why-isnt-ico-file-defined-when-setting-windows-icon
- show viewer open status (change text to "reopen?" "running")
- viewer on another thread?
- allow loading wwconfig?
  - just call GUI with this file
  - don't load log
  - some flag to reuse loaded banks/wwnames?
- on opening close viewer?
- viewer on close web tab notify server
- option to transfer helper filenames + bks and make a base rip automagically?

## view
- check if port is open (may open 2 instances and only 1 server works, but there is no port error)
- improve threading/pool? (not too useful as doesn't have that many resources)
- maybe move preloads to globals, auto init, recreate node printer every time
- button to hide generic/useless stuff? (PositioningParams, AdvSettingsParams, etc)
- add combo with all common HIRC types
- links: if not found/loaded call bank and load sid id
- simple JS query:
  - `open = bank > HircChunk > listLoadedItem > *` #opens all items that match that tree
  - `close = NodeBaseParams` #closes all node params
  - `find = ...`

## names
- add key per game in DB so wwnames can contain everything, register "default" common names

## txtp
- txtp should round up numbers? 1/48000 ~= 0.0000208333 * 48000 = 0.999999 > 1 or 0?
- could round values that don't make samples, `#r 1.5000000000000002`
  - makes it easier to compare vs tree and most times can't be rounded
  - problem when rounding certain values depending if floor or ceil is used: 
    - 6.0000007 * 48000 = 288000.0336 ~= 6.0 * 48000 = 288000
    - 0.9999999 * 48000 = 47999.9952  != 1.0 * 48000 = 48000
  - may be useful to find dupes with simpler flag: body like 0.399999999 vs 0.4 (uncommon?)
- overlapped transitions
  - needs fades (games use fading transition to smooth out loops)
  - next segment and looping to itself may have different transitions
  - randoms also need transitions from A to B/C/D/E/F to G
- transition objects in mranseq (Polyball)
- resampler for demo music, pokemon, sor4
- fix multiloops
- DelayTime/InitialDelay may not work correctly with loops + groups (ex. John Wick Hex 2932040671)
- mark loop inside inner group (double loop) as multiloop (ex. DmC last boss)
- mark dialogueevents somehow as they can have the same name as events (unlikely though)
- check how argument is used in older wwise dialogue events
- builder: find0() / optional=True, return emptyNode where value() is None
- add get_info() in model that converts tid to hashname and common props

- layers of blend RTPCs (hard to understand and not very used)
- some way to set GS/SC/GV lists + defaults (auto generated list)
  - `* / (bgm_layer=on,off)` = one pass with auto vars, other exact vars [Astral Chain]
  - complex due to render setup
  - may not be useful b/c default may need certain flags > use wwconfig
- AC:BF BNK_SP_MU_Global_Naval_MUSIC has unused AkMediaInformation in 551617484
  - detect + register somewhere?
- filter localized .bnk options (to load all without looking)

## txtp fade-in
- apply transition delays: fTransitionTime in all ranseqs, TransitionTime, etc
  - TTime in earlier games (ex. Trine 2)
- fadein on actions (LoopCrossfadeDuration? and such props?)
  - problems with loops when fadein + automation? (would need to move down curves)
  - check weirdprops
    - "[FadeInCurve]", "[FadeOutCurve]", #seen in CAkState, used in StateChunks (ex. NSR)
    - "[TrimInTime]", "[TrimOutTime]", #seen in CAkState (ex. DMC5)
  - some rtpc params like Transition are for internal use only?

## txtp misc cleanup
- txtpcache > txtpstate (ts) + make wconfig/wsettings
- improve passing of txtpcache stuff
- don't use txtpcache from stats, pass stats directly, or read later
- wstatechunks improve generation code with "default" case
  - detect if default is unreachable fails
  - print default first?
  - print unrechable default? =~
- unused mark pass to Txtp() from Renderer?
- when applying volumes from bottom>top, hoist volumes (like layered #v3 can be moved to group)
- don't ignore sound volumes in simpler txtp? (uses auto normalize)

## txtp properties
- filter properties that can't combine: pitch<>music objects, etc
  - AkProps.filter()?
- simplify+unify RTPC and AkProp usage > AkPropertyInfo?
- prop calculator: could cache simple properties (default+parents)
- prop calculator: profile slowness when reading params
  - preload load parent bus my default? (rather than looking for it every time)
- improve wwise gain effect (Tetris Effect, DMC5)
  - check bypass effects flag
  - apply rtpcs on the sfx + base node bypasses

# txtp transitions
- on make_txtp read correct transitions depending on src<>dst
- write jumps (beta, format to be determined)
- problem: each .wem potentially has N rules
  - from nothing to wem (when starting to play, usually plays entry)
  - from wem to itself (loops, infinite but also N=3)
  - from wem to others: usually only "next wem" but in randoms may be N
  - from any to wem: generic values
  - from wem to any: generic values
- jumps ideas:
  - in/out + target: - (nothing), * (any) / self / position N or file.wem or ?
  - type: on beat N, on time N, next cue, ... needed?
```
    # without fades
    bgm01.adx #jo 25s  #ji 5s
    bgm02.adx
    # with fades
    bgm01.adx #jo 25s P / 2s 0s  #ji 5s P / 2s 0s
    bgm02.adx
```
- jumps ideas2:
  - print entry/exit as is like `#j 10.0 50.0` (entry/exit)
  - define rules like wwise (#@rule 1 to bgm01.adx play exit, play entry, fade in, fade out), transition
  - by default if no rules: play entry, play exit
