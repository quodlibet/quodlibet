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

# Quodlibet tags

_ql_tags_make() {
    command -v operon >/dev/null 2>&1 || return
    operon tags -a -t -c tag | tr '\n' ' '
}

_ql_tags="$(_ql_tags_make)"

# Quodlibet supported extensions (as bash globs)

_ql_audio_glob_make() {
    command -v python3   >/dev/null 2>&1 || return
    command -v quodlibet >/dev/null 2>&1 || return

    python3 - << EOF
from quodlibet.formats import init, loaders
init()
exts = []
for k in sorted(loaders.keys()):
    dot, ext = k.split('.', 1)
    exts.append(ext)
print('@(' + '|'.join(exts) + ')')
EOF
}

_ql_audio_glob="$(_ql_audio_glob_make)"
_ql_img_glob="@(gif|jp?(e)g|png)"

# Quodlibet completion

_quodlibet() {
    # Assigned variable by _init_completion:
    #   cur    Current argument.
    #   prev   Previous argument.
    #   words  Argument array.
    #   cword  Argument array size.
    local cur prev words cword
    _init_completion -n = || return

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
            _filedir "$_ql_audio_glob"
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
            comps="$_ql_tags"
            COMPREPLY=($(compgen -S= -W "$comps" -- "$cur"))
            return 0
            ;;

        --random) # tag
            comps="$_ql_tags"
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

# Operon completion

_in_array() {
    local i
    for i in "${@:2}"; do
        [[ $1 = "$i" ]] && return
    done
}

