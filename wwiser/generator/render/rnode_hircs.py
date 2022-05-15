from . import bnode_misc
from .rnode_base import RN_CAkHircNode


#non-audio node, doesn't contribute to txtp
class RN_CAkNone(RN_CAkHircNode):
    
    def _render_base(self, bnode, txtp):
        #don't print node info in txtp
        return

    #def _render_txtp(self, txtp):
    #    return

#******************************************************************************

class RN_CAkEvent(RN_CAkHircNode):

    def _render_txtp(self, bnode, txtp):
        # N play actions are layered (may set a delay)
        txtp.group_layer(bnode.ntids, bnode.config)
        for ntid in bnode.ntids:
            self._render_next(ntid, txtp)
        txtp.group_done(bnode.ntids)
        return

#******************************************************************************

class RN_CAkDialogueEvent(RN_CAkHircNode):

    def _render_txtp(self, bnode, txtp):

        if bnode.ntid:
            # tree plays a single object with any state
            txtp.group_single(bnode.config)
            self._render_next(bnode.ntid, txtp)
            txtp.group_done()
            return

        if not bnode.tree:
            return 

        if not txtp.params:
            # find all possible gamesyncs paths (won't generate txtp)
            for path, ntid in bnode.tree.paths:
                unreachable = txtp.ppaths.adds(path)
                if not unreachable:
                    self._render_next(ntid, txtp)
                txtp.ppaths.done()
            return

        # find if current gamesync combo matches one of the paths
        npath_combo = bnode.tree.get_npath(txtp.params)
        if npath_combo:
            npath, ntid = npath_combo
            txtp.info.gamesyncs(npath)

            txtp.group_single(bnode.config)
            self._render_next(ntid, txtp)
            txtp.group_done()
        return

#******************************************************************************

class RN_CAkAction(RN_CAkHircNode):
    pass

#******************************************************************************

class RN_CAkActionPlayAndContinue(RN_CAkAction):
    pass

#******************************************************************************

class RN_CAkActionTrigger(RN_CAkAction):

    def _render_txtp(self, bnode, txtp):
        # Trigger calls current music object (mranseq/mswitch usually) defined CAkStinger,
        # which in turn links to some segment and stops.
        # Trigger events may come before CAkStingers, and one trigger may call
        # stingers from any song (1 trigger > N stingers), so they are handled
        # separatedly during mranseq/mswitch.

        #logging.info("generator: trigger %i not implemented", self.sid)
        return

#******************************************************************************

class RN_CAkActionPlay(RN_CAkAction):

    def _render_txtp(self, bnode, txtp):
        txtp.group_single(bnode.config) # rare but may contain config
        self._render_next(bnode.ntid, txtp, bnode.nbankid)
        txtp.group_done()
        return

#******************************************************************************

class RN_CAkActionPlayEvent(RN_CAkActionPlay): #RN_CAkActionPlay
    pass

#******************************************************************************

class RN_CAkSwitchCntr(RN_CAkHircNode):

    def _render_txtp(self, bnode, txtp):
        gtype = bnode.gtype
        gname = bnode.ngname.value()

        if not txtp.params:
            # find all possible gamesyncs paths (won't generate txtp)
            for ntids, ngvalue in bnode.gvalue_ntids.values(): #order doesn't matter
                gvalue = ngvalue.value()
                unreachable = txtp.ppaths.add(gtype, gname, ngvalue.value())
                if not unreachable:
                    for ntid in ntids:
                        self._render_next(ntid, txtp)
                txtp.ppaths.done()
            return

        #get current gamesync
        gvalue = txtp.params.current(gtype, gname)
        if gvalue is None:
            return
        if not gvalue in bnode.gvalue_ntids: #exact match (no * like MusicSwitches)
            return
        ntids, ngvalue = bnode.gvalue_ntids[gvalue]


        txtp.info.gamesync(gtype, bnode.ngname, ngvalue)
        txtp.group_layer(ntids, bnode.config)
        for ntid in ntids: #multi IDs are possible but rare (KOF13)
            self._render_next(ntid, txtp)
        txtp.group_done()
        return

#******************************************************************************

class RN_CAkRanSeqCntr(RN_CAkHircNode):

    def _render_txtp(self, bnode, txtp):

        if   bnode.mode == 0 and bnode.continuous: #random + continuous (plays all objects randomly, on loop/next call restarts)
            txtp.group_random_continuous(bnode.ntids, bnode.config)

        elif bnode.mode == 0: #random + step (plays one object at random, on next call plays another object / cannot loop)
            txtp.group_random_step(bnode.ntids, bnode.config)

        elif bnode.mode == 1 and bnode.continuous: #sequence + continuous (plays all objects in sequence, on loop/next call restarts)
            txtp.group_sequence_continuous(bnode.ntids, bnode.config)

        elif bnode.mode == 1: #sequence + step (plays one object from first, on next call plays next object / cannot loop)
            txtp.group_sequence_step(bnode.ntids, bnode.config)

        else:
            self._barf('unknown ranseq mode')

        for ntid in bnode.ntids:
            self._render_next(ntid, txtp)
        txtp.group_done(bnode.ntids)

        return

