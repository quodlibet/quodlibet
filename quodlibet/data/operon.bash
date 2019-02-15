# operon(1) completion                             -*- shell-script -*-
# vim: sts=4 sw=4 et

__tags() {
    operon tags -a -t -c tag | tr '\n' ' '
}

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
                    comps=$(__tags)
                    COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                elif [[ $nargs -ge 2 ]]; then
                    compopt -o default
                    COMPREPLY=()
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
                                    comps=$(__tags)
                                    COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                                elif [[ $nargs -ge 1 ]]; then
                                    compopt -o default
                                    COMPREPLY=()
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
                        compopt -o default
                        COMPREPLY=()
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
                        compopt -o default
                        COMPREPLY=()
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
                            compopt -o default
                            COMPREPLY=()
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
                compopt -o default
                COMPREPLY=()
                return 0
                ;;

            image-extract) # [--dry-run] [--primary] [-d <destination>] <file> [<files>]
                case $cur in
                    -*)
                        comps="--destination --dry-run --primary"
                        COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                        ;;
                    *)
                        compopt -o default
                        COMPREPLY=()
                        ;;
                esac
                return 0
                ;;

            image-set) # <image-file> <file> [<files>]
                compopt -o default
                COMPREPLY=()
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
                                compopt -o default
                                COMPREPLY=()
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
                                compopt -o default
                                COMPREPLY=()
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
                            -c|--pattern)
                                ;;
                            *)
                                compopt -o default
                                COMPREPLY=()
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
                            comps=$(__tags)
                            COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                        elif [[ $nargs -ge 2 ]]; then
                            compopt -o default
                            COMPREPLY=()
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
                            comps=$(__tags)
                            COMPREPLY=($(compgen -W "$comps" -- "$cur"))
                        elif [[ $nargs -ge 2 ]]; then
                            compopt -o default
                            COMPREPLY=()
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

# ex: filetype=sh
