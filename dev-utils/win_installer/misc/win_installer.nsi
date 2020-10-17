; Copyright 2016 Christoph Reiter
;
; This program is free software; you can redistribute it and/or modify
; it under the terms of the GNU General Public License as published by
; the Free Software Foundation; either version 2 of the License, or
; (at your option) any later version.

Unicode true

!define QL_NAME "Quod Libet"
!define QL_ID "quodlibet"
!define QL_DESC "Music Library / Editor / Player"

!define EF_NAME "Ex Falso"
!define EF_ID "exfalso"

!define QL_WEBSITE "https://quodlibet.readthedocs.io"

!define QL_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${QL_NAME}"
!define QL_INSTDIR_KEY "Software\${QL_NAME}"
!define QL_INSTDIR_VALUENAME "InstDir"

!define MUI_CUSTOMFUNCTION_GUIINIT custom_gui_init
!include "MUI2.nsh"
!include "FileFunc.nsh"

Name "${QL_NAME} (${VERSION})"
OutFile "quodlibet-LATEST.exe"
SetCompressor /SOLID /FINAL lzma
SetCompressorDictSize 32
InstallDir "$PROGRAMFILES\${QL_NAME}"
RequestExecutionLevel admin

Var EF_INST_BIN
Var QL_INST_BIN
Var UNINST_BIN

!define MUI_ABORTWARNING
!define MUI_ICON "..\quodlibet.ico"

!insertmacro MUI_PAGE_LICENSE "..\quodlibet\COPYING"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Afrikaans"
!insertmacro MUI_LANGUAGE "Albanian"
!insertmacro MUI_LANGUAGE "Arabic"
!insertmacro MUI_LANGUAGE "Basque"
!insertmacro MUI_LANGUAGE "Belarusian"
!insertmacro MUI_LANGUAGE "Bosnian"
!insertmacro MUI_LANGUAGE "Breton"
!insertmacro MUI_LANGUAGE "Bulgarian"
!insertmacro MUI_LANGUAGE "Catalan"
!insertmacro MUI_LANGUAGE "Croatian"
!insertmacro MUI_LANGUAGE "Czech"
!insertmacro MUI_LANGUAGE "Danish"
!insertmacro MUI_LANGUAGE "Dutch"
!insertmacro MUI_LANGUAGE "Esperanto"
!insertmacro MUI_LANGUAGE "Estonian"
!insertmacro MUI_LANGUAGE "Farsi"
!insertmacro MUI_LANGUAGE "Finnish"
!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_LANGUAGE "Galician"
!insertmacro MUI_LANGUAGE "German"
!insertmacro MUI_LANGUAGE "Greek"
!insertmacro MUI_LANGUAGE "Hebrew"
!insertmacro MUI_LANGUAGE "Hungarian"
!insertmacro MUI_LANGUAGE "Icelandic"
!insertmacro MUI_LANGUAGE "Indonesian"
!insertmacro MUI_LANGUAGE "Irish"
!insertmacro MUI_LANGUAGE "Italian"
!insertmacro MUI_LANGUAGE "Japanese"
!insertmacro MUI_LANGUAGE "Korean"
!insertmacro MUI_LANGUAGE "Kurdish"
!insertmacro MUI_LANGUAGE "Latvian"
!insertmacro MUI_LANGUAGE "Lithuanian"
!insertmacro MUI_LANGUAGE "Luxembourgish"
!insertmacro MUI_LANGUAGE "Macedonian"
!insertmacro MUI_LANGUAGE "Malay"
!insertmacro MUI_LANGUAGE "Mongolian"
!insertmacro MUI_LANGUAGE "Norwegian"
!insertmacro MUI_LANGUAGE "NorwegianNynorsk"
!insertmacro MUI_LANGUAGE "Polish"
!insertmacro MUI_LANGUAGE "PortugueseBR"
!insertmacro MUI_LANGUAGE "Portuguese"
!insertmacro MUI_LANGUAGE "Romanian"
!insertmacro MUI_LANGUAGE "Russian"
!insertmacro MUI_LANGUAGE "SerbianLatin"
!insertmacro MUI_LANGUAGE "Serbian"
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "Slovak"
!insertmacro MUI_LANGUAGE "Slovenian"
!insertmacro MUI_LANGUAGE "SpanishInternational"
!insertmacro MUI_LANGUAGE "Spanish"
!insertmacro MUI_LANGUAGE "Swedish"
!insertmacro MUI_LANGUAGE "Thai"
!insertmacro MUI_LANGUAGE "TradChinese"
!insertmacro MUI_LANGUAGE "Turkish"
!insertmacro MUI_LANGUAGE "Ukrainian"
!insertmacro MUI_LANGUAGE "Uzbek"
!insertmacro MUI_LANGUAGE "Welsh"


