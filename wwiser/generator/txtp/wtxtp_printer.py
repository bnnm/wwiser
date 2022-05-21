import logging
from . import wtxtp_tree, wtxtp_simplifier


TXTP_SPACES = 1

DEBUG_PRINT_TREE_PRE = False
DEBUG_PRINT_TREE_POST = False
DEBUG_PRINT_GROUP_HEADER = False
# envelopes tend to make giant lines in some cases and vgmstream max line is ~1000, to be improved
DEBUG_PRINT_ENVELOPES = True
DEBUG_PRINT_ENVELOPES_LIMIT = 1800

GROUPS_TYPE = {
    wtxtp_tree.TYPE_GROUP_SINGLE: 'S',
    wtxtp_tree.TYPE_GROUP_SEQUENCE_CONTINUOUS: 'S',
    wtxtp_tree.TYPE_GROUP_SEQUENCE_STEP: 'S',
    wtxtp_tree.TYPE_GROUP_RANDOM_CONTINUOUS: 'R',
    wtxtp_tree.TYPE_GROUP_RANDOM_STEP: 'R',
    wtxtp_tree.TYPE_GROUP_LAYER: 'L',
}
GROUPS_INFO = {
    wtxtp_tree.TYPE_GROUP_SINGLE: 'single',
    wtxtp_tree.TYPE_GROUP_SEQUENCE_CONTINUOUS: 'sequence-continuous',
    wtxtp_tree.TYPE_GROUP_SEQUENCE_STEP: 'sequence-step',
    wtxtp_tree.TYPE_GROUP_RANDOM_CONTINUOUS: 'random-continuous',
    wtxtp_tree.TYPE_GROUP_RANDOM_STEP: 'random-step',
    wtxtp_tree.TYPE_GROUP_LAYER: 'layer',
}


VOLUME_DB_MAX = 200.0 # 96.3 #wwise editor typical range is -96.0 to +12 but allowed editable max is +-200

#******************************************************************************

# Takes the TXTP tree, simplifies and prints it. 

