/*
# ******************************************************
# Copyright 2004: David Collett
# David Collett <david.collett@dart.net.au>
#
# * This program is free software; you can redistribute it and/or
# * modify it under the terms of the GNU General Public License
# * as published by the Free Software Foundation; either version 2
# * of the License, or (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
# ******************************************************
*/
%module sw_metadata

%{
#include <FLAC/metadata.h>
%}

%inline %{
    const char *TypeString(int index) {
        return FLAC__MetadataTypeString[index];
    }
%}

// import common typedefs etc
%include "flac/format.i"

%rename (Chain) FLAC__Metadata_Chain;
typedef struct FLAC__Metadata_Chain {} FLAC__Metadata_Chain;

%extend FLAC__Metadata_Chain {
    FLAC__Metadata_Chain() {
        return FLAC__metadata_chain_new();
    }
    ~FLAC__Metadata_Chain() {
//        FLAC__metadata_chain_delete(self);
    }
    FLAC__Metadata_ChainStatus status() {
        return FLAC__metadata_chain_status(self);
    }
    FLAC__bool read(const char *filename) {
        return FLAC__metadata_chain_read(self, filename);
    }
    FLAC__bool write(FLAC__bool use_padding, FLAC__bool preserve_file_stats) {
        return FLAC__metadata_chain_write(self, use_padding, preserve_file_stats);
    }
    void merge_padding() {
        return FLAC__metadata_chain_merge_padding(self);
    }
    void sort_padding() {
        return FLAC__metadata_chain_sort_padding(self);
    }
}

%rename (Iterator) FLAC__Metadata_Iterator;
typedef struct FLAC__Metadata_Iterator {} FLAC__Metadata_Iterator;

%extend FLAC__Metadata_Iterator {
    FLAC__Metadata_Iterator() {
        return FLAC__metadata_iterator_new();
    }
    ~FLAC__Metadata_Iterator() {
//        FLAC__metadata_iterator_delete(self);
    }
    void init(FLAC__Metadata_Chain *chain) {
        FLAC__metadata_iterator_init(self, chain);
    }
    FLAC__bool next() {
        return FLAC__metadata_iterator_next(self);
    }
    FLAC__bool prev() {
        return FLAC__metadata_iterator_prev(self);
    }
    FLAC__MetadataType get_block_type() {
        return FLAC__metadata_iterator_get_block_type(self);
    }
    FLAC__StreamMetadata *get_block() {
        return FLAC__metadata_iterator_get_block(self);
    }
    FLAC__bool set_block(FLAC__StreamMetadata *block) {
        return FLAC__metadata_iterator_set_block(self, block);
    }
    FLAC__bool delete_block(FLAC__bool replace_with_padding) {
        return FLAC__metadata_iterator_delete_block(self, replace_with_padding);
    }
    FLAC__bool insert_block_before(FLAC__StreamMetadata *block) {
        return FLAC__metadata_iterator_insert_block_before(self, block);
    }
    FLAC__bool insert_block_after(FLAC__StreamMetadata *block) {
        return FLAC__metadata_iterator_insert_block_after(self, block);
    }
}

