
# STATECHUNK
#
# Most Wwise objects can define properties + values to be used when a state in set ("states" tab).
# For example could change object's volume=-96 when state bgm_type=silent. This info is saved into
# a "StateChunk". StateChunks only define info for active states, so "none" is not allowed.
#
# These are often used to silence tracks using states (ex. MGR, DMC)
# In rare cases also used to slightly increase volume from one track (Monster Hunter World's 3221323256.bnk).

class _AkStateInfo(object):
    def __init__(self):
        self.nstategroupid = None
        self.nstatevalueid = None
        self.group = None
        self.value = None
        self.ntid = None
        self.bstate = None

class AkStateChunk(object):
    def __init__(self, node, builder):
        self.valid = False
        self._states = []
        self._usables = None
        self._build(node, builder)

    def _build(self, node, builder):
        nstatechunk = node.find1(name='StateChunk')
        if not nstatechunk:
            return
        self.valid = True

        # StateChunk  has 2 sections:
        # - stateProps: list of AkStatePropertyInfo with possible modified properties (RTPC IDs).
        #   It's the defined columns in the "states" tab, even if not used (defaulting to 0).
        #   * AkStatePropertyInfo has ID, "inDb" (volume flag) and "accumType" (2=additive, but not
        #     actually always true),  but most of that info is implicit when applied later, thus ignored
        # - pStateChunks: list of AkStateGroupChunk, that defines which state=value will modify what.
        #   Typically only one but may define N for state-group1=state-value1, state-group2=state-value2, ....
        #
        # Each state-value doesn't have the list of modified properties, but rather an ID of a CAkState HIRC,
        # that has those in their AkPropBundle props

        bank_id = nstatechunk.get_root().get_id()

        nstategroups = nstatechunk.finds(name='AkStateGroupChunk')
        for nstategroup in nstategroups:
            nstategroupid = nstategroup.find1(name='ulStateGroupID')
            #eStateSyncType #when to apply props when state changes, not needed since we don't to dynamic changes

            nstates = nstategroup.finds(name='AkState')
            if not nstates: #possible to have groupchunks without pStates when leaving all values default (Xcom2's 820279197)
                continue

            for nstate in nstates:
                nstatevalueid = nstate.find1(name='ulStateID')
                if not nstatevalueid or not nstatevalueid.value():
                    continue #not possible to set "none" as value

                nstateinstanceid = nstate.find1(name='ulStateInstanceID') #each 
                if not nstateinstanceid or not nstateinstanceid.value():
                    continue

                # state should exist as a node and have properties
                tid = nstateinstanceid.value()
                bstate = builder._get_bnode(bank_id, tid)
                if not bstate or not bstate.props:
                    continue

                bsi = _AkStateInfo()
                bsi.nstategroupid = nstategroupid
                bsi.nstatevalueid = nstatevalueid
                bsi.ntid = nstateinstanceid
                bsi.group = nstategroupid.value()
                bsi.value = nstatevalueid.value()
                bsi.bstate = bstate

                #TODO filter repeats
                self._states.append(bsi)

    def get_bstate(self, group, value):
        for bsi in self._states:
            if bsi.group == group and bsi.value == value:
                return bsi.bstate
        return None

    def get_states(self):
        return self._states

    # states with properties that wwiser/vgmstream can handle (ignores stuff like auxs)
    def get_usable_states(self, apply_bus):
        if self._usables is None:
            items = []
            for bsi in self._states:
                if bsi.bstate.props.is_usable(apply_bus):
                    items.append(bsi)
            self._usables = items
        return self._usables
