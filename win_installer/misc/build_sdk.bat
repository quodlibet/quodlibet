set PATH=%PATH%;C:\Python27\

set GI_TYPELIB_PATH=%~dp0\deps\lib\girepository-1.0
set PATH=%PATH%;%~dp0\deps;

python -m pip install bin\mutagen-1.27.tar.gz
python -m pip install bin\feedparser-5.1.3.tar.bz2
python -m pip install bin\python-musicbrainz2-0.7.4.tar.gz

python -m easy_install -Z bin\pywin32-218.win32-py2.7.exe
python -m easy_install -Z bin\py2exe-0.6.9.win32-py2.7.exe
python -m easy_install -Z bin\pyHook-1.5.1.win32-py2.7.exe
