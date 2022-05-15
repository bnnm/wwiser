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
- set multiple rtpc and generate combos: VALUE=0.0,1.0 to make 2 txtp (ex. Batman Arkham City)
  - multi-rtpc combine all: VALUE1=0.0,1.0 + VALUE2=2.0,3.0 = to make 4 txtp
- rtpc of makeupgain?
- apply rtcp default? option to use it? print in tree?
