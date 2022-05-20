#!/usr/bin/env python3
# (should work for python2 and 3)
#
# Wwiser bnk parser by bnnm

import sys
from wwiser import wcli
from wwiser import wgui

_PROFILE = False


def main():
    if len(sys.argv) > 1:
        wcli.Cli().start()
    else:
        wgui.Gui().start()


def profile_simple():
    try:
        import cProfile as profile
    except:
        import profile
    profile.run('wcli.Cli().start()')


def profile_complex():
    import pstats
    try:
        import cProfile as profile
    except:
        import profile
    #profile.run('wcli.Cli().start()')
    profiler = profile.Profile()
    profiler.enable()
    main()
    profiler.disable()
    sort = 'cumtime' #tottime ncalls
    stats = pstats.Stats(profiler).sort_stats(sort)
    stats.print_stats()


if __name__ == "__main__":
    if _PROFILE:
        profile_complex()
    else:
        main()
