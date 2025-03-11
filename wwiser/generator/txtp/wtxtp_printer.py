from . import wtxtp_tree, wtxtp_simplifier


_TXTP_INDENTATION_SPACES = 1

_DEBUG_PRINT_GROUP_HEADER = False
# envelopes tend to make giant lines in some cases and vgmstream max line is ~2000, adjust as needed
_ENVELOPES_LIMIT = 1800
# many sounds are problematic due to txtp/filesystem limit, mark as {!}
_SOUNDS_LIMIT = 150


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
        self.has_streams = False        # stream .wem
        self.has_internals = False      # internal .wem (inside .bnk)
        self.has_externals = False      # special "external sources"
        self.has_unsupported = False    # missing audio/unsupported plugins
        self.has_multiloops = False     # multiple layers have infinite loops
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
        return self._simplifier.get_sounds_count() > 0

    def has_many_sounds(self):
        return self._simplifier.get_sounds_count() > _SOUNDS_LIMIT

    def ignore_silenced(self, tnode):
        return self._simplifier.get_sounds_count() == 1 and tnode.silenced_default

    def is_crossfading_multiple(self):
        return self.has_silences and self._simplifier.get_sounds_count() > 1

    #--------------------------------------------------------------------------

    # simplifies tree to simulate some Wwise features with TXTP
    def _modify(self):
        self._simplifier.modify()
        return

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
        if tnode.crossfaded or tnode.silenced:
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

        # add volume (before layers, b/c vgmstream only does PCM ATM so audio could peak if added after)
        volume = tnode.volume or 0
        if self._simpler and not tnode.crossfaded: #don't silence rtpc-modified vars
            volume = 0
        if self._txtpcache.x_silence_all:
            mods += '  #v 0'
        elif volume:
            mods += '  #v %sdB' % (volume)

        # wwise seems to mix untouched then use volumes to tweak
        if tnode.is_group_layers():
            mods += ' #@layer-v'

        # add config
        if not self._simpler:
            mods += self._get_ms(' #p', tnode.pad_begin) #for delays

        #for special start..entry clamp
        mods += self._get_ms(' #B', tnode.body_time)
        mods += self._get_ms(' #r', tnode.trim_begin)

        # add envelopes
        envs_mods, envs_info = self._get_envelopes(tnode)
        mods += envs_mods
        info += envs_info

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

        if tnode.fake_entry:
            info += '  ##fake-entry'

        # final result
        pad = self._get_padding() #padded for clarity
        self._lines.append('%s%s%s%s\n' % (pad, line, mods, info))


    # make a TXTP group header
    def _write_group_header(self, tnode):
        if not _DEBUG_PRINT_GROUP_HEADER:
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

        # sometimes midis are used as bgm, but also used to sync stuff (silent)
        if sound.source and sound.source.plugin_wmid:
            name += '?'
            if not tnode.silenced:
                self.has_unsupported = True


        # prepare lang for some cases
        lang_fullname = ''
        if sound.source and self._txtpcache.lang:
            lang_fullname = sound.source.lang_fullname()
            if lang_fullname and lang_fullname != 'SFX': #in case it's blank for some sources yet filled for others
                self.lang_name = sound.source.lang_shortname()


        # add source
        if   sound.silent:
            #silent/empty subtrack (ignored)
            name = "?.silent"

        elif not sound.source:
            #rare (ZoE2 HD)
            name = "?.missing"

        elif sound.source.plugin_id is not None:
            # generator plugin
            name = "?.plugin-%s" % (sound.source.plugin_name)

            if   sound.source.is_plugin_silence and sound.source.plugin_fx:
                mods += self._get_ms(' #B', sound.source.plugin_fx.duration)
            elif sound.source.is_plugin_silence or tnode.silenced: # plugin "none" has no fx
                pass
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
            mdi = self._txtpcache.mediaindex
            media = mdi.get_media_index(bankname, sound.source.tid)
            extension = sound.source.extension
            if self._txtpcache.alt_exts:
                extension = sound.source.extension_alt

            if media and self._simpler:
                # when finding dupes we want to ignore bank origins were same sounds are loaded in multiple .bnk
                # (would be technically possible that 2 .wem in .bnk share same id but content differs, extremely unlikely though)
                bankname, index = media
                #name += self._txtpcache.locator.find_bnk_path(bankname, lang_fullname)
                name += 'banks/' #sometimes id repeat between banks in different localization dirs
                name += "%s.%s" % (sound.source.tid, extension)
                #info += "  ##%s #s%s" % (bankname, index + 1) #matters for dupes
            elif media:
                bankname, index = media
                name += self._txtpcache.locator.find_bnk_path(bankname, lang_fullname)
                name += "%s #s%s" % (bankname, index + 1)
                info += "  ##%s.%s" % (sound.source.tid, extension) #to check source in info tree
            elif sound.source.internal_ebp:
                # memory audio in UE4 may be in a RAM .uasset, but .bnk has no way to known this so allow as loose .wem
                name += self._txtpcache.locator.find_wem_path(sound.source.tid, extension, lang_fullname)
                name = name + "%s.%s" % (sound.source.tid, extension)
                info += "  ##memory"
                mdi.set_event_based_packaging(True)
            else:
                # old memory audio must be in a bnk
                name = "?" + name + "%s.%s" % (sound.source.tid, extension)
                info += "  ##other bnk?"
                self.has_unsupported = True

            if sound.source.plugin_wmid:
                info += " ##unsupported wmid"

            self.has_internals = True
            self._txtpcache.stats.register_bank(bankname)

        else:
            # regular stream
            extension = sound.source.extension
            if self._txtpcache.alt_exts:
                extension = sound.source.extension_alt

            name += self._txtpcache.locator.find_wem_path(sound.source.tid, extension, lang_fullname)
            name += "%s.%s" % (sound.source.tid, extension)
            self.has_streams = True

        if sound.unreachable:
            name = "#" + name
            info += " ##unreachable"


        line += name

        # in rare cases there is a single silenced wem, detect and don't silence (DMC5's play_m22_dojo)
        ignore_silenced = self.ignore_silenced(tnode)

        # add config
        if sound.clip: #CAkMusicTrack's clip
            mods += self._get_clip(sound, tnode)
        else: #CAkSound
            mods += self._get_sfx(sound, tnode)

        # add volume
        volume = tnode.volume or 0
        if self._simpler and not tnode.crossfaded: #don't silence rtpc-modified vars
            volume = 0
        if self._txtpcache.x_silence_all or tnode.silenced and not ignore_silenced:
            silence_line = True #set "?" below as it's a bit simpler to use
        if volume:
            if ignore_silenced: # with auto-volume on this volume gets removed, but anyway:
                info += '  ##v %sdB' % (volume)
            else:
                mods += '  #v %sdB' % (volume)

        # add anchors
        if tnode.loop_anchor:
            mods += ' #@loop'
            if tnode.loop_end:
                mods += ' #@loop-end'

        # add envelopes
        envs_mods, envs_info = self._get_envelopes(tnode)
        mods += envs_mods
        info += envs_info

        # extra info
        if tnode.loop_killed:
            info += '  ##loop'
            if tnode.loop_end:
                info += ' #loop-end'

        if tnode.crossfaded or tnode.silenced:
            info += '  ##fade'

        if tnode.fake_entry:
            info += '  ##fake-entry'

        if silence_line:
            line = "?" + line

        # final result
        pad = self._get_padding() #padded for clarity
        self._lines.append('%s%s%s%s\n' % (pad, line, mods, info))


    def _get_envelopes(self, tnode):
        mods = ''
        info = ''

        if not tnode.envelopelist or tnode.envelopelist.empty:
            return (mods, info)

        if self._simpler:
            # rarely there are .txtp clones with fading and non-fading paths [Pokemon BDSP, Death Stranding]
            pass
        else:
            # ch(type)(position)(time-start)+(time-length)
            # N^(volume-start)~(volume-end)=(shape)@(time-pre)~(time-start)+(time-length)~(time-last)
            envs = ''
            for envelope in tnode.envelopelist.items():
                vol_st = self._get_sec(envelope.vol1)
                vol_ed = self._get_sec(envelope.vol2)
                shape = envelope.shape
                time_st = self._get_sec(envelope.time1)
                time_ed = self._get_sec(envelope.time2)
                env = ' #m0^%s~%s=%s@-1~%s+%s~-1' %  (vol_st, vol_ed, shape, time_st, time_ed)
                envs += env

                # some games add too many envelopes making huge lines, and vgmstream has a "reasonable line" limit
                # (Tetris Beat on Apple Arcade: Play_Music [Music=Hydra] (MUSIC_PROGRESS=FULL_SONG), Jedi Fallen Order)
                if len(envs) >= _ENVELOPES_LIMIT:
                    info += ' ##more envelopes...'
                    break
            mods += envs

        return (mods, info)

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

        # clips don't have delay and don't need it removed when _simpler is set
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
        #TODO ignore trims that end up being 0 samples (value * second = sample)

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
        return ' ' * (self._depth - 1) * _TXTP_INDENTATION_SPACES