#******************************************************************************

class RN_CAkLayerCntr(RN_CAkHircNode):

    def _render_txtp(self, bnode, txtp):
        txtp.group_layer(bnode.ntids, bnode.config)
        for ntid in bnode.ntids:
            self._render_next(ntid, txtp)
        txtp.group_done(bnode.ntids)
        return

#******************************************************************************

class RN_CAkSound(RN_CAkHircNode):

    def _render_txtp(self, bnode, txtp):
        txtp.info.source(bnode.sound.nsrc, bnode.sound.source)
        txtp.source_sound(bnode.sound, bnode.config)
        return

#******************************************************************************

class RN_CAkMusicSwitchCntr(RN_CAkHircNode):

    def _render_txtp(self, bnode, txtp):
        self._register_transitions(txtp, bnode.ntransitions)

        if bnode.ntid:
            # rarely tree plays a single object with any state
            txtp.group_single(bnode.config)
            self._render_next(bnode.ntid, txtp)
            txtp.group_done()
            return

        if bnode.tree:

            if not txtp.params:
                # find all possible gamesyncs paths (won't generate txtp)
                txtp.ppaths.add_stingers(bnode.stingers)

                for path, ntid in bnode.tree.paths:
                    unreachable = txtp.ppaths.adds(path)
                    if not unreachable:
                        self._render_next(ntid, txtp)
                    txtp.ppaths.done()
                return

            # find if current gamesync combo matches one of the paths
            npath_combo = bnode.tree.get_npath(txtp.params)
            if npath_combo:
                npath, ntid = npath_combo
                txtp.info.gamesyncs(npath)

                txtp.group_single(bnode.config) #rarely may contain volumes
                self._render_next(ntid, txtp)
                txtp.group_done()
            return

        else:
            gtype = bnode.gtype
            gname = bnode.ngname.value()

            if not txtp.params:
                # find all possible gamesyncs paths (won't generate txtp)
                for ntid, ngvalue in bnode.gvalue_ntid.values(): #order doesn't matter
                    gvalue = ngvalue.value()
                    unreachable = txtp.ppaths.add(gtype, gname, ngvalue.value())
                    if not unreachable:
                        self._render_next(ntid, txtp)
                    txtp.ppaths.done()
                return

            # get current gamesync
            gvalue = txtp.params.current(gtype, gname)
            if gvalue is None:
                return
            if not gvalue in bnode.gvalue_ntid:
                return
            ntid, ngvalue = bnode.gvalue_ntid[gvalue]
            txtp.info.gamesync(gtype, bnode.ngname, ngvalue)

            txtp.group_single(bnode.config)
            self._render_next(ntid, txtp)
            txtp.group_done()
            return

        return

#******************************************************************************

class RN_CAkMusicRanSeqCntr(RN_CAkHircNode):

    def _render_txtp(self, bnode, txtp):
        self._register_transitions(txtp, bnode.ntransitions)

        if not txtp.params:
            txtp.ppaths.add_stingers(bnode.stingers)

        txtp.group_single(bnode.config) #typically useless but may have volumes
        self._process_playlist(txtp, bnode.items)
        txtp.group_done()

    def _process_playlist(self, txtp, items):
        if not items:
            return

        for item in items:
            type = item.type
            subitems = item.items

            txtp.info.next(item.nitem, item.fields)
            #leaf node uses -1 in newer versions, sid in older (ex. Enslaved)
            if type == -1 or item.ntid:
                transition = bnode_misc.NodeTransition()
                transition.play_before = False

                txtp.group_single(item.config, transition=transition)
                self._render_next(item.ntid, txtp)
                txtp.group_done()
            else:
                if   type == 0: #0: ContinuousSequence (plays all objects in sequence, on loop/next call restarts)
                    txtp.group_sequence_continuous(subitems, item.config)

                elif type == 1: #1: StepSequence (plays one object from first, on loop/next call plays next object)
                    txtp.group_sequence_step(subitems, item.config)

                elif type == 2: #2: ContinuousRandom (plays all objects randomly, on loop/next call restarts)
                    txtp.group_random_continuous(subitems, item.config)

                elif type == 3: #3: StepRandom (plays one object at random, on loop/next call plays another object)
                    txtp.group_random_step(subitems, item.config)

                else:
                    self._barf('unknown type')

                self._process_playlist(txtp, item.items)
                txtp.group_done(subitems)
            txtp.info.done()

        return


