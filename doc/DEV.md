# WWISER DEV INFO


## OVERVIEW
Wwiser is roughly divided in "components" that do certain jobs. Most are somewhat separate, but
a full course of action would be:
- open .bnk file
- make *IO reader*: pass file
- make *parser*: pass *io*, create *model* tree
- open *names*: read companion name files
- pass *names* to *parser*
- make *printer*: pass *parser*, write *model* tree
- make *viewer*: pass *parser*, print tree nodes on demand
- make *generator*: pass *parser*, analyze and generate *.txtp*


## COMPONENTS
A general rundown of wwiser internals:

### CLI
Simple client interfase. Opens and manages other components depending on to CLI commands.

### GUI
Simple GUI, mostly the same as CLI but simplified (less options).

### IO
Simple file reading encapsulation.

### MODEL
A generic a tree/xml-like structure of nodes ("objects", "lists", "fields", etc), tuned to read the bank
file with the IO reader.

### PARSER
Reads a .bnk and creates a bank tree. This generic structure then can be used for other components to do their thing.

This was developed by analyzing SDK decompilations and somewhat trying to follow original code along. It was simply too time consuming to analyze, understand and reinterpret every single thing. As a result, I don't actually know every field or anything, but I can see if parser is correct by checking that it handles the same things as the SDK, in the correct order. This is also why it uses a generic tree rather than proper classes (much faster to create, test and modify).

### DEFS/CLS
Companion info/constants for the parser.

### PRINTER
Takes the Parser and writes current banks as a xml/text/etc file. Basically follows the generic bank tree along and prints nodes as found, nothing fancy. Mostly to debugging and test banks, as the viewer is meant to print nodes in different ways.

### NAMES
Reads companion files/databases and creates a list of possible names to be used by the parser (ID=name). This is then injected to the parser, so it automatically shows names as attributes in the tree nodes that have an ID.

### VIEWER
Web server that shows the Parser node tree as HTML. Base .html interacts with the crude server requesting printed nodes via AJAX, that are created with a dumb templating engine (home-baked rather than a known engine for simplicity, to minimize dependencies, and for fun too).

A pure python GUI was ultimate dismissed, as using CSS+HTML+JS was much more flexible (plus ubiquitous) and having to learn a new, probably limited GUI would end up being time consuming and unmaintainable. The html design was also repurposed from the Printer's test XML output to save time.

### GENERATOR
Takes the Parser tree and tries to build .txtp files to play with vgmstream. Because how Wwise internally works (objects point to objects based on config) there is quite a bit of jumping around. A bunch of helper classes are used to create simplified .txtp trees from the parser tree, that ultimately makes text files.

Base generator populates a "rebuilder", where parser nodes are read and simplified a bit with direct field access to ease handling. Then those rebuilt nodes start adding parts to a TXTP helper, calling their descendants and sound nodes until the whole path is parsed. The helper in turn makes a tree of simpler nodes, that are ultimately post-processed to make a final .txtp (some extra info is gathered and printer
to the .txtp too.

Because the huge amount of features Wwise has that vgmstream lacks, this component is most incomplete, unlike others. Particularly, some things are ignored and others are simplified to be more suitable with vgmstream's features. Since it was also the hardest part, code is kind of chaotic as I was randomly tumbling around.


## OTHER NOTES

Random thoughts:
- I (bnnm) barely know/knew python, so code shouldn't be taken as a good example of the language or software engineering practices, as I was often trying stuff along
- python was mainly chosen for its good prototyping/quick iteration powerz, and being common enough for users
- key milestones are/were: parser > names > visualizer > generator, and were developed as such
- code was written prioritizing dev speed over orderly design, stuff came along as needed. That is to say, it was more important to churn out something viable, usable and testable (as the whole thing is no easy task) than slowly making the best thing ever. As a result lots of code isn't too great, but good enough and done is better than perfect but pending.
- packages aren't very organized until I figure out that mess
- some parts were mix and matched from small .py tests around, not too consistent
- codebase isn't considered stable and may change anytime on a whim
