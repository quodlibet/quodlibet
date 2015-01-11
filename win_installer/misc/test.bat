call env.bat
python %~dp0quodlibet\quodlibet\setup.py clean --all
python %~dp0quodlibet\quodlibet\setup.py test
