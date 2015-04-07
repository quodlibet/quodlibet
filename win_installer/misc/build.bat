set PATH=%PATH%;C:\Python27\

set GI_TYPELIB_PATH=%~dp0\deps\lib\girepository-1.0
set PATH=%PATH%;%~dp0\deps;

cd ql_temp
cd quodlibet
python setup.py py2exe
