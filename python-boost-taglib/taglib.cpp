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

#include <taglib/textidentificationframe.h>
#include <taglib/id3v2framefactory.h>

using namespace boost::python;
using namespace TagLib;

struct StringToUnicode {
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

struct StringListToUnicodeList {
  static PyObject *convert(StringList const &sl) {
    PyObject *pl = PyList_New((int)sl.size());
    for (unsigned int i = 0; i < sl.size(); i++)
      PyList_SetItem(pl, i, StringToUnicode::convert(sl[i]));
    return pl;
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
    new (storage) String(value, String::UTF8);
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

struct StringListFromStrList {
  StringListFromStrList() {
    converter::registry::push_back(&convertible, &construct,
				   type_id<StringList>());
  }

  static void *convertible(PyObject* o) {
    if (PyList_Check(o)) {
      int size = PyList_Size(o);
      for (int i = 0; i < size; i++) {
	PyObject *s = PyList_GetItem(o, i);
	if (!(PyString_Check(s) || PyUnicode_Check(s)))
	  return 0;
      }
      return o;
    } else return 0;
  }

  static void construct(PyObject* o,
			converter::rvalue_from_python_stage1_data *data) {
    void* storage = ((converter::rvalue_from_python_storage<StringList> *)
		     data)->storage.bytes;
    int size = PyList_Size(o);
    new (storage) StringList;
    data->convertible = storage;
    StringList *l = (StringList *)(data->convertible);
    for (int i = 0; i < size; i++) {
      PyObject *s = PyList_GetItem(o, i);
      if (PyUnicode_Check(s))
	s = PyUnicode_AsUTF8String(s);
      const char *value = PyString_AsString(s);
      if (value == 0) throw_error_already_set();
      l->append(String(value, String::UTF8));
    }
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

  enum_<String::Type>("Encoding")
    .value("LATIN1", String::Latin1)
    .value("UTF16", String::UTF16)
    .value("UTF16BE", String::UTF16BE)
    .value("UTF8", String::UTF8)
    ;

  // Utility classes <-> Python types //
  to_python_converter<ByteVector, ByteVectorToStr>();
  to_python_converter<String, StringToUnicode>();
  to_python_converter<StringList, StringListToUnicodeList>();
  ByteVectorFromStr();
  StringFromStr();
  StringListFromStrList();

  class_<FileRef>("FileRef", init<const char *>())
    .def("save", &FileRef::save)
    .def("audioProperties", &FileRef::audioProperties,
	 return_internal_reference<1>())
    .def("tag", &FileRef::tag,
	 return_internal_reference<1>())
    .def("file", &FileRef::file,
	 return_internal_reference<1>())
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
    .def("tag", &File::tag, return_internal_reference<1>())
    .def("audioProperties", &File::audioProperties,
	 return_internal_reference<1>())
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

  // ID3v2 //

  class_<ID3v2::Frame, boost::noncopyable>("_ID3v2Frame", no_init)
    .add_property("frameID", &ID3v2::Frame::frameID)
    .add_property("size", &ID3v2::Frame::size)
    .add_property("text", &ID3v2::Frame::toString, &ID3v2::Frame::setText)
    .add_property("data", &ID3v2::Frame::render, &ID3v2::Frame::setData)
    .def("__unicode__", &ID3v2::Frame::toString)
    ;
 
  void (ID3v2::TextIdentificationFrame::*setTextList)(const StringList &) =
    &ID3v2::TextIdentificationFrame::setText;

  class_<ID3v2::TextIdentificationFrame, boost::noncopyable,
    bases<ID3v2::Frame> >
    ("ID3v2TextFrame", init<ByteVector, String::Type>())
    .add_property("encoding", &ID3v2::TextIdentificationFrame::textEncoding,
    &ID3v2::TextIdentificationFrame::setTextEncoding)
    .add_property("fields", &ID3v2::TextIdentificationFrame::fieldList,
		  setTextList)

    ;
}