%extend FLAC__StreamMetadata {
    FLAC__StreamMetadata(FLAC__MetadataType type) {
        return FLAC__metadata_object_new(type);
    }
    ~FLAC__StreamMetadata() {
//        FLAC__metadata_object_delete(self);
    }
    FLAC__StreamMetadata *clone() {
        return FLAC__metadata_object_clone(self);
    }
    FLAC__bool is_equal(const FLAC__StreamMetadata *block) {
        return FLAC__metadata_object_is_equal(self, block);
    }
    FLAC__bool application_set_data(FLAC__byte *data, unsigned length, FLAC__bool copy) {
        return FLAC__metadata_object_application_set_data(self, data, length, copy);
    }
    FLAC__bool seektable_resize_points(unsigned new_num_points) {
        return FLAC__metadata_object_seektable_resize_points(self, new_num_points);
    }
    void seektable_set_point(unsigned point_num, FLAC__StreamMetadata_SeekPoint point) {
        FLAC__metadata_object_seektable_set_point(self, point_num, point);
    }
    FLAC__bool seektable_insert_point(unsigned point_num, FLAC__StreamMetadata_SeekPoint point) {
        return FLAC__metadata_object_seektable_insert_point(self, point_num, point);
    }
    FLAC__bool seektable_delete_point(unsigned point_num) {
        return FLAC__metadata_object_seektable_delete_point(self, point_num);
    }
    FLAC__bool seektable_is_legal() {
        return FLAC__metadata_object_seektable_is_legal(self);
    }
    FLAC__bool seektable_template_append_placeholders(unsigned num) {
        return FLAC__metadata_object_seektable_template_append_placeholders(self, num);
    }
    FLAC__bool seektable_template_append_point(FLAC__uint64 sample_number) {
        return FLAC__metadata_object_seektable_template_append_point(self, sample_number);
    }
    FLAC__bool seektable_template_append_points(FLAC__uint64 sample_numbers[], unsigned num) {
        return FLAC__metadata_object_seektable_template_append_points(self, sample_numbers, num);
    }
    FLAC__bool seektable_template_append_spaced_points(unsigned num, FLAC__uint64 total_samples) {
//      printf("total samples: %ull\n", total_samples);
        return FLAC__metadata_object_seektable_template_append_spaced_points(self, num, total_samples);
    }
    FLAC__bool seektable_template_sort(FLAC__bool compact) {
        return FLAC__metadata_object_seektable_template_sort(self, compact);
    }
    FLAC__bool vorbiscomment_set_vendor_string(FLAC__StreamMetadata_VorbisComment_Entry entry, FLAC__bool copy) {
        return FLAC__metadata_object_vorbiscomment_set_vendor_string(self, entry, copy);
    }
    FLAC__bool vorbiscomment_resize_comments(unsigned new_num_comments) {
        return FLAC__metadata_object_vorbiscomment_resize_comments(self, new_num_comments);
    }
    FLAC__bool vorbiscomment_set_comment(unsigned comment_num, FLAC__StreamMetadata_VorbisComment_Entry entry, FLAC__bool copy) {
        return FLAC__metadata_object_vorbiscomment_set_comment(self, comment_num, entry, copy);
    }
    FLAC__bool vorbiscomment_insert_comment(unsigned comment_num, FLAC__StreamMetadata_VorbisComment_Entry entry, FLAC__bool copy) {
        return FLAC__metadata_object_vorbiscomment_insert_comment(self, comment_num, entry, copy);
    }
    FLAC__bool vorbiscomment_delete_comment(unsigned comment_num) {
        return FLAC__metadata_object_vorbiscomment_delete_comment(self, comment_num);
    }
    int vorbiscomment_find_entry_from(unsigned offset, const char *field_name) {
        return FLAC__metadata_object_vorbiscomment_find_entry_from(self, offset, field_name);
    }
    int vorbiscomment_remove_entry_matching(const char *field_name) {
        return FLAC__metadata_object_vorbiscomment_remove_entry_matching(self, field_name);
    }
    int vorbiscomment_remove_entries_matching(const char *field_name) {
        return FLAC__metadata_object_vorbiscomment_remove_entries_matching(self, field_name);
    }
    FLAC__bool cuesheet_track_resize_indices(unsigned track_num, unsigned new_num_indices) {
        return FLAC__metadata_object_cuesheet_track_resize_indices(self, track_num, new_num_indices);
    }
    FLAC__bool cuesheet_track_insert_index(unsigned track_num, unsigned index_num, FLAC__StreamMetadata_CueSheet_Index index) {
        return FLAC__metadata_object_cuesheet_track_insert_index(self, track_num, index_num, index);
    }
    FLAC__bool cuesheet_track_insert_blank_index(unsigned track_num, unsigned index_num) {
        return FLAC__metadata_object_cuesheet_track_insert_blank_index(self, track_num, index_num);
    }
    FLAC__bool cuesheet_track_delete_index(unsigned track_num, unsigned index_num) {
        return FLAC__metadata_object_cuesheet_track_delete_index(self, track_num, index_num);
    }
    FLAC__bool cuesheet_resize_tracks(unsigned new_num_tracks) {
        return FLAC__metadata_object_cuesheet_resize_tracks(self, new_num_tracks);
    }
    FLAC__bool cuesheet_insert_track(unsigned track_num, FLAC__StreamMetadata_CueSheet_Track *track, FLAC__bool copy) {
        return FLAC__metadata_object_cuesheet_insert_track(self, track_num, track, copy);
    }
    FLAC__bool cuesheet_insert_blank_track(unsigned track_num) {
        return FLAC__metadata_object_cuesheet_insert_blank_track(self, track_num);
    }
    FLAC__bool cuesheet_delete_track(unsigned track_num) {
        return FLAC__metadata_object_cuesheet_delete_track(self, track_num);
    }
    FLAC__bool cuesheet_is_legal(FLAC__bool check_cd_da_subset, const char **violation) {
        return FLAC__metadata_object_cuesheet_is_legal(self, check_cd_da_subset, violation);
    }
}

