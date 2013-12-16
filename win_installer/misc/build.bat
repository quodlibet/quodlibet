set PATH=%PATH%;C:\Python27\;C:\Python27\Scripts

set GI_TYPELIB_PATH=%~dp0\deps\lib\girepository-1.0
set PATH=%PATH%;%~dp0\deps;

python bin/ez_setup.py
easy_install pip

pip install bin\mutagen-1.22.tar.gz
pip install bin\feedparser-5.1.3.tar.bz2
pip install bin\python-musicbrainz2-0.7.4.tar.gz

easy_install -Z bin\pywin32-218.win32-py2.7.exe
easy_install -Z bin\py2exe-0.6.9.win32-py2.7.exe
easy_install -Z bin\pyHook-1.5.1.win32-py2.7.exe

cd ql_temp
cd quodlibet
python setup.py py2exe
