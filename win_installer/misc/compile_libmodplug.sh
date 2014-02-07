#!/bin/sh

wget -c "http://sourceforge.net/projects/modplug-xmms/files/libmodplug/0.8.8.4/libmodplug-0.8.8.4.tar.gz"
tar -zxvf "libmodplug-0.8.8.4.tar.gz"
cd "libmodplug-0.8.8.4"
./configure --host=i586-mingw32msvc --prefix=`pwd`"/prefix" CFLAGS='-Os' CXXFLAGS='-Os'
make clean
make -j
make install
cp "prefix/bin/libmodplug-1.dll" "../"
cd ..
rm -Rf "libmodplug-0.8.8.4"
rm "libmodplug-0.8.8.4.tar.gz"
