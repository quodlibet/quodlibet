set GI_TYPELIB_PATH=%~dp0\deps\lib\girepository-1.0
set PATH=%~dp0\deps;%~dp0\python;%~dp0\python\Lib\site-packages\pywin32_system32;%PATH%
set QUODLIBET_USERDIR=%~dp0\_ql_config
python %~dp0\quodlibet\quodlibet\quodlibet.py
