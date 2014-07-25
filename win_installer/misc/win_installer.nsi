;Quod Libet / Ex Falso Windows installer script
;Modified by Steven Robertson, Christoph Reiter
;Based on the NSIS Modern User Interface Start Menu Folder Example Script
;Written by Joost Verburg

  ;compression
  SetCompressor /SOLID LZMA

  !define MULTIUSER_EXECUTIONLEVEL Highest
  !define MULTIUSER_MUI
  !define MULTIUSER_INSTALLMODE_COMMANDLINE
  !include "MultiUser.nsh"

  !define UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\Quod Libet"
  !define INSTDIR_KEY "Software\Quod Libet"
  !define INSTDIR_SUBKEY "InstDir"

;--------------------------------
;Include Modern UI

  !include "MUI2.nsh"

;--------------------------------
;General

  ;Name and file
  Name "Quod Libet"
  OutFile "quodlibet-LATEST.exe"

  ;Default installation folder
  InstallDir "$PROGRAMFILES\Quod Libet"
  
  ;Get installation folder from registry if available
  ;InstallDirRegKey HKCU "${INSTDIR_KEY}" ""
  ;doesn't work with multi user -> see onInit..

  ;Request application privileges for Windows Vista
  RequestExecutionLevel admin

;--------------------------------
;Variables

  Var StartMenuFolder
  Var instdir_temp

;--------------------------------
;Interface Settings

  !define MUI_ABORTWARNING
  !define MUI_ICON "quodlibet.ico"

;--------------------------------
;Pages

  !insertmacro MULTIUSER_PAGE_INSTALLMODE
  !insertmacro MUI_PAGE_LICENSE "ql_temp\quodlibet\COPYING"
  !insertmacro MUI_PAGE_DIRECTORY
  
  ;Start Menu Folder Page Configuration
  !define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKCU" 
  !define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\Quod Libet" 
  !define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "Start Menu Folder"
  
  !insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder
  
  !insertmacro MUI_PAGE_INSTFILES
  
  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
;Languages
 
  !insertmacro MUI_LANGUAGE "English" ;first language is the default language
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

;--------------------------------
;Installer Sections

Section "Dummy Section" SecDummy

  SetOutPath "$INSTDIR"

  File /r "ql_temp\quodlibet\dist\*.*" 

  ;Old installer wrote the path to HKCU only, delete it
  DeleteRegKey HKCU "Software\Quod Libet"
  ;Store installation folder
  WriteRegStr SHCTX "${INSTDIR_KEY}" "${INSTDIR_SUBKEY}" $INSTDIR

  ;Multi user uninstaller stuff
  WriteRegStr SHCTX "${UNINST_KEY}" \
    "DisplayName" "Quod Libet - audio library tagger, manager, and player"
  WriteRegStr SHCTX "${UNINST_KEY}" "DisplayIcon" "$\"$INSTDIR\bin\quodlibet.exe$\""
  WriteRegStr SHCTX "${UNINST_KEY}" "UninstallString" \
    "$\"$INSTDIR\uninstall.exe$\" /$MultiUser.InstallMode"
  WriteRegStr SHCTX "${UNINST_KEY}" "QuietUninstallString" \
    "$\"$INSTDIR\uninstall.exe$\" /$MultiUser.InstallMode /S"

  ; Folder association for Ex Falso
  ; Context menu for folders
  WriteRegStr HKCR  "Directory\shell\quodlibet" "Icon" "$INSTDIR\bin\exfalso.exe"
  WriteRegStr HKCR  "Directory\shell\quodlibet" "MUIVerb" "Ex Falso"
  WriteRegStr HKCR  "Directory\shell\quodlibet\command" "" "$INSTDIR\bin\exfalso.exe $\"%1$\""
  ; Context menu by shift+right clicking on explorer background
  WriteRegStr HKCR  "Directory\Background\shell\quodlibet" "Icon" "$INSTDIR\bin\exfalso.exe"
  WriteRegStr HKCR  "Directory\Background\shell\quodlibet" "MUIVerb" "Ex Falso"
  ; Extended hides it if shift isn't pressed, like the cmd entry
  WriteRegStr HKCR  "Directory\Background\shell\quodlibet" "Extended" ""
  WriteRegStr HKCR  "Directory\Background\shell\quodlibet\command" "" "$INSTDIR\bin\exfalso.exe $\"%V$\""

  ;Create uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"
  
  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
    
    ;Create shortcuts
    CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
    CreateShortCut "$SMPROGRAMS\$StartMenuFolder\Quod Libet.lnk" "$INSTDIR\bin\quodlibet.exe"
    CreateShortCut "$SMPROGRAMS\$StartMenuFolder\Ex Falso.lnk" "$INSTDIR\bin\exfalso.exe"
  
  !insertmacro MUI_STARTMENU_WRITE_END

SectionEnd

Function .onInit
  !insertmacro MULTIUSER_INIT

  ;Read the install dir and set it
  ReadRegStr $instdir_temp SHCTX "${INSTDIR_KEY}" "${INSTDIR_SUBKEY}"
  StrCmp $instdir_temp "" skip 0
    StrCpy $INSTDIR $instdir_temp
  skip:

  ; try to un-install existing installations first
  IfFileExists "$INSTDIR" do_uninst do_continue
    do_uninst:
        ; instdir exists
        IfFileExists "$INSTDIR\uninstall.exe" exec_uninst rm_instdir
        exec_uninst:
            ; uninstall.exe exists, execute it and
            ; if it returns success proceede, otherwise abort the installer
            ; (uninstall aborted by user for example)
            ExecWait '"$INSTDIR\uninstall.exe" _?=$INSTDIR' $R1
            ; uninstall suceeded, since the uninstall.exe is still there
            ; goto rm_instdir as well
            StrCmp $R1 0 rm_instdir
            ; uninstall failed
            Abort
        rm_instdir:
            ; either the uninstaller was sucessfull or
            ; the uninstaller.exe wasn't found
            RMDir /r "$INSTDIR"
    do_continue:
        ; the instdir shouldn't exist from here on

FunctionEnd

;--------------------------------
;Uninstaller Section

Section "Uninstall"

  RMDir /r "$INSTDIR"

  Delete "$INSTDIR\uninstall.exe"

  !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder

  Delete "$SMPROGRAMS\$StartMenuFolder\Quod Libet.lnk"
  Delete "$SMPROGRAMS\$StartMenuFolder\Ex Falso.lnk"
  RMDir "$SMPROGRAMS\$StartMenuFolder"

  ; Remove folder association
  DeleteRegKey HKCR "Directory\shell\quodlibet\command"
  DeleteRegKey HKCR "Directory\shell\quodlibet"
  DeleteRegKey HKCR "Directory\Background\shell\quodlibet\command"
  DeleteRegKey HKCR "Directory\Background\shell\quodlibet"

  ;Old installer wrote the path to HKCU only, delete it
  DeleteRegKey HKCU "Software\Quod Libet"

  DeleteRegKey SHCTX "${UNINST_KEY}"
  DeleteRegKey SHCTX "${INSTDIR_KEY}"

SectionEnd

Function un.onInit
  !insertmacro MULTIUSER_UNINIT
FunctionEnd


