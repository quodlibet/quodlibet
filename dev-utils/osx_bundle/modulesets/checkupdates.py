#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Checks package versions against Arch, pypi, gnome and reports out of date
packages.
"""

import sys
import xml.etree.ElementTree as etree
from multiprocessing.pool import ThreadPool

import requests


def get_moduleset_versions():
    versions = {}
    tree = etree.parse('quodlibet.modules')
    root = tree.getroot()
    for x in root.iter():
        branch = x.find("branch")
        if branch is not None and branch.attrib.get("repo", "") != "system" \
                and "version" in branch.attrib:
            versions[x.attrib["id"]] = branch.attrib["version"]
    versions.pop("gtk-osx-docbook", None)

    # verify repos while at it
    repos = set()
    for e in root.findall("repository"):
        repos.add(e.attrib["name"])
    used = set(["git.gnome.org", "git.gnome.org/browse"])
    for x in root.iter():
        branch = x.find("branch")
        if branch is not None:
            repo = branch.attrib.get("repo")
            if repo is not None:
                assert repo in repos
                used.add(repo)
    assert not (repos - used), "unused repos %r" % (repos - used)

    return versions


def fix_name(name):
    if name == "freetype-no-harfbuzz":
        name = "freetype"
    if name == "freetype":
        name = "freetype2"
    if name == "openssl":
        name = "openssl-1.0"
    if name == "libxml2-python2":
        name = "libxml2"
    return name


def _fetch_version(name):
    arch_name = fix_name(name)

    # First try to get the package by name
    r = requests.get("https://www.archlinux.org/packages/search/json",
                     params={"name": arch_name})
    if r.status_code == 200:
        results = r.json()["results"]
    else:
        results = []

    def build_url(r):
        return "https://www.archlinux.org/packages/%s/%s/%s" % (
            r["repo"], r["arch"], r["pkgname"])

    versions = {}
    for result in results:
        url = build_url(result)
        versions[arch_name] = (result["pkgver"], url)
        for vs in result["provides"]:
            if "=" in vs:
                prov_name, ver = vs.split("=", 1)
                ver = ver.rsplit("-", 1)[0]
                versions[prov_name] = (ver, url)
            else:
                versions[vs] = (result["pkgver"], url)
        return versions

    # If all fails, search the AUR
    r = requests.get("https://aur.archlinux.org/rpc.php", params={
        "v": "5", "type": "search", "by": "name", "arg": arch_name})
    if r.status_code == 200:
        results = r.json()["results"]
    else:
        results = []

    for result in results:
        if result["Name"] == arch_name:
            url = "https://aur.archlinux.org/packages/%s" % result["Name"]
            return {arch_name: (result["Version"].rsplit("-", 1)[0], url)}

    if arch_name.startswith(("python-", "python2-")):
        pypi_name = arch_name.split("-", 1)[-1]
    else:
        pypi_name = arch_name

    r = requests.get(f"https://pypi.org/pypi/{pypi_name}/json")
    if r.status_code == 200:
        return {arch_name: (
            r.json()["info"]["version"], "https://pypi.python.org/pypi/%s" % pypi_name)}

    r = requests.get(
        "http://ftp.gnome.org/pub/GNOME/sources/%s/cache.json" % arch_name)
    if r.status_code == 200:
        return {arch_name: (list(r.json()[2].values())[0][-1], "")}

    return {}


def is_maybe_newer(a, b):
    try:
        return tuple(map(int, a.split("."))) > tuple(map(int, b.split(".")))
    except (ValueError, TypeError):
        pass

    return a != b


def main():
    assert sys.version_info[0] == 3

    moduleset_versions = get_moduleset_versions()

    pool = ThreadPool(4)
    pool_iter = pool.imap_unordered(_fetch_version, moduleset_versions.keys())

    arch_versions = {}
    for i, some_versions in enumerate(pool_iter):
        arch_versions.update(some_versions)

    for name, version in sorted(moduleset_versions.items()):
        arch_name = fix_name(name)
        if arch_name in arch_versions:
            arch_version, arch_url = arch_versions[arch_name]
            arch_version = arch_version.split("+", 1)[0]
            if arch_name == "readline":
                arch_version = ".".join(arch_version.split(".")[:2])
        else:
            arch_version = "???"
            arch_url = ""

        if is_maybe_newer(arch_version, version):
            print("%-30s %-20s %-20s %s" % (
                name, version, arch_version, arch_url))


if __name__ == "__main__":
    main()
