/* eggstatusicon.h:
 *
 * Copyright (C) 2003 Sun Microsystems, Inc.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 *
 * Authors:
 *      Mark McLoughlin <mark@skynet.ie>
 */

#ifndef __EGG_STATUS_ICON_H__
#define __EGG_STATUS_ICON_H__

#include "eggtrayicon.h"
#include <gtk/gtkimage.h>

G_BEGIN_DECLS

#define EGG_TYPE_STATUS_ICON         (egg_status_icon_get_type ())
#define EGG_STATUS_ICON(o)           (G_TYPE_CHECK_INSTANCE_CAST ((o), EGG_TYPE_STATUS_ICON, EggStatusIcon))
#define EGG_STATUS_ICON_CLASS(k)     (G_TYPE_CHECK_CLASS_CAST ((k), EGG_TYPE_STATUS_ICON, EggStatusIconClass))
#define EGG_IS_STATUS_ICON(o)        (G_TYPE_CHECK_INSTANCE_TYPE ((o), EGG_TYPE_STATUS_ICON))
#define EGG_IS_STATUS_ICON_CLASS(k)  (G_TYPE_CHECK_CLASS_TYPE ((k), EGG_TYPE_STATUS_ICON))
#define EGG_STATUS_ICON_GET_CLASS(o) (G_TYPE_INSTANCE_GET_CLASS ((o), EGG_TYPE_STATUS_ICON, EggStatusIconClass))
	
typedef struct _EggStatusIcon	     EggStatusIcon;
typedef struct _EggStatusIconClass   EggStatusIconClass;
typedef struct _EggStatusIconPrivate EggStatusIconPrivate;

struct _EggStatusIcon
{
  GObject               parent_instance;

  EggStatusIconPrivate *priv;
};

struct _EggStatusIconClass
{
  GObjectClass parent_class;

  void     (* activate)     (EggStatusIcon *status_icon);
  void     (* popup_menu)   (EggStatusIcon *status_icon,
			     guint          buttton,
			     guint32        activate_time);
  gboolean (* size_changed) (EggStatusIcon *status_icon,
			     gint           size);
};

GType                 egg_status_icon_get_type           (void);

EggStatusIcon        *egg_status_icon_new                (void);
EggStatusIcon        *egg_status_icon_new_from_pixbuf    (GdkPixbuf          *pixbuf);
EggStatusIcon        *egg_status_icon_new_from_file      (const gchar        *filename);
EggStatusIcon        *egg_status_icon_new_from_stock     (const gchar        *stock_id);
EggStatusIcon        *egg_status_icon_new_from_animation (GdkPixbufAnimation *animation);

void                  egg_status_icon_set_from_pixbuf    (EggStatusIcon      *status_icon,
							  GdkPixbuf          *pixbuf);
void                  egg_status_icon_set_from_file      (EggStatusIcon      *status_icon,
							  const gchar        *filename);
void                  egg_status_icon_set_from_stock     (EggStatusIcon      *status_icon,
							  const gchar        *stock_id);
void                  egg_status_icon_set_from_animation (EggStatusIcon      *status_icon,
							  GdkPixbufAnimation *animation);

GtkImageType          egg_status_icon_get_image_type     (EggStatusIcon      *status_icon);

GdkPixbuf            *egg_status_icon_get_pixbuf         (EggStatusIcon      *status_icon);
G_CONST_RETURN gchar *egg_status_icon_get_stock          (EggStatusIcon      *status_icon);
GdkPixbufAnimation   *egg_status_icon_get_animation      (EggStatusIcon      *status_icon);

gint                  egg_status_icon_get_size           (EggStatusIcon      *status_icon);

void                  egg_status_icon_set_tooltip        (EggStatusIcon      *status_icon,
							  const gchar        *tooltip_text,
							  const gchar        *tooltip_private);

void                  egg_status_icon_set_balloon_text   (EggStatusIcon      *status_icon,
							  const gchar        *text);
G_CONST_RETURN gchar *egg_status_icon_get_balloon_text   (EggStatusIcon      *status_icon);

void                  egg_status_icon_set_is_blinking    (EggStatusIcon      *status_icon,
							  gboolean            enable_blinking);
gboolean              egg_status_icon_get_is_blinking    (EggStatusIcon      *status_icon);

G_END_DECLS

#endif /* __EGG_STATUS_ICON_H__ */
