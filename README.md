# WWISER
A Wwise `.bnk` parser, to assist in handling audio from games using the Wwise engine.

Simply open `wwiser` without arguments to start the GUI. From there you can load
and view banks, dump contents or make TXTP (used to simulate audio). It reads
and shows all `.bnk` chunks, including *HIRC* (audio scripting) data, and properly
identifies all fields. *wwiser* *can't* modify banks.


## MINI GUIDE
How to play audio simulating the Wwise engine:
- open *wwiser.pyz*
- press *Load dirs...* and select a *base folder* with `.bnk` and `.wem` inside
  - if you have `.pck`, use *Quickbms* + [this script](https://github.com/bnnm/wwiser-utils/blob/master/scripts/wwise_pck_extractor.bms) to extract `.wem`/`.bnk` first
  - if game has `SoundbanksInfo.xml`, `Wwise_IDs.h`, `(bankname).txt` or similar files you will have (some) names
  - or make/download a [name list](https://github.com/bnnm/wwiser-utils/tree/master/wwnames) put it as `wwnames.txt` in the *base folder*
- press *Generate TXTP* to make `.txtp` in the *base folder*
  - may need to fiddle with some options, such as setting language to `SFX` to skip voice lines
- open those `.txtp` with some player like *foobar2000/winamp/audacious* with the *vgmstream* plugin installed (or use the CLI tool)
  - this plays `.wem` closer to how they sound in-game (such as having multiple `.wem` at once if needed)
  - it may be more usable to set *TXTP subdir* to *empty* so that `.txtp` are generated in the *base folder* instead of a subfolder
  - note that *TXTP* currently can't simulate all Wwise features

You can also press *View banks* to explore, or *Dump banks* to save (somewhat) readable info, but isn't important to generate *TXTP*.

Wwise is very complex so this program can only help so much, you may need to read and understand *doc/WWISER.md* to get the full picture.


## OTHER INFO
All actions (and more) can be done from the command line as well: `wwiser [options] (files)`
- `wwiser bgm.bnk`
  - (dumps `bgm.bnk` info to `bgm.bnk.xml`)
- `wwiser -d txt init.bnk bgm.bnk -dn banks.txt`
  - (loads multiple `.bnk`, like Wwise does, and dumps to banks.txt)
- `wwiser *.bnk -r -v`
  - (loads all .bnk in current folder and subfolders recursively and starts the viewer)
- `wwiser -g bgm.bnk`
  - (generates TXTP files from banks to use with vgmstream)
- `wwiser wwconfig.txt`
  - (loads a text list of any CLI commands, to simplify complex usage)
- `wwiser -h`
  - (shows all available actions)

Loaded banks can be explored using the *viewer*, a web browser-based tool (if you'd
prefer a native GUI, please understand there are multiple reasons behind this),
or dumped to a file. For best results make sure to load `init.bnk` then one or more
related banks, since banks can point to data in other banks.

If companion files like *SoundbankInfo.xml* or *(bank name).txt* are found in the
`.bnk` dir they'll automatically be used to show names. *wwiser* also supports some
artificial ways to add reversed names (`wwnames.txt` and `wwnames.db3`).

Be aware that depending on the bank size loading may be slow, memory usage high,
dump output big, and *txtp* generation slow. Dumped `.xml` can be opened with a
browser to see contents (like a simple html/GUI) but since they can be huge 
browsers may run out of memory; the *viewer* is a safer bet (looks the same).

*wwiser* requires *Python 3* installed. The viewer also needs a modern-ish browser.

Extra info:
- *doc/WWISER.md*: detailed Wwise info and usage explanations
- wwiser-utils (https://github.com/bnnm/wwiser-utils): info and helpers for audio rips
- For further help try asking on hcs64.com forums or discord


## WWISE ENGINE AND WWISER USAGE
**TL;DR**: Wwise never plays `.wem` directly and always uses *events* inside `.bnk`
that play one or many `.wem` indirectly. You want to open main `.bnk` (leaving
companion `xml` and `txt` files together to get names) with *wwiser*, maybe explore
a bit, and  automatically generate *TXTP* for *events*, to use with *vgmstream* to
play music (https://github.com/vgmstream/vgmstream).

Wwise has two "modes", a sound module that plays single sfx or tracks capable of
simple looping (some games loop like this), and a music module that dynamically
plays multiple audio stems mixed in realtime (other games loop by using multiple
separate files). You want *TXTP* to handle the later, but they also give consistency
and (sometimes) original names to the former. In short, for games using Wwise audio
don't play `.wem` directly but use *wwiser*'s generated `.txtp`.


## WWISER OUTPUT
Web view or dumped `.xml` shows what is stored in `.bnk`, trying to follow original
(Audiokinetic's) names. Since Wwise is a complex engine it can be a bit hard to
understand at first. Most concepts are explained in *doc/WWISER.md*, though to get
most of it install Wwise (free) and play around with the editor to get a better feel
of how Wwise deals with audio.


## TXTP GENERATION
You can generate `.txtp` files from `.bnk` that allow *vgmstream* to (mostly) play audio
simulating Wwise. Make sure `.wem` go to the `/txtp/wem` folder and open `.txtp` with a
player like *foobar2000* or *Winamp* with the *vgmstream* plugin installed (or use 
vgmstream's *CLI* tools).

This function tries its best to make good, usable `.txtp` to improve the listening
experience of Wwise audio rips (like giving names when possible, or handling
complex loops). However Wwise is a very complex, dynamic audio engine, so you may
need to tweak various options to improve output. *vgmstream* also has some limitations
and audio simulation is not always perfect.

See *WWISER* doc for detailed explanations.


## LIMITATIONS
This tool is not, and will never be, a `.bnk` editor (can't replace files). It's only
meant to show bank data and generate TXTP. But feel free to use info here to make
other programs.

Almost all `.bnk` versions should work, except the first two, used in *Shadowrun (X360)*
(unsupported) and *Too Human (X360)* (mostly supported but can't make .txtp). Report if
you get errors or incorrect behavior. All fields should be correctly identified and named,
save a few bit flags in some versions and some lesser objects like plugins.


## LEGAL STUFF
Everything from *wwiser* was researched and reverse-engineered by studying public
SDKs, executables and files, by bnnm.