#******************************************************************************

class RN_CAkMusicSegment(RN_CAkHircNode):

    def _render_txtp(self, bnode, txtp):
        # empty segments are allowed as silence
        if not bnode.ntids:
            #logging.info("generator: found empty segment %s" % (self.sid))
            elems = [bnode.sound] #force some list to fool group_layer
            txtp.group_layer(elems, bnode.config)
            txtp.source_sound(bnode.sound, bnode.sconfig)
            txtp.group_done(elems)
            return

        txtp.group_layer(bnode.ntids, bnode.config)
        for ntid in bnode.ntids:
            self._render_next(ntid, txtp)
        txtp.group_done(bnode.ntids)
        return


#******************************************************************************

class RN_CAkMusicTrack(RN_CAkHircNode):

    def _render_txtp(self, bnode, txtp):
        if not bnode.subtracks: #empty / no clips
            return

        # node defines states that muted sources
        if bnode.config.volume_states:
            txtp.vpaths.add_nstates(bnode.config.volume_states)

        # musictrack can play in various ways
        if   bnode.type == 0: #normal (plays one subtrack, N aren't allowed)
            if len(bnode.subtracks) > 1:
                raise ValueError("more than 1 track")
            txtp.group_single(bnode.config)
            for subtrack in bnode.subtracks:
                self._render_clips(subtrack, txtp)
            txtp.group_done()

        elif bnode.type == 1: #random (plays random subtrack, on next call plays another)
            txtp.group_random_step(bnode.subtracks, bnode.config)
            for subtrack in bnode.subtracks:
                self._render_clips(subtrack, txtp)
            txtp.group_done(bnode.subtracks)

        elif bnode.type == 2: #sequence (plays first subtrack, on next call plays next)
            txtp.group_sequence_step(bnode.subtracks, bnode.config)
            for subtrack in bnode.subtracks:
                self._render_clips(subtrack, txtp)
            txtp.group_done(bnode.subtracks)

        elif bnode.type == 3: #switch (plays one subtrack depending on variables)
            gtype = bnode.gtype
            gname = bnode.ngname.value()

            if not txtp.params:
                # find all possible gamesyncs paths (won't generate txtp)
                for __, ngvalue in bnode.gvalue_index.values(): #order doesn't matter
                    if not ngvalue:
                        gvalue = 0
                    else:
                        gvalue = ngvalue.value()
                    txtp.ppaths.add(gtype, gname, gvalue)
                    #no subnodes
                    txtp.ppaths.done()
                return

            # get current gamesync
            gvalue = txtp.params.current(gtype, gname)
            if gvalue is None:
                return
            if not gvalue in bnode.gvalue_index:
                return
            index, ngvalue = bnode.gvalue_index[gvalue]

            #play subtrack based on index (assumed to follow order as defined)
            txtp.info.gamesync(gtype, bnode.ngname, ngvalue)

            if index is None:
                return # no subtrack, after adding path to gamesync (NHM3)
            subtrack = bnode.subtracks[index]

            txtp.group_single(bnode.config)
            self._render_clips(subtrack, txtp)
            txtp.group_done()

        else:
            self._barf()

        return

    def _render_clips(self, subtrack, txtp):
        if not subtrack:
            #logging.info("generator: found empty subtrack %s" % (self.sid))
            # rarely may happen with default = no track = silence (NMH3)
            sound = self._build_silence(self.node, True)
            config = bnode_misc.NodeConfig()
            sconfig = bnode_misc.NodeConfig()
            elems = [sound]
            txtp.group_layer(elems, config)
            txtp.source_sound(sound, sconfig)
            txtp.group_done(elems)
            return

        config = bnode_misc.NodeConfig()
        txtp.group_layer(subtrack, config)
        for clip in subtrack:
            if clip.neid and clip.neid.value():
                econfig = bnode_misc.NodeConfig()
                econfig.idelay = clip.sound.fpa #uses FPA to start segment, should work ok

                txtp.group_single(econfig)
                self._render_next(clip.neid, txtp)
                txtp.group_done()
            else:
                sconfig = bnode_misc.NodeConfig()
                sound = clip.sound
                txtp.info.next(clip.nitem, clip.fields)
                txtp.info.source(clip.sound.nsrc, clip.sound.source)
                txtp.info.done()
                txtp.source_sound(clip.sound, sconfig)
        txtp.group_done(subtrack)
        return
