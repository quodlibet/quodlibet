Useful Development Tools
========================

Memory Profiling
----------------

GObject Instance Count Leak Check
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Requires a development (only available in debug mode) version of glib. Jhbuild
recommended.

::

    jhbuild shell
    GOBJECT_DEBUG=instance-count GTK_DEBUG=interactive ./quodlibet.py

* In the GTK+ Inspector switch to the "Statistics" tab
* Sort by "Cumulative" and press the "Next" multimedia key to quickly switch
  songs.
* If something in the "Cumulative" column steadily increases we have a leak.


Performance Profiling
---------------------

cProfile
^^^^^^^^

 * https://docs.python.org/2/library/profile.html
 * bundled with python

::

    python -m cProfile -s [sort_order] quodlibet.py > cprof.txt


where ``sort_order`` can one of the following:
calls, cumulative, file, line, module, name, nfl, pcalls, stdname, time

Example output::

             885311 function calls (866204 primitive calls) in 12.110 seconds

       Ordered by: cumulative time

       ncalls  tottime  percall  cumtime  percall filename:lineno(function)
            1    0.002    0.002   12.112   12.112 quodlibet.py:11(<module>)
            1    0.007    0.007   12.026   12.026 quodlibet.py:25(main)
    19392/13067    0.151    0.000    4.342    0.000 __init__.py:639(__get__)
            1    0.003    0.003    4.232    4.232 quodlibetwindow.py:121(__init__)
            1    0.000    0.000    4.029    4.029 quodlibetwindow.py:549(select_browser)
            1    0.002    0.002    4.022    4.022 albums.py:346(__init__)
            ...
            ...

SnakeViz
^^^^^^^^

 * https://jiffyclub.github.io/snakeviz/
 * ``pip install snakeviz``

::

    python -m cProfile -o prof.out quodlibet.py
    snakeviz prof.out


Run Snake
^^^^^^^^^

 * http://www.vrplumber.com/programming/runsnakerun/
 * package runsnakerun in debian Wheezy

::

    python -m cProfile -o prof.out quodlibet.py
    runsnake  prof.out

Example: https://www.google.at/search?q=runsnakerun&tbm=isch


Gprof2Dot
^^^^^^^^^

 * https://github.com/jrfonseca/gprof2dot

::

    python -m cProfile -o output.pstats ./quodlibet.py
    gprof2dot.py -f pstats output.pstats | dot -Tpng -o output.png


Line Profiler
^^^^^^^^^^^^^

 * https://github.com/rkern/line_profiler

::

    # wrap all functions of interest with the @profile decorator
    ./kernprof.py  -l ./quodlibet.py # creates quodlibet.py.lprof
    python line_profiler.py quodlibet.py.lprof > prof.txt

Example output::

    Timer unit: 1e-06 s

    File: test.py
    Function: a at line 2
    Total time: 0.001528 s

    Line #      Hits         Time  Per Hit   % Time  Line Contents
    ==============================================================
         2                                           @profile
         3                                           def a():
         4         1          134    134.0      8.8      print "hello"
         5         1           12     12.0      0.8      b = []
         6       101          628      6.2     41.1      for i in xrange(100):
         7       100          696      7.0     45.5          b.append(i)
         8         1           58     58.0      3.8      print "world"


strace
^^^^^^

 * https://linux.die.net/man/1/strace

::

    strace -c ./quodlibet.py

Example output::

     time     seconds  usecs/call     calls    errors syscall
    ------ ----------- ----------- --------- --------- ----------------
     81.64    0.013274           9      1444       178 read
      7.04    0.001144           0      4041      3259 open
      3.81    0.000619          11        54           getdents64
      2.80    0.000456           0      1004           fstat64
      1.84    0.000299           0      2221      1688 stat64
    ...
    ...


IOProfiler
^^^^^^^^^^

 * https://code.google.com/archive/p/ioapps/wikis/ioprofiler.wiki
 * strace GUI
 * Shows read/write to files (how many reads/writes per file, which parts of the files were affected)

::

    strace -q -a1 -s0 -f -tttT -oOUT_FILE -e trace=file,desc,process,socket ./quodlibet.py
    ioreplay -c -f OUT_FILE -o OUT_FILE.bin
    ioprofiler.py
    # open OUT_FILE.bin


Example: https://code.google.com/archive/p/ioapps/wikis/IOProfilerScreenshots.wiki
