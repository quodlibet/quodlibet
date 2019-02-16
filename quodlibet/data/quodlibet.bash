# quodlibet(1) completion                                  -*- shell-script -*-
# vim: sts=4 sw=4 et

# This file is part of Quodlibet.
#
# Copyright 2019 Arnaud Rebillout
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

__tags() {
    if command -v operon >/dev/null 2>&1; then
        operon tags -a -t -c tag | tr '\n' ' '
    fi
}

_quodlibet() {
    # Assigned variable by _init_completion:
    #   cur    Current argument.
    #   prev   Previous argument.
    #   words  Argument array.
    #   cword  Argument array size.
    local cur prev words cword
    _init_completion -n = || return

    local audio_extensions='@(a?(l)ac|ac3|ape|flac|m[4k]a|mid|mp3|og[ag]|opus|w?(a)v)'

    # Quodlibet commands and options
    local opts=(--add-location --debug --enqueue --enqueue-files \
		--filter --focus --force-previous --help --hide-window \
		--list-browsers --next --no-plugins --open-browser --pause \
		--play --play-file --play-pause --previous --print-playing \
		--print-playlist --print-query --print-query-text --print-queue \
		--query --queue --quit --random --refresh --repeat --repeat-type \
		--run --seek --set-browser --set-rating --show-window --shuffle \
		--shuffle-type --start-hidden --start-playing --status --stop \
		--stop-after --toggle-window --unfilter --unqueue --version \
		--volume --volume-down --volume-up)

    # Completion per otion
    case "$prev" in

        --enqueue|--unqueue|--enqueue-files|--add-location|--play-file)
            # For these options we complete with audio files, even though
            # it's not necessarily what user wants.
            # --add-location=location
            # --enqueue=filename|query
            # --enqueue-files=filename[,filename..]
            # --play-file=filename
            # --unqueue=filename|query
            _filedir "$audio_extensions"
            return 0
            ;;

        --queue|--repeat|--shuffle)
            compopt -o nosort
            comps="on off toggle"
            COMPREPLY=($(compgen -W "$comps" -- "$cur"))
            return 0
            ;;

        --repeat-type)
            compopt -o nosort
            comps="current all one off"
            COMPREPLY=($(compgen -W "$comps" -- "$cur"))
            return 0
            ;;

        --shuffle-type)
            compopt -o nosort
            comps="random weighted off"
            COMPREPLY=($(compgen -W "$comps" -- "$cur"))
            return 0
            ;;

        --stop-after)
            compopt -o nosort
            comps="0 1 t"
            COMPREPLY=($(compgen -W "$comps" -- "$cur"))
            return 0
            ;;

        --filter) # tag=value
            compopt -o nospace
            comps="$(__tags)"
            COMPREPLY=($(compgen -S= -W "$comps" -- "$cur"))
            return 0
            ;;

        --random) # tag
            comps=$(__tags)
            COMPREPLY=($(compgen -W "$comps" -- "$cur"))
            return 0
            ;;

        --open-browser|--query|--print-query|--seek|--set-browser|--set-rating|--volume)
            # These options expect an argument that we can't guess.
            # --open-browser=BrowserName
            # --query=query
            # --print-query=query
            # --seek=[+|-][HH:]MM:SS
            # --set-browser=BrowserName
            # --set-rating=0.0..1.0
            # --volume=(+|-|)0..100
            return 0
            ;;

        -*)
            # Other options don't expect any argument, however user might want
            # to provide more options. So we don't return yet.
            ;;

    esac

    # Initial completion
    case "$cur" in
        -*)
            COMPREPLY=($(compgen -W "${opts[*]}" -- "$cur"))
            return 0
            ;;
        *)
            return 0
            ;;
    esac
} && \
complete -F _quodlibet quodlibet	
