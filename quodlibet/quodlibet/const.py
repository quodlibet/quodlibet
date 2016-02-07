# -*- coding: utf-8 -*-
# Constants used in various parts of QL, mostly strings.

import sys
import os


class Version(tuple):
    """Represent the version of a dependency as a tuple"""

    def __new__(cls, name, *args):
        inst = tuple.__new__(Version, args)
        inst.name = name
        return inst

    def human_version(self):
        return ".".join(map(str, self))

    def __str__(self):
        return self.human_version()

    def check(self, version_tuple):
        """Raises ImportError if the version isn't supported"""

        if self[0] == version_tuple[0] and version_tuple >= self:
            return
        raise ImportError("%s %s required. %s found." % (
            self.name, self, Version("", *version_tuple)))


class MinVersions(object):
    """Dependency requirements for Quod Libet / Ex Falso"""

    PYTHON2 = Version("Python2", 2, 7)
    PYTHON3 = Version("Python3", 3, 4)
    MUTAGEN = Version("Mutagen", 1, 30)
    GTK = Version("GTK+", 3, 10)
    PYGOBJECT = Version("PyGObject", 3, 10)
    GSTREAMER = Version("GStreamer", 1, 0)


VERSION_TUPLE = Version("", 3, 6, -1)
VERSION = str(VERSION_TUPLE)

# entry point for the user guide / wiki
BRANCH_NAME = "master"
DOCS_BASE_URL = "https://quodlibet.readthedocs.org/en/%s"
DOCS_LATEST = DOCS_BASE_URL % "latest"
DOCS_BASE_URL %= BRANCH_NAME if BRANCH_NAME != "master" else "latest"
ONLINE_HELP = DOCS_BASE_URL + "/guide/index.html"
SEARCH_HELP = DOCS_BASE_URL + "/guide/searching.html"

# Email used as default for reading/saving per-user data in tags, etc.
EMAIL = os.environ.get("EMAIL", "quodlibet@lists.sacredchao.net")

# Displayed as registered / help email address
SUPPORT_EMAIL = "quod-libet-development@googlegroups.com"

MAIN_AUTHORS = """\
Joe Wreschnig
Michael Urman
Iñigo Serna
Steven Robertson
Christoph Reiter
Nick Boultbee""".split("\n")

# about dialog, --version etc.
WEBSITE = "https://quodlibet.readthedocs.org/"
COPYRIGHT = """Copyright © 2004-2016 %s...""" % ", ".join(MAIN_AUTHORS)

AUTHORS = sorted("""\
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
Bruno Bergot
Carlo Teubner
Christine Spang
Christoph Reiter
David Kågedal
David Schneider
Decklin Foster
Eduardo Gonzalez
Eric Casteleijn
Erich Schubert
Eric Le Lay
Federico Pelloni
Felix Krull
Florian Demmer
Guillaume Chazarain
Hans Scholze
Iñigo Serna
Jacob Lee
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
Vasiliy Faronov
Zack Weinberg
""".strip().split("\n"))

TRANSLATORS = sorted("""
Alexandre Passos (pt)
Andreas Bertheussen (nb)
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
""".strip().splitlines())

ARTISTS = sorted("""\
Tobias
Jakub Steiner
Fabien Devaux
""".strip().split("\n"))

# Default songlist column headers
DEFAULT_COLUMNS = "~#track ~people ~title~version ~album~discsubtitle " \
                  "~#length".split()

DEBUG = ("--debug" in sys.argv or "QUODLIBET_DEBUG" in os.environ)
