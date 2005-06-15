#include <boost/python.hpp>
#include <taglib/taglib.h>
#include <taglib/fileref.h>
#include <taglib/tbytevector.h>
#include <taglib/audioproperties.h>
#include <taglib/oggfile.h>
#include <taglib/vorbisfile.h>
#include <taglib/vorbisproperties.h>

using namespace boost::python;

BOOST_PYTHON_MODULE(taglib) {
  class_<TagLib::FileRef>("FileRef", init<const char *>())
    .def("isNull", &TagLib::FileRef::isNull)
    ;

  class_<TagLib::ByteVector>("ByteVector", no_init);

  class_<TagLib::AudioProperties, boost::noncopyable>
    ("AudioProperties", no_init)
    .add_property("length", &TagLib::AudioProperties::length)
    .add_property("bitrate", &TagLib::AudioProperties::bitrate)
    .add_property("sampleRate", &TagLib::AudioProperties::sampleRate)
    .add_property("channels", &TagLib::AudioProperties::channels)
    ;

  class_<TagLib::File, boost::noncopyable>("File", no_init)
    .add_property("name", &TagLib::File::name)
    .add_property("size", &TagLib::File::length)
    .def("read", &TagLib::File::readBlock)
    .def("seek", &TagLib::File::seek)
    .def("tell", &TagLib::File::tell)
    //.def("audioProperties", pure_virtual(&TagLib::File::audioProperties))
    ;

  class_<TagLib::Ogg::File, boost::noncopyable, bases<TagLib::File> >
    ("OggFile", no_init)
    .def("__getitem__", &TagLib::Ogg::File::packet)
    .def("__setitem__", &TagLib::Ogg::File::setPacket)
    ;

  class_<TagLib::Ogg::Vorbis::File, boost::noncopyable,
    bases<TagLib::Ogg::File> >("VorbisFile", init<const char *>())
    ;
  
  class_<TagLib::Ogg::Vorbis::AudioProperties, boost::noncopyable,
    bases<TagLib::AudioProperties> >
    ("VorbisProperties", no_init)
    ;
  
}
