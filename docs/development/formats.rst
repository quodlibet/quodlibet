Tag Formats & Spec Deviations
=============================

Deviations
----------

Quod Libet deviates from several of the standards it claims to support. 
We'll document them here, but most of the time we won't change them; we had 
a good reason for violating them in the first place.

General Deviations
------------------

Since we translate to and from many formats, sometimes we're forced to 
accept the lowest common denominator among tag formats. Don't worry; if 
it's too low we'll figure out some way around it.

    * Dates are restricted to YYYY or YYYY-MM-DD formats. Blame ID3.
    * = and ~ are not allowed in tag names, and tag names must also be
      pure ASCII.
    * Tag names are always case-insensitive.
    * Newlines are not allowed in tag values. If you use a newline in a
      tag value, it will instead be treated as two values for the tag.

ID3
---

UTF-8 and ID3 Tags
^^^^^^^^^^^^^^^^^^

If Quod Libet finds data in an MP3 claiming to be "latin 1", it won't trust 
it. It'll try UTF-8 and some other encodings before it gives up and 
actually considers it Latin 1. On the other hand, when it writes tags, it 
saves purely ASCII values as UTF-8 and any non-ASCII values as UTF-16. This 
means it won't try to "guess" when it reloads them, and other programs 
shouldn't either.

Using a format like Ogg Vorbis, FLAC, or Musepack, the tag encoding is 
known and Unicode is perfectly supported.

Genre and TCON
^^^^^^^^^^^^^^

The ID3 standard is ambiguous in its specification for the TCON frame. If 
you try to use a numeric genre in the form of 02 or (23) (for example) it 
will get translated into a text genre. This means there's no way to have a 
genre actually start with (xx) for MP3s.

QuodLibet::TXXX Frames
^^^^^^^^^^^^^^^^^^^^^^

ID3 doesn't let you have frames named whatever you want like Ogg Vorbis and 
APEv2 do. However, it does let you create "TXXX" frames which are text data 
with an associated "description". Quod Libet uses these frames with a 
*`QuodLibet``::<tagname>* description to store tags that don't have ID3 
counterparts. For example, labelid is stored as *`QuodLibet`::labelid*.

RVA2 / ReplayGain
^^^^^^^^^^^^^^^^^

Quod Libet implements ReplayGain using MP3's RVA2 frame. Unfortunately 
there is no standard on how to read RVA2 frames to support RG properly. If 
the description string is "album" the gain is treated as the 
album/audiophile value. Any other value is read as the track/radio value, 
but an actual description of "track" will preempt other values.

I've passed this information along to the GStreamer guys and their RVA2 
support should match this, once it's completed.

foobar2000-style TXXX:replaygain_* tags are also supported, but 
migrated to the proper RVA2 format on save.

COMM Frame Language codes
^^^^^^^^^^^^^^^^^^^^^^^^^

Language codes in COMM frames with empty descriptors are replaced by 
\x00\x00\x00 on save. These tend to contain garbage rather than valid 
language codes anyway, and empty descriptors are usually a sign of comments 
migrated ID3v1 or other formats that do not support language markers.

Legacy Stuff
^^^^^^^^^^^^

Multiframe Hack:

    Since versions of ID3 prior to 2.4 did not support multiple values in a 
    single text frame, we stored multiple text frames of the same type with 
    one value for each if you tried to save more than one value per frame. 
    This was strictly a violation of the ID3 spec, but we never encountered 
    an ID3 reader that had trouble reading the tags saved this way (and 
    still haven't).

    Now that we use Mutagen, we store multiple values in the standard 
    ID3v2.4 format. Old tags are migrated when you edit them.


QuodLibet:: COMM Frames:

    Quod Libet used to use COMM frames instead of TXXX frames for its 
    extended tag names. It will still load old COMM tags, but clears then 
    when you save the file again.

APEv2
-----

Naming Conflicts
^^^^^^^^^^^^^^^^

Since we turn APEv2's ``Subtitle`` tag into version, you can't edit a tag 
named ``subtitle`` in MPC files. Similar problems exist for ``Track``, 
``Catalog``, ``Year``, and ``Record location`` tags.


VorbisComment
-------------

This is a list of Ogg Vorbis tags Quod Libet uses that require special 
handling. They are presented here in the hopes that other applications will 
adopt them.

**rating**

The rating tag has a subkey of an email address, and is formatted as e.g. 
``rating:quodlibet@sacredchao.net``. The email is used as a unique 
identifier to allow multiple users to share the same files (it need not 
actually be an email address, but having it as such ensures that it's 
unique across users). It represents how much a user likes a song. Its value 
is a string representation of a floating point number between 0.0 and 1.0, 
inclusive. This format is chosen so the application may decide what 
precision it offers to the user, and how this information is presented. If 
no value is present, the rating should be assumed to be 0.5.
Starting from version 4.8, the de-facto standard for representing and 
interpreting ratings in Vorbis comments uses a 0–100 integer scale, 
ensuring consistent reading and writing of rating values across applications.

Example: ``rating:quodlibet@sacredchao.net=0.67``
         ``rating=67``

**playcount**

The playcount tag has a subkey of an email address, and is formatted as 
e.g. ``playcount:quodlibet@sacredchao.net``. It stores how many times the 
user has played the song all the way through, as a numeric string. If no 
value is present, it should be assumed to be 0.

Example: ``playcount:quodlibet@sacredchao.net=3``

**website**

The website tag stores an absolute IRI (Internationalized Resource 
Identifier), as per RFC 3987. The intent is that it hold an IRI suitable 
for opening in a standard web browser (e.g. http, https, or ftp scheme). As 
it is an IRI, and not a URI, it should be stored in unescaped form. If an 
application needs a URI, it should follow the procedure in RFC 3987 section 
3.1 to convert a valid IRI to a valid URI. As per the Vorbis comment 
specification, the tag must be a UTF-8 representation of the Unicode string.

This tag may occur any number of times in a file.

Performer Roles
^^^^^^^^^^^^^^^

This is similar to the ID3v2 IPLS (involved person list) frame. Quod Libet
displays these tags by putting the role after the name, parenthesized (e.g.
``Béla Fleck (banjo)``), but in other supporting programs the role can be
associated with the name in any understandable way, or simply ignored and
treated like an ordinary performer tag.