class TxtpPrinter(object):
    def __init__(self, txtp, tree):
        self._tree = tree
        self._txtp = txtp
        self._txtpcache = txtp.txtpcache

        # during write
        self._lines = None
        self._depth = None
        self._simpler = False   # when set skips some configs to ease comparing similar txtp
                                # (some games have an event + same softer or slightly delayed = useless)

        # during simplify
        self._simplifier = wtxtp_simplifier.TxtpSimplifier(self, txtp, tree)
        self.externals = []
        self.volume_auto = None

        # output flags (loaded during simplify or write)
        self.lang_name = None
        self.has_random_continuous = False
        self.has_random_steps = False   # some parts contain randoms
        self.has_silences = False       # may use silences to change/crossfade songs
        self.has_self_loops = False     # hack for smoother looping
        self.has_streams = False        # stream .wem
        self.has_internals = False      # internal .wem (inside .bnk)
        self.has_externals = False      # special "external sources"
        self.has_unsupported = False    # missing audio/unsupported plugins
        self.has_multiloops = False     # multiple layers have infinite loops
        self.has_others = False         # misc marks
        self.has_debug = False          # special mark for testing

        self.selectable_count = 0       # number of selectable (in the first node only), for flags below
        self.is_random_select = False   # has selectable random group
        self.is_multi_select = False    # has selectable multilooping group
        self.is_force_select = False    # has selectable forced group


    def prepare(self):
        self._modify()

    def generate(self, simpler=False):
        self._depth = 0
        self._lines = []
        self._simpler = simpler

        self._write()
        text = ''.join(self._lines)
        return text

    def has_sounds(self):
        return self._simplifier.has_sounds()


    #--------------------------------------------------------------------------

    # simplifies tree to simulate some Wwise features with TXTP
    def _modify(self):
        if DEBUG_PRINT_TREE_PRE:
            logging.info("*** tree pre:")
            self._mdepth = 0
            self._print_tree(self._tree, False)
            logging.info("")

        self._simplifier.modify()

        if DEBUG_PRINT_TREE_POST:
            logging.info("*** tree post:")
            self._mdepth = 0
            self._print_tree(self._tree, True)
            logging.info("")
        return


    def _print_tree(self, tnode, post):
        line1 = ''
        line2 = ''
        config1 = ''
        config2 = ''

        if post:
            if tnode.loop is not None:       config1 += " lpn=%s" % (tnode.loop)
            if tnode.volume:                 config1 += " vol=%s" % (tnode.volume)
            if tnode.ignorable():            config1 += " [i]"

            if tnode.body_time:              config2 += ' bt={0:.5f}'.format(tnode.body_time)
            if tnode.pad_begin:              config2 += ' pb={0:.5f}'.format(tnode.pad_begin)
            if tnode.trim_begin:             config2 += ' tb={0:.5f}'.format(tnode.trim_begin)
            if tnode.trim_end:               config2 += ' te={0:.5f}'.format(tnode.trim_end)
            if tnode.pad_end:                config2 += ' pb={0:.5f}'.format(tnode.pad_end)

        else:
            if tnode.config.loop is not None: config1 += " lpn=%s" % (tnode.config.loop)
            if tnode.config.delay:           config1 += " dly=%s" % (tnode.config.delay)
            if tnode.config.gain:          config1 += " vol=%s" % (tnode.config.gain)
            if tnode.transition:             config1 += " (trn)"

            if tnode.config.entry or tnode.config.exit:
                dur = '{0:.5f}'.format(tnode.config.duration)
                ent = '{0:.5f}'.format(tnode.config.entry)
                exi = '{0:.5f}'.format(tnode.config.exit)
                config2 += " (dur=%s, ent=%s, exi=%s)" % (dur, ent, exi)

            if tnode.sound and tnode.sound.clip:
                fsd = '{0:.5f}'.format(tnode.sound.fsd)
                fpa = '{0:.5f}'.format(tnode.sound.fpa)
                fbt = '{0:.5f}'.format(tnode.sound.fbt)
                fet = '{0:.5f}'.format(tnode.sound.fet)
                config2 += " (fsd=%s, fpa=%s, fbt=%s, fet=%s)" % (fsd, fpa, fbt, fet)

        if tnode.is_sound():
            tid = None
            if tnode.sound.source:
                tid = tnode.sound.source.tid
            line1 += "%s %s" % (tnode.type, tid)
            line1 += config1
            line2 += config2
        else:
            line1 += "%s%i" % (tnode.type, len(tnode.children))
            line1 += config1
            line2 += config2

        logging.info("%s%s", ' ' * self._mdepth, line1)
        if line2:
            logging.info("%s%s", ' ' * self._mdepth, line2)


        self._mdepth += 1
        for subtnode in tnode.children:
            self._print_tree(subtnode, post)
        self._mdepth -= 1

    #--------------------------------------------------------------------------

    # prints tree as a .txtp
    def _write(self):
        # generic nodes
        self._write_node(self._tree)
        self._lines.append('\n')

        self._write_commands()
        return

    def _write_commands(self):
        # apply increasing master volume after all other volumes
        # (lowers chances of clipping due to vgmstream's pcm16)
        vol = self._simplifier.volume_master
        if vol and vol > 0 and not self._simpler:
            line = 'commands = #v %sdB' % (vol)
            self._lines.append('%s\n' % (line))
        return

    def _write_node(self, tnode):
        if not tnode.ignorable(simpler=self._simpler):
            self._depth += 1

        if   tnode.is_sound():
            self._write_sound(tnode)
        elif tnode.is_group():
            self._write_group_header(tnode)

        for subnode in tnode.children:
            self._write_node(subnode)

        # TXTP groups need to go to the end
        if tnode.is_group():
            self._write_group(tnode)

        if not tnode.ignorable(simpler=self._simpler):
            self._depth -= 1

        # set flag with final tree since randoms of a single file can be simplified
        if tnode.is_group_random_continuous() and len(tnode.children) > 1:
            self.has_random_continuous = True
        if tnode.is_group_steps() and len(tnode.children) > 1:
            self.has_random_steps = True
        if tnode.silenced or tnode.crossfaded:
            self.has_silences = True


    # make a TXTP group
    def _write_group(self, tnode):
        #ignore dumb nodes that don't contribute (children are output though)
        if tnode.ignorable(simpler=self._simpler):
            return

        # ex. -L2: at position N (auto), layers previous 2 files
        type_text = GROUPS_TYPE[tnode.type]
        count = len(tnode.children)
        ignored = False #self._ignore_next #or count <= 1 #allow 1 for looping full segments

        line = ''
        mods = ''
        info = ''
        if ignored:
            line += '#'

        # add base group
        line += 'group = -%s%s' % (type_text, count)
        if    tnode.is_group_steps() or tnode.force_selectable:
            selection = self._txtp.selected or 1
            line += '>%s' % (selection)
            #info += "  ##select >N of %i" % (count)
        elif tnode.is_group_random_continuous(): #not for sequence since it looks a bit strange
            line += '>-'

        # volume before layers, b/c vgmstream only does PCM ATM so audio could peak if added after
        volume = tnode.volume or 0
        if self._simpler:
            volume = 0
        if self._txtpcache.silence or tnode.silenced:
            mods += '  #v 0'
        elif volume:
            mods += '  #v %sdB' % (volume)

        # wwise seems to mix untouched then use volumes to tweak
        if tnode.is_group_layers():
            mods += ' #@layer-v'

        # add delay config
        if not self._simpler:
            mods += self._get_ms(' #p', tnode.pad_begin)


        # add loops/anchors
        if tnode.loop is not None: #and node.loop_anchor: #groups always use anchors
            if   tnode.loop == 0:
                mods += ' #@loop'
                if tnode.loop_end:
                    mods += ' #@loop-end'
            elif tnode.loop > 1:
                mods += ' #E #l %i.0' % (tnode.loop)


        # extra info
        if tnode.loop_killed:
            info += '  ##loop'
            if tnode.loop_end:
                info += ' #loop-end'

        if tnode.crossfaded or tnode.silenced:
            info += '  ##fade'
            self.has_others = True

        # final result
        pad = self._get_padding() #padded for clarity
        self._lines.append('%s%s%s%s\n' % (pad, line, mods, info))


    # make a TXTP group header
    def _write_group_header(self, tnode):
        if not DEBUG_PRINT_GROUP_HEADER:
            return #not too useful
        if tnode.ignorable(simpler=self._simpler):
            return

        line = ''

        line += '#%s of %s' % (GROUPS_INFO[tnode.type], len(tnode.children))
        if tnode.loop is not None:
            if   tnode.loop == 0:
                line += ' (N loops)'
            elif tnode.loop > 1:
                line += ' (%i loops)' % (tnode.loop)

        pad = self._get_padding()
        self._lines.append('%s%s\n' % (pad, line))


    # write a TXTP sound wem
    def _write_sound(self, tnode):
        sound = tnode.sound
        ignored = False #self._ignore_next

        line = ''
        mods = ''
        info = ''
        if ignored:
            line += '#'
        silence_line = False

        name = ''
        if sound.source and sound.source.plugin_wmid:
            name += '?'
            self.has_unsupported = True

        name += self._txtpcache.wemdir
        if sound.source and self._txtpcache.lang:
            lang = sound.source.lang()
            if lang: #in case it's blank for some sources yet filled for others
                self.lang_name = lang
            name += sound.source.subdir()

        # add source
        if   sound.silent:
            #silent/empty subtrack (ignored)
            name = "?.silent"

        elif sound.source.plugin_id:
            # generator plugin
            name = "?.plugin-%s" % (sound.source.plugin_name)

            if sound.source.is_plugin_silence:
                mods += self._get_ms(' #B', sound.source.plugin_fx.duration)
            else:
                self.has_unsupported = True

        elif sound.source.plugin_external:
            # "external" ID (set at runtime)
            if self._txtp.external_path:
                # set during txtp process
                name = "%s" % (self._txtp.external_path)
            else:
                # unknown
                name = "?" + name
                name += "(?).wem"

            # external tid (a hashname) seems shared for multiple objects, needs to print object's sid to avoid being dupes
            info += "  ##external %s [obj %s]" % (sound.source.tid, sound.source.src_sid)

        elif sound.source.internal and not self._txtpcache.bnkskip:
            # internal/memory stream
            bankname = sound.nsrc.get_root().get_filename()
            media = self._txtpcache.mediaindex.get_media_index(bankname, sound.source.tid)
            extension = sound.source.extension
            if self._txtpcache.alt_exts:
                extension = sound.source.extension_alt

            if media:
                bankname, index = media
                name += "%s #s%s" % (bankname, index + 1)
                info += "  ##%s.%s" % (sound.source.tid, extension) #to check source in info tree
                if sound.source.plugin_wmid:
                    info += " ##unsupported wmid"
            else:
                name = "?" + name + "%s.%s" % (sound.source.tid, extension)
                info += "  ##other bnk?"
                self.has_unsupported = True
            self.has_internals = True
            self._txtpcache.stats.register_bank(bankname)

        else:
            # regular stream
            extension = sound.source.extension
            if self._txtpcache.alt_exts:
                extension = sound.source.extension_alt

            name += "%s.%s" % (sound.source.tid, extension)
            self.has_streams = True


        line += name

        # add config
        if sound.clip: #CAkMusicTrack's clip
            mods += self._get_clip(sound, tnode)
        else: #CAkSound
            mods += self._get_sfx(sound, tnode)

        # add envelopes
        if tnode.envelopes:
            # ch(type)(position)(time-start)+(time-length)
            # N^(volume-start)~(volume-end)=(shape)@(time-pre)~(time-start)+(time-length)~(time-last)
            if DEBUG_PRINT_ENVELOPES:
                info_envs = ''
                #TODO: some games add too many envelopes making huge lines that are ignored by vgmstream
                # (Tetris Beat on Apple Arcade: Play_Music [Music=Hydra] (MUSIC_PROGRESS=FULL_SONG), Jedi Fallen Order)
                for envelope in tnode.envelopes:
                    vol_st = self._get_sec(envelope.vol1)
                    vol_ed = self._get_sec(envelope.vol2)
                    shape = envelope.shape
                    time_st = self._get_sec(envelope.time1)
                    time_ed = self._get_sec(envelope.time2)
                    #TODO: seems to reapply on loops (time becomes 0 again)
                    info_env = ' ##m0^%s~%s=%s@-1~%s+%s~-1' %  (vol_st, vol_ed, shape, time_st, time_ed)
                    info_envs += info_env
                    if len(info_envs) >= DEBUG_PRINT_ENVELOPES_LIMIT:
                        info_envs += ' ##(...)'
                        break
                info += info_envs
            else:
                # rarely there are .txtp clones with fading and non-fading paths, ignore for now [Pokemon BDSP, Death Stranding]
                #info += ' ##envelopes'
                pass

        # add volume
        volume = tnode.volume or 0
        if self._simpler and not tnode.crossfaded: #don't silence rtpc-modified vars
            volume = 0
        if self._txtpcache.silence or tnode.silenced:
            silence_line = True #set "?" below as it's a bit simpler to use
        if volume:
            mods += '  #v %sdB' % (volume)

        # add anchors
        if tnode.loop_anchor:
            mods += ' #@loop'
            if tnode.loop_end:
                mods += ' #@loop-end'


        # extra info
        if tnode.loop_killed:
            info += '  ##loop'
            if tnode.loop_end:
                info += ' #loop-end'

        if tnode.crossfaded or tnode.silenced:
            info += '  ##fade'

        if silence_line:
            line = "?" + line

        # final result
        pad = self._get_padding() #padded for clarity
        self._lines.append('%s%s%s%s\n' % (pad, line, mods, info))


    def _get_sfx(self, sound, node):
        #sfx are mostly pre-modified before generation, so main config is looping
        mods = ''

        # we don't go parsing whole .wems to figure out loops so always write flags
        # (rarely .wem has loop points while loop is not set at all, but must not loop to play ok)
        if node.loop is None or node.loop == 1:
            mods += ' #i'
        else:
            #uses internal loops if set, or full loops otherwise
            if not self._txtpcache.x_noloops: #force disable as some games don't seem to follow this (KOF12/13)
                mods += ' #e'
            # 0=infinite
            if node.loop > 1:
                mods += ' #l %s.0' % (node.loop)

        # add delay config (remove for comparision if flag is set)
        if not self._simpler:
            mods += self._get_ms(' #p', node.pad_begin)

        return mods


    def _get_clip(self, sound, tnode):
        mods = ''

        # final body time goes over 1 loop (not using loop flag since it seems to depend on final trim, see examples)
        # some files slightly over duration (ex. 5000 samples) and are meant to be looped as segments, it's normal

        loops = not sound.silent and tnode.body_time - tnode.trim_end > sound.fsd  # trim_begin not included

        if sound.silent:
            pass
        elif loops:
            mods += ' #E' #clips only do full loops
        else:
            mods += ' #i' #just in case

        #clips don't have delay and don't need it removed when _simpler is set

        mods += self._get_ms(' #p', tnode.pad_begin)
        if loops: #forces disabling fades, that get in the way when playing separate music tracks
            mods += self._get_ms(' #B', tnode.body_time)
        else:
            mods += self._get_ms(' #b', tnode.body_time)
        mods += self._get_ms(' #r', tnode.trim_begin)
        mods += self._get_ms(' #R', tnode.trim_end)
        mods += self._get_ms(' #P', tnode.pad_end)

        return mods

    def _get_float_str(self, value_sec):
        if not value_sec:
            return ''
        value_str = str(value_sec) #default, no 0 padding
        if 'e' in value_str:
            # has scientific notation, use format to fix/truncate (9.22e-06 > 0.0000092213114704)
            # there may be some precission loss but shouldn't matter (wwise doesn't seem to round up)
            value_str = '{0:.10f}'.format(value_sec)
            if not float(value_str): # truncated result may be 0.000000
                return ''
        #todo ignore trims that end up being 0 samples (value * second = sample)

        return value_str

    def _get_ms(self, param, value_ms):
        if not value_ms:
            return ''
        value_sec = value_ms / 1000

        # useful when 2 musictrack using the same are slightly different?
        # (ex. AC:B BORGIATOWERS 149.341643661262 vs 149.34014099656)
        #if self._simpler:
        #    value_sec = round(value_sec, 2)

        value_str = self._get_float_str(value_sec)
        if not value_str:
            return ''
        out = '%s %s' % (param, value_str)
        return out

    def _get_sec(self, value_sec):
        value_str = self._get_float_str(value_sec)
        if not value_str:
            return '0.0'
        return value_str


    def _get_padding(self):
        return ' ' * (self._depth - 1) * TXTP_SPACES
