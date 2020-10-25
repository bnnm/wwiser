#!/usr/bin/env python3
# (should work for python2 and 3)
#
# Wwiser bnk parser by bnnm

import sys
from wwiser import wcli
from wwiser import wgui

if __name__ == "__main__":
    #import profile
    #profile.run('wcli.Cli().start()')

    if len(sys.argv) > 1:
        wcli.Cli().start()
    else:
        wgui.Gui().start()
