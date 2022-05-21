# TODO
Low priority TODOs

## general
- fix todo-s 

## parser
- support Shadowrun, Too Human
- clean bitflags in parser (some change between versions)
- make as list: uNumSrc, srcID/etc, Children, etc
- v36<= eTransitionMode/_bIsUsingWeight etc recheck

## model
- 'var' type may go over omax, should adjust max loops
- attr list may return non-ordered to speed-up find()?

## gui
- show ico https://stackoverflow.com/questions/18537918/why-isnt-ico-file-defined-when-setting-windows-icon
- show viewer open status (change text to "reopen?" "running")
- viewer on another thread?

## view
- check if port is open (may open 2 instances and only 1 server works, but there is no port error)
- improve threading/pool? (not too useful as doesn't have that many resources)
- maybe move preloads to globals, auto init, recreate node printer every time
- button to hide generic/useless stuff? (PositioningParams, AdvSettingsParams, etc)
- add combo with all common HIRC types
- links: if not found/loaded call bank and load sid id

## names
- add key per game in DB so wwnames can contain everything, register "default" common names

## txtp
- txtp should round up numbers? 1/48000 ~= 0.0000208333 * 48000 = 0.999999 > 1 or 0?
  - makes it easier to compare vs tree and most times can't be rounded
- overlapped transitions
  - needs fades (games use fading transition to smooth out loops)
  - next segment and looping to itself may have different transitions
  - randoms also need transitions from A to B/C/D/E/F to G
- transition objects in mranseq (Polyball)
- round values that don't make samples, `#r 1.5000000000000002`
- resampler for demo music, pokemon, sor4
- apply transition delays: fTransitionTime in all ranseqs, TransitionTime, etc
- recheck TTime in earlier games (ex. Trine 2)
- fix multiloops
- DelayTime/InitialDelay may not work correctly with loops (ex. John Wick Hex 2932040671)
  - difference between them? 
- apply default bus volumes for better results? (ex. Astral Chain, Gunslinger Stratos)
- mark loop inside inner group (double loop) as multiloop (ex. DmC last boss)
- mark dialogueevents somehow as they can have the same name as events
- check how argument is used in older wwise dialogue events
- unused nodes may be affected by loading parent? (probably little effect)
- builder: find0() / optional=True, return emptyNode where value() is None
- maybe set option to not generate statechunks "nothing set" for MGR
- add get_info() in model that converts tid to hashname and common props
- prioritice variable order for Spiderman: Web of Shadows
  - some kind of weight system?
  - doesn't seem useful to order by wwnames since different events may order differently
- layers of blend RTPCs (hard to understand and not very used)
- state: may be useful to add multiple gsparams: "st=a1 / st=a2" (fake gspath combos)

## properties
- filter properties that can't combine: pitch<>music objects, etc
  - AkProps.filter()?
- simplify+unify RTPC and AkProp usage > AkPropertyInfo?