Section "Install"
    SetShellVarContext all

    ; Use this to make things faster for testing installer changes
    ;~ SetOutPath "$INSTDIR\bin"
    ;~ File /r "mingw32\bin\*.exe"

    SetOutPath "$INSTDIR"
    File /r "*.*"

    StrCpy $EF_INST_BIN "$INSTDIR\bin\exfalso.exe"
    StrCpy $QL_INST_BIN "$INSTDIR\bin\quodlibet.exe"
    StrCpy $UNINST_BIN "$INSTDIR\uninstall.exe"

    ; Store installation folder
    WriteRegStr HKLM "${QL_INSTDIR_KEY}" "${QL_INSTDIR_VALUENAME}" $INSTDIR

    ; Set up an entry for the uninstaller
    WriteRegStr HKLM "${QL_UNINST_KEY}" \
        "DisplayName" "${QL_NAME} - ${QL_DESC}"
    WriteRegStr HKLM "${QL_UNINST_KEY}" "DisplayIcon" "$\"$QL_INST_BIN$\""
    WriteRegStr HKLM "${QL_UNINST_KEY}" "UninstallString" \
        "$\"$UNINST_BIN$\""
    WriteRegStr HKLM "${QL_UNINST_KEY}" "QuietUninstallString" \
    "$\"$UNINST_BIN$\" /S"
    WriteRegStr HKLM "${QL_UNINST_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "${QL_UNINST_KEY}" "HelpLink" "${QL_WEBSITE}"
    WriteRegStr HKLM "${QL_UNINST_KEY}" "Publisher" "The ${QL_NAME} Development Community"
    WriteRegStr HKLM "${QL_UNINST_KEY}" "DisplayVersion" "${VERSION}"
    WriteRegDWORD HKLM "${QL_UNINST_KEY}" "NoModify" 0x1
    WriteRegDWORD HKLM "${QL_UNINST_KEY}" "NoRepair" 0x1
    ; Installation size
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "${QL_UNINST_KEY}" "EstimatedSize" "$0"

    ; Folder association for Ex Falso
    ; Context menu for folders
    WriteRegStr HKLM  "Software\Classes\Directory\shell\${EF_ID}" "Icon" "$EF_INST_BIN"
    WriteRegStr HKLM  "Software\Classes\Directory\shell\${EF_ID}" "MUIVerb" "${EF_NAME}"
    WriteRegStr HKLM  "Software\Classes\Directory\shell\${EF_ID}\command" "" "$\"$EF_INST_BIN$\" $\"%1$\""

    ; Context menu by shift+right clicking on explorer background
    WriteRegStr HKLM  "Software\Classes\Directory\Background\shell\${EF_ID}" "Icon" "$EF_INST_BIN"
    WriteRegStr HKLM  "Software\Classes\Directory\Background\shell\${EF_ID}" "MUIVerb" "${EF_NAME}"

    ; Extended hides it if shift isn't pressed, like the cmd entry
    WriteRegStr HKLM  "Software\Classes\Directory\Background\shell\${EF_ID}" "Extended" ""
    WriteRegStr HKLM  "Software\Classes\Directory\Background\shell\${EF_ID}\command" "" "$\"$EF_INST_BIN$\" $\"%V$\""

    ; Register a default entry for file extensions
    WriteRegStr HKLM "Software\Classes\${QL_ID}.assoc.ANY\shell\play\command" "" "$\"$QL_INST_BIN$\" --run --play-file $\"%1$\""
    WriteRegStr HKLM "Software\Classes\${QL_ID}.assoc.ANY\DefaultIcon" "" "$\"$QL_INST_BIN$\""
    WriteRegStr HKLM "Software\Classes\${QL_ID}.assoc.ANY\shell\play" "FriendlyAppName" "${QL_NAME}"

    ; Add application entry
    WriteRegStr HKLM "Software\${QL_NAME}\${QL_ID}\Capabilities" "ApplicationDescription" "${QL_DESC}"
    WriteRegStr HKLM "Software\${QL_NAME}\${QL_ID}\Capabilities" "ApplicationName" "${QL_NAME}"

    ; Register supported file extensions
    ; (generated using gen_supported_types.py)
    !define QL_ASSOC_KEY "Software\${QL_NAME}\${QL_ID}\Capabilities\FileAssociations"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".3g2" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".3gp" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".3gp2" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".669" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".aac" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".adif" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".adts" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".aif" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".aifc" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".aiff" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".amf" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".ams" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".ape" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".asf" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".dsf" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".dsm" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".far" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".flac" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".gdm" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".it" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".m4a" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".m4v" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".med" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".mid" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".mod" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".mp+" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".mp1" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".mp2" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".mp3" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".mp4" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".mpc" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".mpeg" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".mpg" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".mt2" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".mtm" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".oga" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".ogg" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".oggflac" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".ogv" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".okt" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".opus" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".s3m" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".spc" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".spx" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".stm" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".tta" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".ult" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".vgm" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".wav" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".wma" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".wmv" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".wv" "${QL_ID}.assoc.ANY"
    WriteRegStr HKLM "${QL_ASSOC_KEY}" ".xm" "${QL_ID}.assoc.ANY"

    ; Register application entry
    WriteRegStr HKLM "Software\RegisteredApplications" "${QL_NAME}" "Software\${QL_NAME}\${QL_ID}\Capabilities"

    ; Register app paths
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\quodlibet.exe" "" "$QL_INST_BIN"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\exfalso.exe" "" "$EF_INST_BIN"

    ; Create uninstaller
    WriteUninstaller "$UNINST_BIN"

    ; Create start menu shortcuts
    CreateDirectory "$SMPROGRAMS\${QL_NAME}"
    CreateShortCut "$SMPROGRAMS\${QL_NAME}\${QL_NAME}.lnk" "$QL_INST_BIN"
    CreateShortCut "$SMPROGRAMS\${QL_NAME}\${EF_NAME}.lnk" "$EF_INST_BIN"
