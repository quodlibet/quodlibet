#!/usr/bin/env python3
# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen

import feedparser


GITHUB = ("https://github.com/quodlibet/quodlibet/releases/download/"
          "release-%(version)s/")

OSX_QL = "osx-quodlibet"
OSX_EF = "osx-exfalso"
WIN = "windows"
WIN_PORT = "windows-portable"
TARBALL = "default"

BUILD_TYPE_TITLES = {
    OSX_QL: "Quod Libet (OS X)",
    OSX_EF: "Ex Falso (OS X)",
    WIN: "Quod Libet / Ex Falso (Windows)",
    WIN_PORT: "Quod Libet / Ex Falso (Windows Portable)",
    TARBALL: "Quod Libet / Ex Falso",
}


BUILD_TYPE_SHORT_TITLES = {
    OSX_QL: "Quod Libet %(version)s",
    OSX_EF: "Ex Falso %(version)s",
    WIN: "Quod Libet %(version)s",
    WIN_PORT: "Quod Libet %(version)s (portable)",
    TARBALL: "Quod Libet %(version)s",
}


RELEASES = [
    {
        "version": "4.2.1",
        "date": "2018-12-26",
        "builds": {
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            OSX_QL: [GITHUB + "QuodLibet-%(version)s.dmg"],
            OSX_EF: [GITHUB + "ExFalso-%(version)s.dmg"],
        }
    },
    {
        "version": "4.2.0",
        "date": "2018-10-31",
        "builds": {
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            OSX_QL: [GITHUB + "QuodLibet-%(version)s.dmg"],
            OSX_EF: [GITHUB + "ExFalso-%(version)s.dmg"],
        }
    },
    {
        "version": "4.1.0",
        "date": "2018-06-03",
        "builds": {
            OSX_QL: [GITHUB + "QuodLibet-%(version)s.dmg"],
            OSX_EF: [GITHUB + "ExFalso-%(version)s.dmg"],
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
    {
        "version": "4.0.2",
        "date": "2018-01-17",
        "builds": {
            OSX_QL: [GITHUB + "QuodLibet-%(version)s.dmg"],
            OSX_EF: [GITHUB + "ExFalso-%(version)s.dmg"],
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
    {
        "version": "4.0.1",
        "date": "2018-01-13",
        "builds": {
            OSX_QL: [GITHUB + "QuodLibet-%(version)s.dmg"],
            OSX_EF: [GITHUB + "ExFalso-%(version)s.dmg"],
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
    {
        "version": "4.0.0",
        "date": "2017-12-26",
        "builds": {
            OSX_QL: [GITHUB + "QuodLibet-%(version)s.dmg"],
            OSX_EF: [GITHUB + "ExFalso-%(version)s.dmg"],
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
    {
        "version": "3.9.1",
        "date": "2017-06-06",
        "builds": {
            OSX_QL: [GITHUB + "QuodLibet-%(version)s.dmg"],
            OSX_EF: [GITHUB + "ExFalso-%(version)s.dmg"],
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
    {
        "version": "3.9.0",
        "date": "2017-05-24",
        "builds": {
            OSX_QL: [GITHUB + "QuodLibet-%(version)s.dmg"],
            OSX_EF: [GITHUB + "ExFalso-%(version)s.dmg"],
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
    {
        "version": "3.8.1",
        "date": "2017-01-23",
        "builds": {
            OSX_QL: [GITHUB + "QuodLibet-%(version)s.dmg"],
            OSX_EF: [GITHUB + "ExFalso-%(version)s.dmg"],
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
    {
        "version": "3.8.0",
        "date": "2016-12-29",
        "builds": {
            OSX_QL: [GITHUB + "QuodLibet-%(version)s.dmg"],
            OSX_EF: [GITHUB + "ExFalso-%(version)s.dmg"],
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
    {
        "version": "3.7.1",
        "date": "2016-09-25",
        "builds": {
            OSX_QL: [GITHUB + "QuodLibet-%(version)s.dmg"],
            OSX_EF: [GITHUB + "ExFalso-%(version)s.dmg"],
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
    {
        "version": "3.7.0",
        "date": "2016-08-27",
        "builds": {
            OSX_QL: [GITHUB + "QuodLibet-%(version)s.dmg"],
            OSX_EF: [GITHUB + "ExFalso-%(version)s.dmg"],
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
    {
        "version": "3.6.2",
        "date": "2016-05-24",
        "builds": {
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
    {
        "version": "3.6.1",
        "date": "2016-04-05",
        "builds": {
            OSX_QL: [GITHUB + "QuodLibet-%(version)s.zip"],
            OSX_EF: [GITHUB + "ExFalso-%(version)s.zip"],
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
    {
        "version": "3.6.0",
        "date": "2016-03-24",
        "builds": {
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
    {
        "version": "3.5.3",
        "date": "2016-01-16",
        "builds": {
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
    {
        "version": "3.5.2",
        "date": "2016-01-13",
        "builds": {
            OSX_QL: [GITHUB + "QuodLibet-%(version)s.zip",
                     GITHUB + "QuodLibet-%(version)s-v2.zip"],
            OSX_EF: [GITHUB + "ExFalso-%(version)s.zip",
                     GITHUB + "ExFalso-%(version)s-v2.zip"],
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
    {
        "version": "3.5.1",
        "date": "2015-10-14",
        "builds": {
            OSX_QL: [GITHUB + "QuodLibet-%(version)s.zip"],
            OSX_EF: [GITHUB + "ExFalso-%(version)s.zip"],
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
    {
        "version": "3.5.0",
        "date": "2015-10-07",
        "builds": {
            OSX_QL: [GITHUB + "QuodLibet-%(version)s.zip",
                     GITHUB + "QuodLibet-%(version)s-v2.zip"],
            OSX_EF: [GITHUB + "ExFalso-%(version)s.zip",
                     GITHUB + "ExFalso-%(version)s-v2.zip"],
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
    {
        "version": "3.4.1",
        "date": "2015-05-24",
        "builds": {
            OSX_QL: [GITHUB + "QuodLibet-%(version)s.zip"],
            OSX_EF: [GITHUB + "ExFalso-%(version)s.zip"],
            WIN: [GITHUB + "quodlibet-%(version)s-installer.exe"],
            WIN_PORT: [GITHUB + "quodlibet-%(version)s-portable.exe"],
            TARBALL: [GITHUB + "quodlibet-%(version)s.tar.gz"],
        }
    },
]


class Build:

    def __init__(self, type, version, build_version, url, hash_url, sig_url,
                 size):
        self.type = type
        self.version = version
        self.build_version = build_version
        self.url = url
        self.hash_url = hash_url
        self.sig_url = sig_url
        self.size = size

    @property
    def name(self):
        return BUILD_TYPE_SHORT_TITLES[self.type] % {
            "version": self.version_desc}

    @property
    def version_desc(self):
        if self.build_version == "0":
            return self.version
        return self.version + "v%d" % (int(self.build_version) + 1, )

    def __repr__(self):
        return ("<Build type=%(type)s build_version=%(build_version)s "
                "url=%(url)s hash_url=%(hash_url)s sig_url=%(sig_url)s "
                "size=%(size)d>" % vars(self))


class Release:

    def __init__(self, version, date, builds):
        self.version = version
        self.date = date
        self.builds = builds

    def __repr__(self):
        return ("<Release version=%(version)s date=%(date)s "
                "builds=%(builds)r>" % vars(self))


def _fill_build(build):
    try:
        r = urlopen(build.url)
    except OSError as e:
        print(e, build.url)
        raise
    build.size = int(r.info().get("Content-Length", "0"))
    r.close()

    hash_url = build.url + ".sha256"
    try:
        urlopen(hash_url).close()
    except OSError as e:
        print(e)
    else:
        build.hash_url = hash_url

    sig_url = build.url + ".sig"
    try:
        urlopen(sig_url).close()
    except OSError as e:
        print(e)
    else:
        build.sig_url = sig_url


def get_releases():
    all_builds = []
    releases = []
    for r in RELEASES:
        version = r["version"]
        date = r["date"]
        builds = []
        for type, urls in r["builds"].items():
            for i, url in reversed(list(enumerate(urls))):
                build_version = str(i)
                url = url % r
                builds.append(
                    Build(type, version, build_version, url, None, None, 0))
        releases.append(Release(version, date, builds))
        all_builds.extend(builds)

    with ThreadPoolExecutor(max_workers=20) as executor:
        for i, _ in enumerate(executor.map(_fill_build, all_builds)):
            print(i + 1, len(all_builds))

    return releases


APPCAST_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" \
xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle" \
xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>%(title)s</title>
    <link>%(link)s</link>
%(items)s\
</channel>
</rss>
"""

APPCAST_ITEM = """\
    <item>
      <title>Version %(version_desc)s</title>
      <sparkle:releaseNotesLink>
        %(changelog)s
      </sparkle:releaseNotesLink>
      <link>%(changelog)s</link>
      <pubDate>%(date)s</pubDate>
      <enclosure url="%(url)s" %(os)s sparkle:version="%(version_key)s" \
length="%(length)s" type="application/octet-stream" />
    </item>
"""


def release_link(version):
    return ("https://quodlibet.readthedocs.io/en/latest/"
            "changelog.html#release-%s" % version.replace(".", "-"))


def release_date(date):
    return time.strftime("%a, %d %b %Y %H:%M:%S +0000",
                         time.strptime(date, "%Y-%m-%d"))


def get_latest_builds(releases, build_type):
    """Returns the latest builds for each major versions, newest first"""

    builds = []
    versions_seen = set()
    for release in releases:
        for build in release.builds:
            if build.type == build_type:
                break
        else:
            continue

        vkey = tuple(release.version.split(".")[:2])
        if vkey in versions_seen:
            continue
        versions_seen.add(vkey)

        builds.append(build)

    return builds


def appcast_build(releases):
    feeds = {}

    os_mapping = {
        OSX_QL: "",
        OSX_EF: "",
        WIN: "windows",
        WIN_PORT: "windows",
        TARBALL: "linux",
    }

    for build_type, title in BUILD_TYPE_TITLES.items():
        items = []
        for release in releases:
            for build in release.builds:
                if build.type != build_type:
                    continue

                version_desc = build.version_desc

                version_key = release.version
                if build.build_version != "0":
                    version_key += "." + build.build_version

                os_id = os_mapping[build.type]

                item = APPCAST_ITEM % {
                    "version_desc": version_desc,
                    "version_key": version_key,
                    "length": build.size,
                    "url": build.url,
                    "date": release_date(release.date),
                    "changelog": release_link(release.version),
                    "os": ("sparkle:os=\"%s\"" % os_id) if os_id else "",
                }
                items.append(item)

        result = APPCAST_TEMPLATE % {
            "title": title,
            "link":
                "https://quodlibet.readthedocs.io/en/latest/downloads.html",
            "items": "".join(items),
        }

        assert feedparser.parse(result)
        feeds[build_type] = result

    return feeds


def get_download_tables(releases):

    tables = {}

    for build_type in BUILD_TYPE_TITLES.keys():
        text = """\
.. list-table::
    :header-rows: 1

    * - Release
      - File
      - SHA256
      - PGP
"""
        for build in get_latest_builds(releases, build_type)[:3]:
            text += """\
    * - %s
      - `%s <%s>`__
      - `SHA256 <%s>`__
      - `SIG <%s>`__
""" % (build.name, build.url.rsplit("/")[-1],
                build.url, build.hash_url, build.sig_url)

        tables[build_type] = text

    return tables


def main(argv):
    releases = get_releases()

    path = os.path.join("..", "quodlibet", "docs", "tables")
    for build_type, table in get_download_tables(releases).items():
        with open(os.path.join(path, build_type.replace("-", "_") + ".rst"),
                  "w", encoding="utf-8") as h:
            h.write(table)

    os.mkdir("appcast")
    for build_type, feed in appcast_build(releases).items():
        with open(os.path.join("appcast", build_type + ".rss"),
                  "w", encoding="utf-8") as h:
            h.write(feed)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
