/* eggstatusicon.c:
 *
 * Copyright (C) 2003 Sun Microsystems, Inc.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Library General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Library General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 *
 * Authors:
 *	Mark McLoughlin <mark@skynet.ie>
 */

#include <string.h>

#include "eggstatusicon.h"

#include <gtk/gtk.h>
#include "eggmarshalers.h"

enum{
  PROP_0,
  PROP_PIXBUF,
  PROP_FILE,
  PROP_STOCK,
  PROP_PIXBUF_ANIMATION,
  PROP_STORAGE_TYPE,
  PROP_SIZE,
  PROP_BLINKING
};

enum {
  ACTIVATE_SIGNAL,
  POPUP_MENU_SIGNAL,
  SIZE_CHANGED_SIGNAL,
  LAST_SIGNAL
};

struct _EggStatusIconPrivate
{
  GtkWidget    *tray_icon;
  GtkWidget    *image;
  gint          size;

  GtkTooltips  *tooltips;

  GtkImageType  image_type;

  union
    {
      GdkPixbuf          *pixbuf;
      const gchar        *stock_id;
      GdkPixbufAnimation *animimation;
    } image_data;

  GdkPixbuf    *blank_icon;
  guint         blinking_timeout;

  guint         blinking : 1;
  guint         blink_off : 1;
  guint         button_down : 1;
};

static void egg_status_icon_class_init (EggStatusIconClass *klass);
static void egg_status_icon_init       (EggStatusIcon      *status_icon);

static void egg_status_icon_finalize     (GObject      *object);
static void egg_status_icon_set_property (GObject      *object,
					  guint         prop_id,
					  const GValue *value,
					  GParamSpec   *pspec);
static void egg_status_icon_get_property (GObject      *object,
					  guint         prop_id,
					  GValue       *value,
					  GParamSpec   *pspec);

static void     egg_status_icon_size_allocate    (EggStatusIcon  *status_icon,
						  GtkAllocation  *allocation);
static gboolean egg_status_icon_button_press     (EggStatusIcon  *status_icon,
						  GdkEventButton *event);
static gboolean egg_status_icon_button_release   (EggStatusIcon  *status_icon,
						  GdkEventButton *event);
static void     egg_status_icon_disable_blinking (EggStatusIcon  *status_icon);
static void     egg_status_icon_reset_image_data (EggStatusIcon  *status_icon);
					   

static GObjectClass *parent_class = NULL;
static guint status_icon_signals [LAST_SIGNAL] = { 0 };

GType
egg_status_icon_get_type (void)
{
  static GType status_icon_type = 0;
  
  if (!status_icon_type)
    {
      static const GTypeInfo status_icon_info =
      {
	sizeof (EggStatusIconClass),
	NULL,		/* base_init */
	NULL,		/* base_finalize */
	(GClassInitFunc) egg_status_icon_class_init,
	NULL,		/* class_finalize */
	NULL,		/* class_data */
	sizeof (EggStatusIcon),
	0,		/* n_preallocs */
	(GInstanceInitFunc) egg_status_icon_init,
      };
      
      status_icon_type = g_type_register_static (G_TYPE_OBJECT,
						 "EggStatusIcon",
						 &status_icon_info, 0);
    }
  
  return status_icon_type;
}

