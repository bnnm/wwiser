import logging

# Utils

class TxtpDebug(object):
    def __init__(self):
        pass

    #--------------------------------------------------------------------------

    # simplifies tree to simulate some Wwise features with TXTP
    def print(self, tree, pre, post):
        if pre and not post:
            logging.info("*** tree pre:")
        if not pre and post:
            logging.info("*** tree post:")
        if pre and post:
            logging.info("*** tree:")

        self._mdepth = 0
        self._print_tree(tree, pre, post)

        logging.info("")

        return


    def _print_tree(self, tnode, pre, post):
        line1 = ''
        line2 = ''
        config1 = ''
        config2 = ''

        if post:
            if tnode.loop is not None:       config1 += " lpn=%s" % (tnode.loop)
            if tnode.volume:                 config1 += " vol=%s" % (tnode.volume)
            if tnode.envelopelist:           config1 += " (env)"
            if tnode.fake_entry:             config1 += " (fke)"
            if tnode.ignorable():            config1 += " [i]"

            if tnode.body_time:              config2 += ' bt={0:.5f}'.format(tnode.body_time)
            if tnode.pad_begin:              config2 += ' pb={0:.5f}'.format(tnode.pad_begin)
            if tnode.trim_begin:             config2 += ' tb={0:.5f}'.format(tnode.trim_begin)
            if tnode.trim_end:               config2 += ' te={0:.5f}'.format(tnode.trim_end)
            if tnode.pad_end:                config2 += ' pb={0:.5f}'.format(tnode.pad_end)

        if pre:
            if tnode.config.loop is not None: config1 += " lpc=%s" % (tnode.config.loop)
            if tnode.config.delay:           config1 += " dly=%s" % (tnode.config.delay)
            if tnode.config.gain:            config1 += " cgn=%s" % (tnode.config.gain)
            if tnode.config.playevent:       config1 += " (pev)"
            if tnode.config.rules:           config1 += " (rules)"
           #if tnode.envelopelist:           config1 += " (env)"

            if tnode.config.entry or tnode.config.exit:
                dur = '{0:.5f}'.format(tnode.config.duration)
                ent = '{0:.5f}'.format(tnode.config.entry)
                exi = '{0:.5f}'.format(tnode.config.exit)
                config2 += " (dur=%s, entry=%s, exit=%s)" % (dur, ent, exi)

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
            self._print_tree(subtnode, pre, post)
        self._mdepth -= 1
