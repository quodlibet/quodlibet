# Copyright 2014 Christoph Reiter
#           2016 Nick Boultbee
#           2020 Daniel Petrescu
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""A list of icon names.

Mainly to see which ones we define and for looking up the standardized ones.
Also reduces the chance of making a typo.

http://standards.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html
https://docs.google.com/spreadsheet/pub?
    key=0AsPAM3pPwxagdGF4THNMMUpjUW5xMXZfdUNzMXhEa2c
"""

from quodlibet.util.enum import enum


@enum
class Icons(str):
    NONE = ""

    # these we have in our fallback icon theme
    QUODLIBET = "io.github.quodlibet.QuodLibet"
    EXFALSO = "exfalso"
    QUODLIBET_MISSING_COVER = "quodlibet-missing-cover"

    # stock icon I couldn't think of a replacement for now
    EDIT = "gtk-edit"

    # these only come from an icon theme
    APPLICATION_EXIT = "application-exit"  # "_Quit"
    APPLICATION_INTERNET = "applications-internet"
    APPLICATION_UTILITIES = "applications-utilities"
    APPOINTMENT_NEW = "appointment-new"
    AUDIO_CARD = "audio-card"
    AUDIO_INPUT_MICROPHONE = "audio-input-microphone"
    AUDIO_VOLUME_MUTED = "audio-volume-muted"
    AUDIO_X_GENERIC = "audio-x-generic"
    CHANGES_PREVENT = "changes-prevent"
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
    DOCUMENT_SAVE_AS = "document-save-as"  # "_Save"
    DOCUMENT_SEND = "document-send"
    DRIVE_REMOVABLE_MEDIA = "drive-removable-media"
    EDIT_CLEAR = "edit-clear"  # "_Clear"
    EDIT_COPY = "edit-copy"  # "_Copy"
    EDIT_PASTE = "edit-paste"  # "_Paste"
    EDIT_DELETE = "edit-delete"  # "_Delete"
    EDIT_FIND = "edit-find"  # "_Find"
    EDIT_FIND_REPLACE = "edit-find-replace"  # "Find and _Replace"
    EDIT_REDO = "edit-redo"  # "_Redo"
    EDIT_SELECT_ALL = "edit-select-all"
    EDIT_UNDO = "edit-undo"  # "_Undo"
    FACE_SMILE = "face-smile"
    FAVORITE = "emblem-favorite"
    FOLDER = "folder"
    FOLDER_DRAG_ACCEPT = "folder-drag-accept"
    FOLDER_OPEN = "folder-open"
    FOLDER_DOWNLOAD = "folder-download"
    FORMAT_JUSTIFY_FILL = "format-justify-fill"
    GO_JUMP = "go-jump"  # "_Jump to"
    HELP_ABOUT = "help-about"  # "_About"
    HELP_BROWSER = "help-browser"  # "_Help"
    IMAGE_X_GENERIC = "image-x-generic"
    INSERT_IMAGE = "insert-image"
    INSERT_TEXT = "insert-text"
    LIST_ADD = "list-add"  # "_Add"
    LIST_EDIT = "document-edit"  # "_Edit"
    LIST_REMOVE = "list-remove"  # "_Remove"
    MEDIA_EJECT = "media-eject"
    MEDIA_OPTICAL = "media-optical"  # "_CD-ROM"
    MEDIA_PLAYBACK_PAUSE = "media-playback-pause"  # "P_ause"
    MEDIA_PLAYBACK_START = "media-playback-start"  # "_Play"
    MEDIA_PLAYBACK_STOP = "media-playback-stop"  # "_Stop"
    MEDIA_PLAYLIST_REPEAT = "media-playlist-repeat"
    MEDIA_PLAYLIST_SHUFFLE = "media-playlist-shuffle"
    MEDIA_RECORD = "media-record"
    MEDIA_SKIP_BACKWARD = "media-skip-backward"  # "Pre_vious"
    MEDIA_SKIP_FORWARD = "media-skip-forward"  # "_Next"
    MULTIMEDIA_PLAYER = "multimedia-player"
    MULTIMEDIA_VOLUME_CONTROL = "multimedia-volume-control"
    NETWORK_WORKGROUP = "network-workgroup"  # "_Network"
    NETWORK_SERVER = "network-server"
    NETWORK_TRANSMIT = "network-transmit"
    NETWORK_RECEIVE = "network-receive"
    OPEN_MENU = "open-menu"
    PREFERENCES_SYSTEM = "preferences-system"  # "_Preferences"
    PREFERENCES_DESKTOP_SCREENSAVER = "preferences-desktop-screensaver"
    PREFERENCES_DESKTOP_THEME = "preferences-desktop-theme"
    PROCESS_STOP = "process-stop"  # "_Stop"
    SYSTEM_LOCK_SCREEN = "system-lock-screen"
    SYSTEM_RUN = "system-run"  # "_Execute"
    SYSTEM_SEARCH = "system-search"
    TEXT_HTML = "text-html"
    TOOLS_CHECK_SPELLING = "tools-check-spelling"  # "_Spell Check"
    USER_BOOKMARKS = "user-bookmarks"  # Looks like a rating
    USER_DESKTOP = "user-desktop"
    USER_TRASH = "user-trash"  # "Trash"
    UTILITIES_TERMINAL = "utilities-terminal"
    VIEW_LIST = "view-list"  #
    VIEW_REFRESH = "view-refresh"  # "_Refresh"
    WINDOW_CLOSE = "window-close"  # "_Close"
