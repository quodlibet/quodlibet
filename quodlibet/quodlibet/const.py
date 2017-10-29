# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""Constants used in various parts of QL, mostly strings."""

import sys
import os


# MSYS2 defines MSYSTEM which changes os.sep/os.path.sep for the mingw
# Python build. Unset here and restart.. (does not work for py.test etc.)
# XXX: do this here since it gets executed by all scripts
if os.name == "nt" and "MSYSTEM" in os.environ:
    import subprocess
    del os.environ["MSYSTEM"]
    argv = []
    for arg in [sys.executable] + sys.argv:
        if os.path.exists(arg):
            arg = arg.replace("/", "\\")
        argv.append(arg)
    sys.exit(subprocess.call(argv))


class Version(tuple):
    """Represent the version of a dependency as a tuple"""

    def __new__(cls, name, *args, **kwargs):
        inst = tuple.__new__(Version, args)
        inst.name = name
        inst.message = kwargs.pop("message", "")
        return inst

    def human_version(self):
        return ".".join(map(str, self))

    def __str__(self):
        return self.human_version()

    def check(self, version_tuple):
        """Raises ImportError if the version isn't supported"""

        if self[0] == version_tuple[0] and version_tuple >= self:
            return
        message = " " + self.message if self.message else ""
        raise ImportError("%s %s required. %s found.%s" % (
            self.name, self, Version("", *version_tuple), message))


class MinVersions(object):
    """Dependency requirements for Quod Libet / Ex Falso"""

    PYTHON2 = Version("Python2", 2, 7)
    PYTHON3 = Version("Python3", 3, 5)
    MUTAGEN = Version("Mutagen", 1, 34,
        message="Use the Quod Libet unstable PPAs/repos to get a newer "
                "mutagen version.")
    GTK = Version("GTK+", 3, 18)
    PYGOBJECT = Version("PyGObject", 3, 18)
    GSTREAMER = Version("GStreamer", 1, 8)


VERSION_TUPLE = Version("", 4, 0, -1)
VERSION = str(VERSION_TUPLE)

# entry point for the user guide / wiki
BRANCH_NAME = "master"
DOCS_BASE_URL = "https://quodlibet.readthedocs.org/en/%s"
DOCS_LATEST = DOCS_BASE_URL % "latest"
DOCS_BASE_URL %= BRANCH_NAME if BRANCH_NAME != "master" else "latest"
ONLINE_HELP = DOCS_BASE_URL + "/guide/index.html"
SEARCH_HELP = DOCS_BASE_URL + "/guide/searching.html"
SHORTCUTS_HELP = DOCS_BASE_URL + "/guide/shortcuts.html"

# Email used as default for reading/saving per-user data in tags, etc.
EMAIL = os.environ.get("EMAIL", "quodlibet@lists.sacredchao.net")

# Displayed as registered / help email address
SUPPORT_EMAIL = "quod-libet-development@googlegroups.com"

# about dialog, --version etc.
WEBSITE = "https://quodlibet.readthedocs.org/"
COPYRIGHT = u"Copyright 2004-2017"

