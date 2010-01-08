;Quod Libet / Ex Falso Windows installer script
;Modified by Steven Robertson
;Based on the NSIS Modern User Interface Start Menu Folder Example Script
;Written by Joost Verburg

;--------------------------------
;Include Modern UI

  !include "MUI2.nsh"

;--------------------------------
;General

  ;Name and file
  SetCompressor /SOLID lzma
  Name "Quod Libet"
  OutFile "quodlibet-LATEST.exe"
  Icon "..\quodlibet\quodlibet\images\quodlibet.ico"

  ;Default installation folder
  InstallDir "$PROGRAMFILES\Quod Libet"
  
  ;Get installation folder from registry if available
  InstallDirRegKey HKCU "Software\Quod Libet" ""

  ;Request application privileges for Windows Vista
  RequestExecutionLevel admin

;--------------------------------
;Variables

  Var StartMenuFolder

;--------------------------------
;Interface Settings

  !define MUI_ABORTWARNING

;--------------------------------
;Pages

  !insertmacro MUI_PAGE_LICENSE "..\quodlibet\COPYING"
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
 
  !insertmacro MUI_LANGUAGE "English"

;--------------------------------
;Installer Sections

Section "Dummy Section" SecDummy

  SetOutPath "$INSTDIR"
  
  File /r "..\quodlibet\dist\*.*" 
 
  ;Store installation folder
  WriteRegStr HKCU "Software\Quod Libet" "" $INSTDIR
  
  ;Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  
  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
    
    ;Create shortcuts
    CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
    CreateShortCut "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    CreateShortCut "$SMPROGRAMS\$StartMenuFolder\Quod Libet.lnk" "$INSTDIR\quodlibet.exe"
    CreateShortCut "$SMPROGRAMS\$StartMenuFolder\Ex Falso.lnk" "$INSTDIR\exfalso.exe"
  
  !insertmacro MUI_STARTMENU_WRITE_END

SectionEnd
 
;--------------------------------
;Uninstaller Section

Section "Uninstall"

  Delete "$INSTDIR\Uninstall.exe"

  RMDir /r "$INSTDIR"
  
  !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder
    
  Delete "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk"
  Delete "$SMPROGRAMS\$StartMenuFolder\Quod Libet.lnk"
  Delete "$SMPROGRAMS\$StartMenuFolder\Ex Falso.lnk"
  RMDir "$SMPROGRAMS\$StartMenuFolder"
  
  DeleteRegKey /ifempty HKCU "Software\Quod Libet"

SectionEnd