// note that there is a typemap defined in format.i (where the original declaration of this class is)
// which makes the output into a python string of the correct length :)
%extend FLAC__StreamMetadata_VorbisComment_Entry {
    FLAC__bool matches(const char *field_name, unsigned field_name_length) {
        return FLAC__metadata_object_vorbiscomment_entry_matches(*self, field_name, field_name_length);
    }
    FLAC__StreamMetadata_VorbisComment_Entry *__getitem__(int index) {
        return self+index;
    }
}

%extend FLAC__StreamMetadata_CueSheet_Track {
    FLAC__StreamMetadata_CueSheet_Track() {
        return FLAC__metadata_object_cuesheet_track_new();
    }
    ~FLAC__StreamMetadata_CueSheet_Track() {
        FLAC__metadata_object_cuesheet_track_delete(self);
    }
    FLAC__StreamMetadata_CueSheet_Track *clone() {
        return FLAC__metadata_object_cuesheet_track_clone(self);
    }
    FLAC__StreamMetadata_CueSheet_Track *__getitem__(int index) {
        return self+index;
    }
}

%extend FLAC__StreamMetadata_CueSheet_Index {
    FLAC__StreamMetadata_CueSheet_Index *__getitem__(int index) {
        return self+index;
    }
}

%extend FLAC__StreamMetadata_SeekPoint {
    FLAC__StreamMetadata_SeekPoint *__getitem__(int index) {
        return self+index;
    }
}

// main metadata methods
//FLAC__Metadata_Chain *FLAC__metadata_chain_new ();
//void 	FLAC__metadata_chain_delete (FLAC__Metadata_Chain *chain);
//FLAC__Metadata_ChainStatus 	FLAC__metadata_chain_status (FLAC__Metadata_Chain *chain);
//FLAC__bool 	FLAC__metadata_chain_read (FLAC__Metadata_Chain *chain, const char *filename);
//FLAC__bool 	FLAC__metadata_chain_write (FLAC__Metadata_Chain *chain, FLAC__bool use_padding, FLAC__bool preserve_file_stats);
//void 	FLAC__metadata_chain_merge_padding (FLAC__Metadata_Chain *chain);
//void 	FLAC__metadata_chain_sort_padding (FLAC__Metadata_Chain *chain);
//FLAC__Metadata_Iterator * 	FLAC__metadata_iterator_new ();
//void 	FLAC__metadata_iterator_delete (FLAC__Metadata_Iterator *iterator);
//void 	FLAC__metadata_iterator_init (FLAC__Metadata_Iterator *iterator, FLAC__Metadata_Chain *chain);
//FLAC__bool 	FLAC__metadata_iterator_next (FLAC__Metadata_Iterator *iterator);
//FLAC__bool 	FLAC__metadata_iterator_prev (FLAC__Metadata_Iterator *iterator);
//FLAC__MetadataType 	FLAC__metadata_iterator_get_block_type (const FLAC__Metadata_Iterator *iterator);
//FLAC__StreamMetadata * 	FLAC__metadata_iterator_get_block (FLAC__Metadata_Iterator *iterator);
//FLAC__bool 	FLAC__metadata_iterator_set_block (FLAC__Metadata_Iterator *iterator, FLAC__StreamMetadata *block);
//FLAC__bool 	FLAC__metadata_iterator_delete_block (FLAC__Metadata_Iterator *iterator, FLAC__bool replace_with_padding);
//FLAC__bool 	FLAC__metadata_iterator_insert_block_before (FLAC__Metadata_Iterator *iterator, FLAC__StreamMetadata *block);
//FLAC__bool 	FLAC__metadata_iterator_insert_block_after (FLAC__Metadata_Iterator *iterator, FLAC__StreamMetadata *block);

// metadata object methods