static void
egg_status_icon_class_init (EggStatusIconClass *klass)
{
  GObjectClass *gobject_class = (GObjectClass *) klass;

  parent_class = g_type_class_peek_parent (klass);

  gobject_class->finalize     = egg_status_icon_finalize;
  gobject_class->set_property = egg_status_icon_set_property;
  gobject_class->get_property = egg_status_icon_get_property;

  g_object_class_install_property (gobject_class,
				   PROP_PIXBUF,
				   g_param_spec_object ("pixbuf",
							"Pixbuf",
							"A GdkPixbuf to display",
							GDK_TYPE_PIXBUF,
							G_PARAM_READWRITE));

  g_object_class_install_property (gobject_class,
				   PROP_FILE,
				   g_param_spec_string ("file",
							"Filename",
							"Filename to load and display",
							NULL,
							G_PARAM_WRITABLE));

  g_object_class_install_property (gobject_class,
				   PROP_STOCK,
				   g_param_spec_string ("stock",
							"Stock ID",
							"Stock ID for a stock image to display",
							NULL,
							G_PARAM_READWRITE));
  
  g_object_class_install_property (gobject_class,
				   PROP_PIXBUF_ANIMATION,
				   g_param_spec_object ("pixbuf-animation",
							"Animation",
							"GdkPixbufAnimation to display",
							GDK_TYPE_PIXBUF_ANIMATION,
							G_PARAM_READWRITE));
  
  g_object_class_install_property (gobject_class,
				   PROP_STORAGE_TYPE,
				   g_param_spec_enum ("image-type",
						      "Image type",
						      "The representation being used for image data",
						      GTK_TYPE_IMAGE_TYPE,
						      GTK_IMAGE_EMPTY,
						      G_PARAM_READABLE));

  g_object_class_install_property (gobject_class,
				   PROP_SIZE,
				   g_param_spec_int ("size",
						     "Size",
						     "The size of the icon",
						     G_MININT,
						     G_MAXINT,
						     0,
						     G_PARAM_READABLE));

  g_object_class_install_property (gobject_class,
				   PROP_BLINKING,
				   g_param_spec_boolean ("blinking",
							 "Blinking",
							 "Whether or not the status icon is blinking",
							 FALSE,
							 G_PARAM_READWRITE));

  status_icon_signals [ACTIVATE_SIGNAL] =
    g_signal_new ("activate",
		  G_TYPE_FROM_CLASS (gobject_class),
		  G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
		  G_STRUCT_OFFSET (EggStatusIconClass, activate),
		  NULL,
		  NULL,
		  g_cclosure_marshal_VOID__VOID,
		  G_TYPE_NONE,
		  0);

  status_icon_signals [POPUP_MENU_SIGNAL] =
    g_signal_new ("popup-menu",
		  G_TYPE_FROM_CLASS (gobject_class),
		  G_SIGNAL_RUN_FIRST | G_SIGNAL_ACTION,
		  G_STRUCT_OFFSET (EggStatusIconClass, popup_menu),
		  NULL,
		  NULL,
		  _egg_marshal_VOID__UINT_UINT,
		  G_TYPE_NONE,
		  2,
		  G_TYPE_UINT,
		  G_TYPE_UINT);

  status_icon_signals [SIZE_CHANGED_SIGNAL] =
    g_signal_new ("size-changed",
		  G_TYPE_FROM_CLASS (gobject_class),
		  G_SIGNAL_RUN_FIRST,
		  G_STRUCT_OFFSET (EggStatusIconClass, size_changed),
		  NULL,
		  NULL,
		  g_cclosure_marshal_VOID__INT,
		  G_TYPE_NONE,
		  1,
		  G_TYPE_INT);
}

static void
egg_status_icon_init (EggStatusIcon *status_icon)
{
  status_icon->priv = g_new0 (EggStatusIconPrivate, 1);

  status_icon->priv->image_type = GTK_IMAGE_EMPTY;
  status_icon->priv->size       = G_MAXINT;

  status_icon->priv->tray_icon = GTK_WIDGET (egg_tray_icon_new (NULL));

  gtk_widget_add_events (GTK_WIDGET (status_icon->priv->tray_icon),
			 GDK_BUTTON_PRESS_MASK | GDK_BUTTON_RELEASE_MASK);

  g_signal_connect_swapped (status_icon->priv->tray_icon, "button-press-event",
			    G_CALLBACK (egg_status_icon_button_press), status_icon);
  g_signal_connect_swapped (status_icon->priv->tray_icon, "button-release-event",
			    G_CALLBACK (egg_status_icon_button_release), status_icon);

  status_icon->priv->image = gtk_image_new ();
  gtk_container_add (GTK_CONTAINER (status_icon->priv->tray_icon),
		     status_icon->priv->image);

  g_signal_connect_swapped (status_icon->priv->image, "size-allocate",
			    G_CALLBACK (egg_status_icon_size_allocate), status_icon);

  gtk_widget_show (status_icon->priv->image);
  gtk_widget_show (status_icon->priv->tray_icon);

  status_icon->priv->tooltips = gtk_tooltips_new ();
  g_object_ref (status_icon->priv->tooltips);
  gtk_object_sink (GTK_OBJECT (status_icon->priv->tooltips));
}