AUTHORS = sorted(u"""\
Alexandre Passos
Alexey Bobyakov
Alex Geoffrey Smith
Anders Carlsson
Andreas Bombe
Andrew Chadwick
Anton Shestakov
Ari Pollak
Aymeric Mansoux
Bastian Kleineidam
Bastien Gorissen
Benjamin Boutier
Ben Zeigler
Bernd Wechner
Bruno Bergot
Carlo Teubner
Christine Spang
Christoph Reiter
Corentin Néau
David Kågedal
David Schneider
Decklin Foster
Didier Villevalois
Eduardo Gonzalez
Eric Casteleijn
Erich Schubert
Eric Le Lay
Federico Pelloni
Felix Krull
Florian Demmer
Fredrik Strupe
Guillaume Chazarain
Hans Scholze
Iñigo Serna
Jacob Lee
Jakob Gahde
Jan Arne Petersen
Jan Path
Javier Kohen
Joe Higton
Joe Wreschnig
Johan Hovold
Johannes Marbach
Johannes Rohrer
Joschka Fischer
Josh Lee
Joshua Homan
Joshua Kwan
Lalo Martins
Lee Willis
Lukáš Lalinský
Markus Koller
Martijn Pieters
Martin Bergström
Michaël Ball
Michael Urman
Mickael Royer
Nicholas J. Michalek
Nick Boultbee
Niklas Janlert
Nikolai Prokoschenko
Philipp Müller
Philipp Weis
Quincy John Hamilton
Remi Vanicat
Robert Muth
Ryan Turner
Sebastian Thürrschmidt
Simonas Kazlauskas
Simon Larsen
Steven Robertson
Thomas Vogt
Tobias Wolf
Tomasz Miasko
Tomasz Torcz
Tshepang Lekhonkhobe
Türerkan İnce
Uriel Zajaczkovski
Vasiliy Faronov
Victoria Hayes
Zack Weinberg
Vimalan Reddy
Jason Heard
David Pérez Carmona
Jakub Wilk
IBBoard@github
CreamyCookie@github
Sauyon Lee
Thomas Leberbauer
Kristian Laakkonen
""".strip().split("\n"))

TRANSLATORS = sorted(u"""
Åka Sikrom (nb)
Alexandre Passos (pt)
Andreas Bertheussen (nb)
Olivier Humbert (fr)
Anton Shestakov (ru)
Bastian Kleineidam (de)
Bastien Gorissen (fr)
Byung-Hee HWANG (ko)
ChangBom Yoon (ko)
Daniel Nyberg (sv)
Dimitris Papageorgiou (el)
Djavan Fagundes (pt)
Einārs Sprūģis (lv)
Eirik Haatveit (nb)
Emfox Zhou (zh_CN)
Erik Christiansson (sv)
Fabien Devaux (fr)
Filippo Pappalardo (it)
Guillaume Ayoub (fr)
Hans van Dok (nl)
Honza Hejzl (cs_CZ)
Hsin-lin Cheng (zh_TW)
Jari Rahkonen (fi)
Javier Kohen (es)
Joe Wreschnig (en_CA)
Johám-Luís Miguéns Vila (es, gl, gl_ES, eu, pt)
Jonas Slivka (lt)
Joshua Kwan (fr)
Luca Baraldi (it)
Ludovic Druette (fr)
Lukáš Lalinský (sk)
Mathieu Morey (fr)
Michal Nowikowski (pl)
Mugurel Tudor (ro)
Mykola Lynnyk (uk)
Naglis Jonaitis (lt)
Nathan Follens (nl)
Nick Boultbee (fr, en_GB)
Olivier Gambier (fr)
Piarres Beobide (eu)
Piotr Drąg (pl)
Roee Haimovich (he)
Rüdiger Arp (de)
SZERVÁC Attila (hu)
Tomasz Torcz (pl)
Türerkan İnce (tr)
Witold Kieraś (pl)
Yasushi Iwata (ja)
Δημήτρης Παπαγεωργίου (el)
Андрей Федосеев (ru)
Микола 'Cthulhu' Линник (uk)
Николай Прокошенко (ru)
Ростислав "zbrox" Райков (bg)
Сергей Федосеев (ru)
scootergrisen@github (da)
Marek Suchánek (cs)
Till Berger (de)
Jean-Michel Pouré (fr)
Kristian Laakkonen (fi)
Kirill Romanov (ru)
""".strip().splitlines())

ARTISTS = sorted(u"""\
Tobias
Jakub Steiner
Fabien Devaux
""".strip().split("\n"))

# Default songlist column headers
DEFAULT_COLUMNS = "~#track ~people ~title~version ~album~discsubtitle " \
                  "~#length".split()

DEBUG = ("--debug" in sys.argv or "QUODLIBET_DEBUG" in os.environ)
