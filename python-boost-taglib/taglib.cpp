#include <Python.h>

#include <boost/python.hpp>
#include <taglib/taglib.h>
#include <taglib/fileref.h>
#include <taglib/tbytevector.h>
#include <taglib/audioproperties.h>
#include <taglib/oggfile.h>
#include <taglib/vorbisfile.h>
#include <taglib/vorbisproperties.h>
#include <taglib/mpegfile.h>
#include <taglib/mpegproperties.h>

using namespace boost::python;
using namespace TagLib;

struct StringUnicodeConv {
  static PyObject *convert(String const &s) {
    const char *ustr = s.toCString();
    return PyUnicode_DecodeUTF8(ustr, strlen(ustr), "strict");
  }
};

struct ByteVectorToStr {
  static PyObject* convert(ByteVector const &b) {
    return PyString_FromStringAndSize(b.data(), b.size());
  }
};

// http://www.boost.org/libs/python/doc/v2/faq.html#custom_string
struct StringFromStr {
  StringFromStr() {
    converter::registry::push_back(&convertible, &construct,
				   type_id<String>());
  }

  static void *convertible(PyObject* o) {
    if (PyString_Check(o) || PyUnicode_Check(o)) return o;
    else return 0;
  }

  static void construct(PyObject* o,
			converter::rvalue_from_python_stage1_data *data) {
    if (PyUnicode_Check(o)) o = PyUnicode_AsUTF8String(o);
    const char *value = PyString_AsString(o);
    if (value == 0) throw_error_already_set();
    void* storage = ((converter::rvalue_from_python_storage<String> *)
		     data)->storage.bytes;
    new (storage) String(value);
    data->convertible = storage;
  }
};

struct ByteVectorFromStr {
  ByteVectorFromStr() {
    converter::registry::push_back(&convertible, &construct,
				   type_id<ByteVector>());
  }

  static void *convertible(PyObject* o) {
    if (PyString_Check(o)) return o;
    else return 0;
  }

  static void construct(PyObject* o,
			converter::rvalue_from_python_stage1_data *data) {
    void* storage = ((converter::rvalue_from_python_storage<ByteVector> *)
		     data)->storage.bytes;
    new (storage) ByteVector(PyString_AsString(o), PyString_Size(o));
    data->convertible = storage;
  }
};

/* TagLib uses isNull, isOpen; Python wants __nonzero__, file.closed.
   The "right" way is to subclass, but that's annoyingly painful for
   a simple !. */
bool FileRef_nonzero(FileRef &f) { return ! f.isNull(); }
bool File_isClosed(File &f) { return ! f.isOpen(); }

BOOST_PYTHON_MODULE(taglib) {
  // Enumerations //
  enum_<AudioProperties::ReadStyle>("ReadStyle")
    .value("FAST", AudioProperties::Fast)
    .value("AVERAGE", AudioProperties::Average)
    .value("ACCURATE", AudioProperties::Accurate)
    ;

  enum_<File::Position>("Position")
    .value("BEGINNING", File::Beginning)
    .value("CURRENT", File::Current)
    .value("END", File::End)
    ;

  enum_<MPEG::File::TagTypes>("TagTypes")
    .value("NOTAGS", MPEG::File::NoTags)
    .value("ID3V1", MPEG::File::ID3v1)
    .value("ID3V2", MPEG::File::ID3v2)
    .value("APE", MPEG::File::APE)
    .value("ALLTAGS", MPEG::File::AllTags)
    ;

  // Utility classes <-> Python types //
  to_python_converter<ByteVector, ByteVectorToStr>();
  to_python_converter<String, StringUnicodeConv>();
  ByteVectorFromStr();
  StringFromStr();

  class_<FileRef>("FileRef", init<const char *>())
    .def("save", &FileRef::save)
    .def("audioProperties", &FileRef::audioProperties,
	 return_value_policy<reference_existing_object>())
    .def("tag", &FileRef::tag,
	 return_value_policy<reference_existing_object>())
    .def("file", &FileRef::file,
	 return_value_policy<reference_existing_object>())
    .def("__nonzero__", &FileRef_nonzero)
    ;

  // Base abstract classes //

  class_<File, boost::noncopyable>("File", no_init)
    .add_property("name", &File::name)
    .add_property("size", &File::length)
    .def("read", &File::readBlock)
    .def("seek", &File::seek)
    .def("tell", &File::tell)
    .def("save", &File::save)
    .def("tag", &File::tag,
	 return_value_policy<reference_existing_object>())
    .def("audioProperties", &File::audioProperties,
	 return_value_policy<reference_existing_object>())
    .add_property("closed", &File_isClosed)
    ;

  class_<AudioProperties, boost::noncopyable>
    ("AudioProperties", no_init)
    .add_property("length", &AudioProperties::length)
    .add_property("bitrate", &AudioProperties::bitrate)
    .add_property("sampleRate", &AudioProperties::sampleRate)
    .add_property("channels", &AudioProperties::channels)
    ;

  class_<Tag, boost::noncopyable> ("Tag", no_init)
    .add_property("title", &Tag::title, &Tag::setTitle)
    .add_property("artist", &Tag::artist, &Tag::setArtist)
    .add_property("album", &Tag::album, &Tag::setAlbum)
    .add_property("genre", &Tag::genre, &Tag::setGenre)
    .add_property("comment", &Tag::comment, &Tag::setComment)
    .add_property("year", &Tag::year, &Tag::setYear)
    .add_property("track", &Tag::track, &Tag::setTrack)
    ;

  // Ogg //

  class_<Ogg::File, boost::noncopyable, bases<File> >
    ("OggFile", no_init)
    .def("__getitem__", &Ogg::File::packet)
    .def("__setitem__", &Ogg::File::setPacket)
    ;

  // Ogg Vorbis //

  class_<Ogg::Vorbis::File, boost::noncopyable,
    bases<Ogg::File> >("VorbisFile", init<const char *>())
    ;

  class_<Vorbis::Properties, boost::noncopyable,
    bases<AudioProperties> >
    ("VorbisProperties",
     init<Vorbis::File *, optional<AudioProperties::ReadStyle> >())
    .add_property("vorbisVersion",
		  &Vorbis::Properties::vorbisVersion)
    .add_property("bitrateMaximum",
		  &Vorbis::Properties::bitrateMaximum)
    .add_property("bitrateMinimum",
		  &Vorbis::Properties::bitrateMinimum)
    .add_property("bitrateNominal",
		  &Vorbis::Properties::bitrateNominal)
    ;

  class_<Ogg::XiphComment, boost::noncopyable, bases<Tag> >
    ("XiphComment", init<>())
    ;

  // MPEG //

  class_<MPEG::File, boost::noncopyable, bases<File> >
    ("MPEGFile", init<const char *>())
    ;

  class_<MPEG::Properties, boost::noncopyable, bases<AudioProperties> >
    ("MPEGProperties",
     init<MPEG::File *, optional<AudioProperties::ReadStyle> >())
    .add_property("layer", &MPEG::Properties::layer)
    ;
}