//FLAC__StreamMetadata * 	FLAC__metadata_object_new (FLAC__MetadataType type);
//FLAC__StreamMetadata * 	FLAC__metadata_object_clone (const FLAC__StreamMetadata *object);
//void 	FLAC__metadata_object_delete (FLAC__StreamMetadata *object);
//FLAC__bool 	FLAC__metadata_object_is_equal (const FLAC__StreamMetadata *block1, const FLAC__StreamMetadata *block2);
//FLAC__bool 	FLAC__metadata_object_application_set_data (FLAC__StreamMetadata *object, FLAC__byte *data, unsigned length, FLAC__bool copy);
//FLAC__bool 	FLAC__metadata_object_seektable_resize_points (FLAC__StreamMetadata *object, unsigned new_num_points);
//void 	FLAC__metadata_object_seektable_set_point (FLAC__StreamMetadata *object, unsigned point_num, FLAC__StreamMetadata_SeekPoint point);
//FLAC__bool 	FLAC__metadata_object_seektable_insert_point (FLAC__StreamMetadata *object, unsigned point_num, FLAC__StreamMetadata_SeekPoint point);
//FLAC__bool 	FLAC__metadata_object_seektable_delete_point (FLAC__StreamMetadata *object, unsigned point_num);
//FLAC__bool 	FLAC__metadata_object_seektable_is_legal (const FLAC__StreamMetadata *object);
//FLAC__bool 	FLAC__metadata_object_seektable_template_append_placeholders (FLAC__StreamMetadata *object, unsigned num);
//FLAC__bool 	FLAC__metadata_object_seektable_template_append_point (FLAC__StreamMetadata *object, FLAC__uint64 sample_number);
//FLAC__bool 	FLAC__metadata_object_seektable_template_append_points (FLAC__StreamMetadata *object, FLAC__uint64 sample_numbers[], unsigned num);
//FLAC__bool 	FLAC__metadata_object_seektable_template_append_spaced_points (FLAC__StreamMetadata *object, unsigned num, FLAC__uint64 total_samples);
//FLAC__bool 	FLAC__metadata_object_seektable_template_sort (FLAC__StreamMetadata *object, FLAC__bool compact);
//FLAC__bool 	FLAC__metadata_object_vorbiscomment_set_vendor_string (FLAC__StreamMetadata *object, //FLAC__StreamMetadata_VorbisComment_Entry entry, FLAC__bool copy);
//FLAC__bool 	FLAC__metadata_object_vorbiscomment_resize_comments (FLAC__StreamMetadata *object, unsigned new_num_comments);
//FLAC__bool 	FLAC__metadata_object_vorbiscomment_set_comment (FLAC__StreamMetadata *object, unsigned comment_num, FLAC__StreamMetadata_VorbisComment_Entry entry, FLAC__bool copy);
//FLAC__bool 	FLAC__metadata_object_vorbiscomment_insert_comment (FLAC__StreamMetadata *object, unsigned comment_num, FLAC__StreamMetadata_VorbisComment_Entry entry, FLAC__bool copy);
//FLAC__bool 	FLAC__metadata_object_vorbiscomment_delete_comment (FLAC__StreamMetadata *object, unsigned comment_num);
//FLAC__bool 	FLAC__metadata_object_vorbiscomment_entry_matches (const FLAC__StreamMetadata_VorbisComment_Entry *entry, const char *field_name, unsigned field_name_length);
//int 	FLAC__metadata_object_vorbiscomment_find_entry_from (const FLAC__StreamMetadata *object, unsigned offset, const char *field_name);
//int 	FLAC__metadata_object_vorbiscomment_remove_entry_matching (FLAC__StreamMetadata *object, const char *field_name);
//int 	FLAC__metadata_object_vorbiscomment_remove_entries_matching (FLAC__StreamMetadata *object, const char *field_name);
//FLAC__StreamMetadata_CueSheet_Track * 	FLAC__metadata_object_cuesheet_track_new ();
//FLAC__StreamMetadata_CueSheet_Track * 	FLAC__metadata_object_cuesheet_track_clone (const FLAC__StreamMetadata_CueSheet_Track *object);
//void 	FLAC__metadata_object_cuesheet_track_delete (FLAC__StreamMetadata_CueSheet_Track *object);
//FLAC__bool 	FLAC__metadata_object_cuesheet_track_resize_indices (FLAC__StreamMetadata *object, unsigned track_num, unsigned new_num_indices);
//FLAC__bool 	FLAC__metadata_object_cuesheet_track_insert_index (FLAC__StreamMetadata *object, unsigned track_num, unsigned index_num, FLAC__StreamMetadata_CueSheet_Index index);
//FLAC__bool 	FLAC__metadata_object_cuesheet_track_insert_blank_index (FLAC__StreamMetadata *object, unsigned track_num, unsigned index_num);
//FLAC__bool 	FLAC__metadata_object_cuesheet_track_delete_index (FLAC__StreamMetadata *object, unsigned track_num, unsigned index_num);
//FLAC__bool 	FLAC__metadata_object_cuesheet_resize_tracks (FLAC__StreamMetadata *object, unsigned new_num_tracks);
//FLAC__bool 	FLAC__metadata_object_cuesheet_insert_track (FLAC__StreamMetadata *object, unsigned track_num, FLAC__StreamMetadata_CueSheet_Track *track, FLAC__bool copy);
//FLAC__bool 	FLAC__metadata_object_cuesheet_insert_blank_track (FLAC__StreamMetadata *object, unsigned track_num);
//FLAC__bool 	FLAC__metadata_object_cuesheet_delete_track (FLAC__StreamMetadata *object, unsigned track_num);
//FLAC__bool 	FLAC__metadata_object_cuesheet_is_legal (const FLAC__StreamMetadata *object, FLAC__bool check_cd_da_subset, const char **violation);
