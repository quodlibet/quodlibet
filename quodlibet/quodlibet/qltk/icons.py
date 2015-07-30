# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""A list of icon names.

Mainly to see which ones we define and for looking up the standardized ones.
Also reduces the chance of making a typo.

http://standards.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html
https://docs.google.com/spreadsheet/pub?
    key=0AsPAM3pPwxagdGF4THNMMUpjUW5xMXZfdUNzMXhEa2c
"""

from quodlibet.util import enum


@enum
class Icons(str):

    NONE = ""

    # these we have in our fallback icon theme
    QUODLIBET = "quodlibet"
    EXFALSO = "exfalso"
    QUODLIBET_MISSING_COVER = "quodlibet-missing-cover"

    # stock icon I couldn't think of a replacement for now
    EDIT = "gtk-edit"

    # these only come from an icon theme
    APPLICATION_EXIT = "application-exit"  # "_Quit"
    AUDIO_X_GENERIC = "audio-x-generic"
    DIALOG_ERROR = "dialog-error"  # "Error"
    DIALOG_INFORMATION = "dialog-information"  # "Information"
    DIALOG_PASSWORD = "dialog-password"
    DIALOG_QUESTION = "dialog-question"  # "Question"
    DIALOG_WARNING = "dialog-warning"  # "Warning"
    DOCUMENT_NEW = "document-new"  # "_New"
    DOCUMENT_OPEN = "document-open"  # "_Open"
    DOCUMENT_PROPERTIES = "document-properties"  # "_Properties"
    DOCUMENT_REVERT = "document-revert"  # "_Revert"
    DOCUMENT_SAVE = "document-save"  # "_Save"
    EDIT_CLEAR = "edit-clear"  # "_Clear"
    EDIT_COPY = "edit-copy"  # "_Copy"
    EDIT_DELETE = "edit-delete"  # "_Delete"
    EDIT_FIND = "edit-find"  # "_Find"
    EDIT_FIND_REPLACE = "edit-find-replace"  # "Find and _Replace"
    EDIT_REDO = "edit-redo"  # "_Redo"
    EDIT_SELECT_ALL = "edit-select-all"
    EDIT_UNDO = "edit-undo"  # "_Undo"
    EMBLEM_SYSTEM = "emblem-system"
    FOLDER = "folder"
    GO_JUMP = "go-jump"  # "_Jump to"
    HELP_ABOUT = "help-about"  # "_About"
    HELP_BROWSER = "help-browser"  # "_Help"
    IMAGE_X_GENERIC = "image-x-generic"
    LIST_ADD = "list-add"  # "_Add"
    LIST_REMOVE = "list-remove"  # "_Remove"
    MEDIA_EJECT = "media-eject"
    MEDIA_OPTICAL = "media-optical"  # "_CD-ROM"
    MEDIA_PLAYBACK_PAUSE = "media-playback-pause"  # "P_ause"
    MEDIA_PLAYBACK_START = "media-playback-start"  # "_Play"
    MEDIA_PLAYBACK_STOP = "media-playback-stop"  # "_Stop"
    MEDIA_SKIP_BACKWARD = "media-skip-backward"  # "Pre_vious"
    MEDIA_SKIP_FORWARD = "media-skip-forward"  # "_Next"
    NETWORK_WORKGROUP = "network-workgroup"  # "_Network"
    PREFERENCES_SYSTEM = "preferences-system"  # "_Preferences"
    PROCESS_STOP = "process-stop"  # "_Stop"
    SYSTEM_RUN = "system-run"  # "_Execute"
    TOOLS_CHECK_SPELLING = "tools-check-spelling"  # "_Spell Check"
    USER_TRASH = "user-trash" # "Trash"
    VIEW_REFRESH = "view-refresh"  # "_Refresh"
    WINDOW_CLOSE = "window-close"  # "_Close"
    AUDIO_CARD = "audio-card"
