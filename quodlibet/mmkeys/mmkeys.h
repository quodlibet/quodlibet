/*
 * Copyright (C) 2004 Lee Willis <lee@leewillis.co.uk>
 *    Borrowed heavily from code by Jan Arne Petersen <jpetersen@uni-bonn.de>
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public
 * License along with this program; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

#include <X11/Xlib.h>
#include <X11/XF86keysym.h>
#include <gdk/gdk.h>
#include <gdk/gdkx.h>
#include <stdio.h>
#include <gtk/gtktogglebutton.h>

#ifndef __MM_KEYS_H
#define __MM_KEYS_H

#define TYPE_MMKEYS            (mmkeys_get_type ())
#define MMKEYS(obj)            (G_TYPE_CHECK_INSTANCE_CAST ((obj), TYPE_MMKEYS, MmKeys))
#define MMKEYS_CLASS(klass)    (G_TYPE_CHECK_CLASS_CAST ((klass), TYPE_MMKEYS, MmKeysClass))
#define IS_MMKEYS(obj)         (G_TYPE_CHECK_INSTANCE_TYPE ((obj), TYPE_MMKEYS))
#define IS_MMKEYS_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), TYPE_MMKEYS))
#define MMKEYS_GET_CLASS(obj)  (G_TYPE_INSTANCE_GET_CLASS ((obj), TYPE_MMKEYS, MmKeysClass))

typedef struct _MmKeys      MmKeys;
typedef struct _MmKeysClass MmKeysClass;

struct _MmKeys
{
	GObject parent;
};

struct _MmKeysClass
{
	GObjectClass parent_class;
};

GType   mmkeys_get_type (void);

MmKeys *mmkeys_new      (void);

#endif /* __MM_KEYS_H */
