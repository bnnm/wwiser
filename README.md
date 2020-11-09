# WWISER
A Wwise `.bnk` parser, to assist in ripping audio from games using the Wwise engine.

Simply open `wwiser` without arguments to start the GUI. From there you can load
and view banks, dump contents or make TXTP (*wwiser can't modify banks*). It reads
and shows all `.bnk` chunks, including *HIRC* (audio scripting) data, and properly
identifies all fields.

Or from the command line: `wwiser [options] (files)`
- `wwiser bgm.bnk`
  (dumps `bgm.bnk` info to `bgm.bnk.xml`)
- `wwiser -d txt init.bnk bgm.bnk -o banks.txt`
  (loads multiple `.bnk`, like Wwise does, and dumps to banks.txt)
- `wwiser *.bnk -v`
  (loads all .bnk in the dir and starts the viewer)
- `wwiser -g bgm.bnk`
  (generates TXTP files from banks to use with vgmstream)
- `wwiser -h`
  (shows all available actions)

Loaded banks can be explored using the viewer, a web browser-based tool (if
you'd prefer a native GUI, please understand there are multiple reasons behind
this), or dumped to a file. For best results load `init.bnk` then one or more
related banks, since banks can point to data in other banks.

If companion files like *SoundbankInfo.xml* or *(bank name).txt* are found in the
`.bnk` dir they'll be automatically used to show names. *wwiser* also supports some
artificial ways to add reversed names (`wwnames.txt` and `wwnames.db3`).

Be aware that depending on the bank size loading may be slow, memory usage high,
dump output big, and *txtp* generation slow.

*wwiser* requires *Python* installed (tested with *python3*, recent *python2*
versions will probably/partially work). The viewer also needs a modern-ish browser.

See *doc/WWISER.md* for full info about various details. CLI also has a few extra
options for advanced users too, also see https://github.com/bnnm/wwiser-utils for
some extra stuff. If you need help try asking on hcs64.com forums or discord.


## WWISE ENGINE AND WWISER USAGE
**TL;DR**: Wwise never plays `.wem` directly and always uses *events* inside `.bnk`
that play one or many `.wem` indirectly. You want to open main `.bnk` (leaving
companion `xml` and `txt` files together to get names) with *wwiser*, maybe explore
a bit, and  automatically generate *TXTP* for *events*, to use with *vgmstream* to
play music (https://github.com/losnoco/vgmstream).

Wwise has two "modes", a sound engine that plays single sfx or tracks capable of simple
looping (some games loop like this), and a music engine that dynamically plays multiple
audio stems mixed in realtime (other games loop by using multiple separate files). You
want *TXTP* to handle the later, but they also give consistency and (sometimes) original
names to the former. In short, for games using Wwise audio don't play `.wem` but use
*wwiser*'s generated `.txtp`.


## WWISER OUTPUT
Web view or dumped `.xml` shows what is stored in `.bnk`, trying to follow original
(Audiokinetic's) names. Since Wwise is a complex engine it can be a bit hard to
understand at first. Most concepts are explained in *doc/WWISER.md*, though to get
most of it install Wwise (free) and play around with the editor.


## TXTP GENERATION
You can generate `.txtp` files from `.bnk` that allow *vgmstream* to (mostly) play audio
simulating Wwise. Make sure `.wem` go to the `/txtp/wem` folder and open `.txtp` with a
player like *foobar2000* or *Winamp* with the *vgmstream* plugin installed (or use *CLI*).
Language-specific `.wem` can be configured to go to `/txtp/wem/(language name)`. Older
games may use other extensions like `.wav/xma/ogg`, this is ok and taken into account.

Pay attention to WARNINGs in the log, as you may need to manually fix some issues that
can't be automated (usually loading multiple banks at once and re-generating). But
sometimes there is no way to fix and can be ignored, since `.bnk` may contain garbage.

If log complains about unused audio set an option to generation those, but only after
trying to load other banks, as results will be better that way (some banks could contain
audio while others contain "events", and you should load both to properly make .txtp).
Unused audio may end up generating nothing (leftover empty or repeated data that doesn't
play anything).

Main Wwise features missing in generated *TXTP* at the moment are:
- overlaps: when a songs changes section or loops, Wwise allows to play "post-exit"
  and "pre-entry" audio simultaneously, but .txtp just ignores those for now, making
  some transitions sound less smooth
- switch transitions: songs can dynamically change sections in real time via passed
  parameters in Wwise, but the generator can only use pre-set parameters
- different sample rates: Wwise can freely combine sample rates, but vgmstream needs
  to be updated to support this (some parts of the song will sound too fast)
- auto parameters: generator automatically makes combinations of parameters to create
  most possible songs, but some combos that play multiple songs simultaneously aren't
  created at the moment (made as separate songs, can be created by passing all
  parameters manually).
- songs with random files/variations: selected from a list and may change dynamically
  in Wwise (like on every loop), can only play pre-selected values (editable).
- multi-loops: Wwise can loop each element independently (since it's just "repeating"
  parts rather than "looping"), but .txtp doesn't (can be manually simulated by
  setting play time of each element manually, but needs a finite time).
- effects: Wwise can apply effects like pitch, panning and so on, none are simulated
- songs with unusual features like midis/sfx plugins can't play (too complex)
- volumes/silences: Wwise games sometimes silence or crossfade files while playing
  others, which isn't autodetected. Audio volume can also be set outside bank, so
  some songs may sound a bit quiet (try adding `#v 3.0dB` or more  to increate volume).

Watch out for filenames with:
- `{r}`: has random `.wem` (open and change `>1` to select random parts)
- `{s}`: may need to silence .wem that crossfade (put `?` in front of unwanted files)
- `{m}`: uses multi-loops (multiple places may loop, some may be fixed manually)
- `{e}`: uses "external IDs" (set at runtime so can't guess file, usually voices)
- `{!}`: missing audio (usually needs more .bnk or uses unsupported audio plugins)
- `{l=(lang)}`: only when flag to handle languages is set (use when multiple songs/sfx
   per language need to coexist coexist in same dir)

It's a good idea to keep the `.bnk` and companion files around in case `.txtp` need
to be generated again when more features are added.

Names are used from *loaded banks*'s companion files, load related files like `init.bnk`
to get names that .txtp may need. You can also create a name list in `wwnames.txt`
instead, see https://github.com/bnnm/wwiser-utils for some tips.


## LIMITATIONS
This tool is not, and will never be, a `.bnk` editor (can't replace files). It's only
meant to show bank data and generate TXTP. But feel free to use info here to make
other programs.

Almost all `.bnk` versions should work, except the first two, used in *Shadowrun (X360)*
and *Too Human (X360)*, report if you get errors or incorrect behavior. All fields should
be correctly identified and named, save a few bit flags in some versions and some lesser
objects like plugins.


## LEGAL STUFF
Everything from *wwiser* was researched and reverse-engineered by studying public
SDKs, executables and files, by bnnm.