_operon() {
    # Assigned variable by _init_completion:
    #   cur    Current argument.
    #   prev   Previous argument.
    #   words  Argument array.
    #   cword  Argument array size.
    local cur prev words cword
    _init_completion -n = || return

    # Operon commands and options
    local opts=(--help --verbose --version)
    local cmds=(add clear copy edit fill help \
                image-clear image-extract image-set \
                info list print remove set tags)

    # Check if a command was entered already
    local command i
    for (( i=0; i < ${#words[@]}-1; i++ )); do
        if _in_array "${words[i]}" "${cmds[@]}"; then
            command=${words[i]}
            break
        fi
    done

    # Completion per command
    if [[ -n $command ]]; then
        case $command in
            add) # <tag> <value> <file> [<files>]
                nargs=0
                for (( j=i+1; j < ${#words[@]}-1; j++ )); do
                    case "${words[j]}" in
                        -*) continue ;;
                        *)  nargs=$((nargs+1)) ;;
                    esac
                done
                if [[ $nargs -eq 0 ]]; then
                    comps="$_ql_tags"
                    COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                elif [[ $nargs -ge 2 ]]; then
                    _filedir "$_ql_audio_glob"
                fi
                return 0
                ;;

            clear) # [--dry-run] [-a | -e <pattern> | <tag>] <file> [<files>]
                case $cur in
                    -*)
                        comps="--all --dry-run --regexp"
                        COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                        ;;
                    *)
                        case $prev in
                            -a|--all)
                                compopt -o default
                                COMPREPLY=()
                                ;;
                            -e|--regex)
                                ;;
                            *)
                                nargs=0
                                for (( j=i+1; j < ${#words[@]}-1; j++ )); do
                                    case "${words[j]}" in
                                        -d|--dry-run) continue ;;
                                        -e|--regexp)  continue ;;
                                        -a|--all)     nargs=$((nargs+1)) ;;
                                        *)            nargs=$((nargs+1)) ;;
                                    esac
                                done
                                if [[ $nargs -eq 0 ]]; then
                                    comps="$_ql_tags"
                                    COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                                elif [[ $nargs -ge 1 ]]; then
                                    _filedir "$_ql_audio_glob"
                                fi
                                ;;
                        esac
                esac
                return 0
                ;;

            copy) # [--dry-run] [--ignore-errors] <source> <dest>
                case $cur in
                    -*)
                        comps="--dry-run --ignore-errors"
                        COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                        ;;
                    *)
                        _filedir "$_ql_audio_glob"
                        ;;
                esac
                return 0
                ;;

            edit) # [--dry-run] <file>
                case $cur in
                    -*)
                        comps="--dry-run"
                        COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                        ;;
                    *)
                        _filedir "$_ql_audio_glob"
                        ;;
                esac
                return 0
                ;;

            fill) # [--dry-run] <pattern> <file> [<files>]
                case $cur in
                    -*)
                        comps="--dry-run"
                        COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                        ;;
                    *)
                        # no completion for <pattern>
                        nargs=0
                        for (( j=i+1; j < ${#words[@]}-1; j++ )); do
                            case "${words[j]}" in
                                -*) continue ;;
                                *)  nargs=$((nargs+1)) ;;
                            esac
                        done
                        if [[ $nargs -ge 1 ]]; then
                            _filedir "$_ql_audio_glob"
                        fi
                        ;;
                esac
                return 0
                ;;

            help) # [<command>]
                COMPREPLY=($(compgen -W "${cmds[*]}" -- "$cur"))
                return 0
                ;;

            image-clear) # <file> [<files>]
                _filedir "$_ql_audio_glob"
                return 0
                ;;

            image-extract) # [--dry-run] [--primary] [-d <destination>] <file> [<files>]
                case $cur in
                    -*)
                        comps="--destination --dry-run --primary"
                        COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                        ;;
                    *)
                        case $prev in
                            -d|--destination)
                                compopt -o default
                                COMPREPLY=()
                                ;;
                            *)
                                _filedir "$_ql_audio_glob"
                                ;;
                        esac
                        ;;
                esac
                return 0
                ;;

            image-set) # <image-file> <file> [<files>]
                case $prev in
                    image-set)
                        _filedir "$_ql_img_glob"
                        ;;
                    *)
                        _filedir "$_ql_audio_glob"
                        ;;
                esac
                return 0
                ;;

            info) # [-t] [-c <c1>,<c2>...] <file>
                case $cur in
                    -*)
                        comps="--columns --terse"
                        COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                        ;;
                    *)
                        case $prev in
                            -c|--columns)
                                ;;
                            *)
                                _filedir "$_ql_audio_glob"
                                ;;
                        esac
                        ;;
                esac
                return 0
                ;;

            list) # [-a] [-t] [-c <c1>,<c2>...] <file>
                case $cur in
                    -*)
                        comps="--all --columns --terse"
                        COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                        ;;
                    *)
                        case $prev in
                            -c|--columns)
                                ;;
                            *)
                                _filedir "$_ql_audio_glob"
                                ;;
                        esac
                        ;;
                esac
                return 0
                ;;

            print) # [-p <pattern>] <file> [<files>]
                case $cur in
                    -*)
                        comps="--pattern"
                        COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                        ;;
                    *)
                        case $prev in
                            -p|--pattern)
                                ;;
                            *)
                                _filedir "$_ql_audio_glob"
                                ;;
                        esac
                        ;;
                esac
                return 0
                ;;

            remove) # [--dry-run] <tag> [-e <pattern> | <value>] <file> [<files>]
                case $cur in
                    -*)
                        comps="--dry-run --regexp"
                        COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                        ;;
                    *)
                        nargs=0
                        for (( j=i+1; j < ${#words[@]}-1; j++ )); do
                            case "${words[j]}" in
                                -*) continue ;;
                                *)  nargs=$((nargs+1)) ;;
                            esac
                        done
                        if [[ $nargs -eq 0 ]]; then
                            comps="$_ql_tags"
                            COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                        elif [[ $nargs -ge 2 ]]; then
                            _filedir "$_ql_audio_glob"
                        fi
                        ;;
                esac
                return 0
                ;;

            set) # [--dry-run] <tag> <value> <file> [<files>]
                case $cur in
                    -*)
                        comps="--dry-run"
                        COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                        ;;
                    *)
                        nargs=0
                        for (( j=i+1; j < ${#words[@]}-1; j++ )); do
                            case "${words[j]}" in
                                -*) continue ;;
                                *)  nargs=$((nargs+1)) ;;
                            esac
                        done
                        if [[ $nargs -eq 0 ]]; then
                            comps="$_ql_tags"
                            COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                        elif [[ $nargs -ge 2 ]]; then
                            _filedir "$_ql_audio_glob"
                        fi
                        ;;
                esac
                return 0
                ;;

            tags) # [-t] [-c <c1>,<c2>...]
                case $cur in
                    -*)
                        comps="--all --columns --terse"
                        COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                        ;;
                esac
                return 0
                ;;
        esac
    fi

    # Initial completion
    case "$cur" in
        -*)
            COMPREPLY=($(compgen -W "${opts[*]}" -- "$cur"))
            return 0
            ;;
        *)
            COMPREPLY=($(compgen -W "${cmds[*]}" -- "$cur"))
            return 0
            ;;
    esac

} && \
complete -F _operon operon