static void
egg_status_icon_finalize (GObject *object)
{
  EggStatusIcon *status_icon = EGG_STATUS_ICON (object);

  egg_status_icon_disable_blinking (status_icon);

  egg_status_icon_reset_image_data (status_icon);

  if (status_icon->priv->blank_icon)
    g_object_unref (status_icon->priv->blank_icon);
  status_icon->priv->blank_icon = NULL;

  if (status_icon->priv->tooltips)
    g_object_unref (status_icon->priv->tooltips);
  status_icon->priv->tooltips = NULL;

  gtk_widget_destroy (status_icon->priv->tray_icon);

  g_free (status_icon->priv);

  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
egg_status_icon_set_property (GObject      *object,
			      guint         prop_id,
			      const GValue *value,
			      GParamSpec   *pspec)
{
  EggStatusIcon *status_icon = EGG_STATUS_ICON (object);

  switch (prop_id)
    {
    case PROP_PIXBUF:
      egg_status_icon_set_from_pixbuf (status_icon, g_value_get_object (value));
      break;
    case PROP_FILE:
      egg_status_icon_set_from_file (status_icon, g_value_get_string (value));
      break;
    case PROP_STOCK:
      egg_status_icon_set_from_stock (status_icon, g_value_get_string (value));
      break;
    case PROP_PIXBUF_ANIMATION:
      egg_status_icon_set_from_animation (status_icon, g_value_get_object (value));
      break;
    case PROP_BLINKING:
      egg_status_icon_set_is_blinking (status_icon, g_value_get_boolean (value));
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
    }
}

static void
egg_status_icon_get_property (GObject    *object,
			      guint       prop_id,
			      GValue     *value,
			      GParamSpec *pspec)
{
  EggStatusIcon *status_icon = EGG_STATUS_ICON (object);

  switch (prop_id)
    {
    case PROP_PIXBUF:
      g_value_set_object (value, egg_status_icon_get_pixbuf (status_icon));
      break;
    case PROP_STOCK:
      g_value_set_string (value, egg_status_icon_get_stock (status_icon));
      break;
    case PROP_PIXBUF_ANIMATION:
      g_value_set_object (value, egg_status_icon_get_animation (status_icon));
      break;
    case PROP_STORAGE_TYPE:
      g_value_set_enum (value, egg_status_icon_get_image_type (status_icon));
      break;
    case PROP_SIZE:
      g_value_set_int (value, status_icon->priv->size);
      break;
    case PROP_BLINKING:
      g_value_set_boolean (value, status_icon->priv->blinking);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
    }
}

EggStatusIcon *
egg_status_icon_new (void)
{
  return g_object_new (EGG_TYPE_STATUS_ICON, NULL);
}

EggStatusIcon *
egg_status_icon_new_from_pixbuf (GdkPixbuf *pixbuf)
{
  return g_object_new (EGG_TYPE_STATUS_ICON,
		       "pixbuf", pixbuf,
		       NULL);
}

EggStatusIcon *
egg_status_icon_new_from_file (const gchar *filename)
{
  return g_object_new (EGG_TYPE_STATUS_ICON,
		       "file", filename,
		       NULL);
}

EggStatusIcon *
egg_status_icon_new_from_stock (const gchar *stock_id)
{
  return g_object_new (EGG_TYPE_STATUS_ICON,
		       "stock", stock_id,
		       NULL);
}

EggStatusIcon *
egg_status_icon_new_from_animation (GdkPixbufAnimation *animation)
{
  return g_object_new (EGG_TYPE_STATUS_ICON,
		       "pixbuf_animation", animation,
		       NULL);
}

static void
emit_activate_signal (EggStatusIcon *status_icon)
{
  g_signal_emit (status_icon,
		 status_icon_signals [ACTIVATE_SIGNAL], 0);
}

static void
emit_popup_menu_signal (EggStatusIcon *status_icon,
			guint          button,
			guint32        activate_time)
{
  g_signal_emit (status_icon,
		 status_icon_signals [POPUP_MENU_SIGNAL], 0,
		 button,
		 activate_time);
}

static gboolean
emit_size_changed_signal (EggStatusIcon *status_icon,
			  gint           size)
{
  gboolean handled = FALSE;
  
  g_signal_emit (status_icon,
		 status_icon_signals [SIZE_CHANGED_SIGNAL], 0,
		 size,
		 &handled);

  return handled;
}

static GdkPixbuf *
egg_status_icon_blank_icon (EggStatusIcon *status_icon)
{
  if (status_icon->priv->blank_icon)
    {
      gint width, height;

      width  = gdk_pixbuf_get_width (status_icon->priv->blank_icon);
      height = gdk_pixbuf_get_width (status_icon->priv->blank_icon);

      if (width  == status_icon->priv->size &&
          height == status_icon->priv->size)
	{
	  return status_icon->priv->blank_icon;
	}
      else
	{
	  g_object_unref (status_icon->priv->blank_icon);
	  status_icon->priv->blank_icon = NULL;
	}
    }

  status_icon->priv->blank_icon = gdk_pixbuf_new (GDK_COLORSPACE_RGB, TRUE, 8,
						  status_icon->priv->size,
						  status_icon->priv->size);
  if (status_icon->priv->blank_icon)
    gdk_pixbuf_fill (status_icon->priv->blank_icon, 0);

  return status_icon->priv->blank_icon;
}

static void
egg_status_icon_update_image (EggStatusIcon *status_icon)
{
  if (status_icon->priv->blink_off)
    {
      gtk_image_set_from_pixbuf (GTK_IMAGE (status_icon->priv->image),
				 egg_status_icon_blank_icon (status_icon));
      return;
    }

  switch (status_icon->priv->image_type)
    {
    case GTK_IMAGE_PIXBUF:
      {
	GdkPixbuf *pixbuf;

	pixbuf = status_icon->priv->image_data.pixbuf;

	if (pixbuf)
	  {
	    GdkPixbuf *scaled;
	    gint size;
	    gint width;
	    gint height;

	    size = status_icon->priv->size;

	    width  = gdk_pixbuf_get_width  (pixbuf);
	    height = gdk_pixbuf_get_height (pixbuf);

	    if (width > size || height > size)
	      {
		scaled = gdk_pixbuf_scale_simple (pixbuf,
						  MIN (size, width),
						  MIN (size, height),
						  GDK_INTERP_BILINEAR);
	      }
	    else
	      {
		scaled = g_object_ref (pixbuf);
	      }

	    gtk_image_set_from_pixbuf (GTK_IMAGE (status_icon->priv->image), scaled);

	    g_object_unref (scaled);
	  }
	else
	  {
	    gtk_image_set_from_pixbuf (GTK_IMAGE (status_icon->priv->image), NULL);
	  }
      }
      break;
    case GTK_IMAGE_STOCK:
    case GTK_IMAGE_ANIMATION:
    case GTK_IMAGE_EMPTY:
      gtk_image_set_from_pixbuf (GTK_IMAGE (status_icon->priv->image), NULL);
      break;
    default:
      g_assert_not_reached ();
      break;
    }
}

static void
egg_status_icon_size_allocate (EggStatusIcon *status_icon,
			       GtkAllocation *allocation)
{
  GtkOrientation orientation;
  gint size;

  orientation = egg_tray_icon_get_orientation (EGG_TRAY_ICON (status_icon->priv->tray_icon));

  if (orientation == GTK_ORIENTATION_HORIZONTAL)
    size = allocation->height;
  else
    size = allocation->width;

  if (status_icon->priv->size != size)
    {
      status_icon->priv->size = size;

      g_object_notify (G_OBJECT (status_icon), "size");

      if (!emit_size_changed_signal (status_icon, size))
	{
	  egg_status_icon_update_image (status_icon);
	}
    }
}

static gboolean
egg_status_icon_button_press (EggStatusIcon  *status_icon,
			      GdkEventButton *event)
{
  if (event->button == 1 && !status_icon->priv->button_down)
    {
      status_icon->priv->button_down = TRUE;
      return TRUE;
    }

  return FALSE;
}

static gboolean
egg_status_icon_button_release (EggStatusIcon  *status_icon,
				GdkEventButton *event)
{
  if (event->button == 1 && status_icon->priv->button_down)
    {
      status_icon->priv->button_down = FALSE;
      emit_activate_signal (status_icon);
      return TRUE;
    }
  /* added by Joe Wreschnig for QL -- popup-menu on RMB */
  else if (event->button == 3) 
    emit_popup_menu_signal(status_icon, (guint)3, (guint32)0);
                        
  return FALSE;
}

static void
egg_status_icon_reset_image_data (EggStatusIcon *status_icon)
{
  switch (status_icon->priv->image_type)
  {
    case GTK_IMAGE_PIXBUF:
      status_icon->priv->image_type = GTK_IMAGE_EMPTY;

      if (status_icon->priv->image_data.pixbuf)
	g_object_unref (status_icon->priv->image_data.pixbuf);
      status_icon->priv->image_data.pixbuf = NULL;

      g_object_notify (G_OBJECT (status_icon), "image-type");
      g_object_notify (G_OBJECT (status_icon), "pixbuf");
      break;
    case GTK_IMAGE_STOCK:
    case GTK_IMAGE_ANIMATION:
    case GTK_IMAGE_EMPTY:
      break;
    default:
      g_assert_not_reached ();
      break;
  }
}

void
egg_status_icon_set_from_pixbuf (EggStatusIcon *status_icon,
				 GdkPixbuf     *pixbuf)
{
  g_return_if_fail (EGG_IS_STATUS_ICON (status_icon));
  g_return_if_fail (pixbuf == NULL || GDK_IS_PIXBUF (pixbuf));

  if (pixbuf)
    g_object_ref (pixbuf);

  g_object_freeze_notify (G_OBJECT (status_icon));

  egg_status_icon_reset_image_data (status_icon);

  status_icon->priv->image_type = GTK_IMAGE_PIXBUF;
  status_icon->priv->image_data.pixbuf = pixbuf;

  g_object_notify (G_OBJECT (status_icon), "image-type");
  g_object_notify (G_OBJECT (status_icon), "pixbuf");

  g_object_thaw_notify (G_OBJECT (status_icon));

  egg_status_icon_update_image (status_icon);
}

void
egg_status_icon_set_from_file (EggStatusIcon *status_icon,
			       const gchar   *filename)
{
  g_return_if_fail (EGG_IS_STATUS_ICON (status_icon));
}

void
egg_status_icon_set_from_stock (EggStatusIcon *status_icon,
				const gchar   *stock_id)
{
  g_return_if_fail (EGG_IS_STATUS_ICON (status_icon));
}

void
egg_status_icon_set_from_animation (EggStatusIcon      *status_icon,
				    GdkPixbufAnimation *animation)
{
  g_return_if_fail (EGG_IS_STATUS_ICON (status_icon));
  g_return_if_fail (animation == NULL || GDK_IS_PIXBUF_ANIMATION (animation));
}
                                                                                                             
GtkImageType
egg_status_icon_get_image_type (EggStatusIcon *status_icon)
{
  g_return_val_if_fail (EGG_IS_STATUS_ICON (status_icon), GTK_IMAGE_EMPTY);

  return status_icon->priv->image_type;
}
                                                                                                             
GdkPixbuf *
egg_status_icon_get_pixbuf (EggStatusIcon *status_icon)
{
  g_return_val_if_fail (EGG_IS_STATUS_ICON (status_icon), NULL);
  g_return_val_if_fail (status_icon->priv->image_type == GTK_IMAGE_PIXBUF ||
			status_icon->priv->image_type == GTK_IMAGE_EMPTY, NULL);
                                                                                                             
  if (status_icon->priv->image_type == GTK_IMAGE_EMPTY)
    status_icon->priv->image_data.pixbuf = NULL;
                                                                                                             
  return status_icon->priv->image_data.pixbuf;
}

G_CONST_RETURN gchar *
egg_status_icon_get_stock (EggStatusIcon *status_icon)
{
  g_return_val_if_fail (EGG_IS_STATUS_ICON (status_icon), NULL);

  return NULL;
}

GdkPixbufAnimation *
egg_status_icon_get_animation (EggStatusIcon *status_icon)
{
  g_return_val_if_fail (EGG_IS_STATUS_ICON (status_icon), NULL);

  return NULL;
}
                                                                                                             
gint
egg_status_icon_get_size (EggStatusIcon *status_icon)
{
  g_return_val_if_fail (EGG_IS_STATUS_ICON (status_icon), -1);

  return status_icon->priv->size;
}
                                                                                                             
void
egg_status_icon_set_tooltip (EggStatusIcon *status_icon,
			     const gchar   *tooltip_text,
			     const gchar   *tooltip_private)
{
  g_return_if_fail (EGG_IS_STATUS_ICON (status_icon));

  gtk_tooltips_set_tip (status_icon->priv->tooltips,
			status_icon->priv->tray_icon,
			tooltip_text,
			tooltip_private);
}

void
egg_status_icon_set_balloon_text (EggStatusIcon *status_icon,
				  const gchar   *text)
{
  g_return_if_fail (EGG_IS_STATUS_ICON (status_icon));
}

G_CONST_RETURN gchar *
egg_status_icon_get_balloon_text (EggStatusIcon *status_icon)
{
  g_return_val_if_fail (EGG_IS_STATUS_ICON (status_icon), NULL);

  return NULL;
}

static gboolean
egg_status_icon_blinker (EggStatusIcon *status_icon)
{
  status_icon->priv->blink_off = !status_icon->priv->blink_off;

  egg_status_icon_update_image (status_icon);

  return TRUE;
}

static void
egg_status_icon_enable_blinking (EggStatusIcon *status_icon)
{
  if (!status_icon->priv->blinking_timeout)
    {
      egg_status_icon_blinker (status_icon);

      status_icon->priv->blinking_timeout =
	g_timeout_add (500, (GSourceFunc) egg_status_icon_blinker, status_icon);
    }
}

static void
egg_status_icon_disable_blinking (EggStatusIcon *status_icon)
{
  if (status_icon->priv->blinking_timeout)
    {
      g_source_remove (status_icon->priv->blinking_timeout);
      status_icon->priv->blinking_timeout = 0;
      status_icon->priv->blink_off = FALSE;

      egg_status_icon_update_image (status_icon);
    }
}

void
egg_status_icon_set_is_blinking (EggStatusIcon *status_icon,
				 gboolean       is_blinking)
{
  g_return_if_fail (EGG_IS_STATUS_ICON (status_icon));

  is_blinking = is_blinking != FALSE;

  if (status_icon->priv->blinking != is_blinking)
    {
      status_icon->priv->blinking = is_blinking;

      if (is_blinking)
	egg_status_icon_enable_blinking (status_icon);
      else
	egg_status_icon_disable_blinking (status_icon);

      g_object_notify (G_OBJECT (status_icon), "blinking");
    }
}

gboolean
egg_status_icon_get_is_blinking (EggStatusIcon *status_icon)
{
  g_return_val_if_fail (EGG_IS_STATUS_ICON (status_icon), FALSE);

  return status_icon->priv->blinking;
}