SectionEnd

Function custom_gui_init
    BringToFront

    ; Read the install dir and set it
    Var /GLOBAL instdir_temp
    Var /GLOBAL uninst_bin_temp

    SetRegView 32
    ReadRegStr $instdir_temp HKLM "${QL_INSTDIR_KEY}" "${QL_INSTDIR_VALUENAME}"
    SetRegView lastused
    StrCmp $instdir_temp "" skip 0
        StrCpy $INSTDIR $instdir_temp
    skip:

    SetRegView 64
    ReadRegStr $instdir_temp HKLM "${QL_INSTDIR_KEY}" "${QL_INSTDIR_VALUENAME}"
    SetRegView lastused
    StrCmp $instdir_temp "" skip2 0
        StrCpy $INSTDIR $instdir_temp
    skip2:

    StrCpy $uninst_bin_temp "$INSTDIR\uninstall.exe"

    ; try to un-install existing installations first
    IfFileExists "$INSTDIR" do_uninst do_continue
    do_uninst:
        ; instdir exists
        IfFileExists "$uninst_bin_temp" exec_uninst rm_instdir
        exec_uninst:
            ; uninstall.exe exists, execute it and
            ; if it returns success proceed, otherwise abort the
            ; installer (uninstall aborted by user for example)
            ExecWait '"$uninst_bin_temp" _?=$INSTDIR' $R1
            ; uninstall succeeded, since the uninstall.exe is still there
            ; goto rm_instdir as well
            StrCmp $R1 0 rm_instdir
            ; uninstall failed
            Abort
        rm_instdir:
            ; either the uninstaller was successfull or
            ; the uninstaller.exe wasn't found
            RMDir /r "$INSTDIR"
    do_continue:
        ; the instdir shouldn't exist from here on

    BringToFront
FunctionEnd

Section "Uninstall"
    SetShellVarContext all
    SetAutoClose true

    ; Remove start menu entries
    Delete "$SMPROGRAMS\${QL_NAME}\${QL_NAME}.lnk"
    Delete "$SMPROGRAMS\${QL_NAME}\${EF_NAME}.lnk"
    RMDir "$SMPROGRAMS\${QL_NAME}"

    ; Remove exfalso folder association
    DeleteRegKey HKLM "Software\Classes\Directory\shell\${EF_ID}"
    DeleteRegKey HKLM "Software\Classes\Directory\Background\shell\${EF_ID}"

    ; Remove application registration and file assocs
    DeleteRegKey HKLM "Software\Classes\${QL_ID}.assoc.ANY"
    DeleteRegKey HKLM "Software\${QL_NAME}"
    DeleteRegValue HKLM "Software\RegisteredApplications" "${QL_NAME}"

    ; Remove app paths
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\quodlibet.exe"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\exfalso.exe"

    ; Delete installation related keys
    DeleteRegKey HKLM "${QL_UNINST_KEY}"
    DeleteRegKey HKLM "${QL_INSTDIR_KEY}"

    ; Delete files
    RMDir /r "$INSTDIR"
SectionEnd
