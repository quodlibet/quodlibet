#!/usr/bin/env python

import os, sys
import dircache
import gtk, gobject

import formats
import widgets
import qltk

def cell_data(column, cell, model, iter):
    cell.set_property('text', os.path.basename(model[iter][0]) or "/")

class DirectoryTree(gtk.TreeView):
    def __init__(self, initial = None):
        gtk.TreeView.__init__(self, gtk.TreeStore(str))
        column = gtk.TreeViewColumn("Folders")
        render = gtk.CellRendererPixbuf()
        render.set_property('stock_id', gtk.STOCK_DIRECTORY)
        column.pack_start(render, expand=False)
        render = gtk.CellRendererText()
        column.pack_start(render)
        column.set_cell_data_func(render, cell_data)
        column.set_attributes(render, text=0)
        self.append_column(column)
        niter = self.get_model().append(None, [os.environ["HOME"]])
        self.get_model().append(niter, ["dummy"])
        niter = self.get_model().append(None, ["/"])
        self.get_model().append(niter, ["dummy"])
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.connect('test-expand-row', DirectoryTree.__expanded,
                     self.get_model())

        if initial:
            path = []
            head, tail = os.path.split(initial)
            while head not in [os.path.dirname(os.environ["HOME"]), "/"]:
                if tail:
                    dirs = [d for d in
                            dircache.listdir(head) if
                            (d[0] != "." and
                             os.path.isdir(os.path.join(head,d)))]
                    try: path.insert(0, dirs.index(tail))
                    except ValueError: break
                head, tail = os.path.split(head)
                    
            if initial.startswith(os.environ["HOME"]): path.insert(0, 0)
            else: path.insert(0, 1)
            for i in range(len(path)):
                self.expand_row(tuple(path[:i+1]), False)
            self.get_selection().select_path(tuple(path))

        else: self.expand_row((0,), False)


    def __expanded(self, iter, path, model):
        if model is None: return
        while model.iter_has_child(iter):
            model.remove(model.iter_children(iter))
        dir = model[iter][0]
        for base in dircache.listdir(dir):
            path = os.path.join(dir, base)
            if (base[0] != "." and os.access(path, os.R_OK) and
                os.path.isdir(path)):
                niter = model.append(iter, [path])
                if filter(os.path.isdir,
                          [os.path.join(path, d) for d in
                           dircache.listdir(path) if d[0] != "."]):
                    model.append(niter, ["dummy"])
        if not model.iter_has_child(iter): return True

class FileSelector(gtk.VPaned):
    __gsignals__ = { 'changed': (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE, (gtk.TreeSelection,))
                     }

    def __init__(self, initial = None, filter = formats.filter):
        gtk.VPaned.__init__(self)
        self.__filter = filter

        dirlist = DirectoryTree(initial)
        filelist = gtk.TreeView(gtk.ListStore(str))
        column = gtk.TreeViewColumn("Audio files")
        render = gtk.CellRendererPixbuf()
        render.set_property('stock_id', gtk.STOCK_FILE)
        column.pack_start(render, expand=False)
        render = gtk.CellRendererText()
        column.pack_start(render)
        column.set_cell_data_func(render, cell_data)
        column.set_attributes(render, text=0)
        filelist.append_column(column)
        filelist.set_rules_hint(True)
        filelist.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

        self.__sig = filelist.get_selection().connect(
            'changed', self.__changed)

        dirlist.get_selection().connect(
            'changed', self.__fill, filelist)
        dirlist.get_selection().emit('changed')

        sw = gtk.ScrolledWindow()
        sw.add(dirlist)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        self.pack1(sw, resize = True)

        sw = gtk.ScrolledWindow()
        sw.add(filelist)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        self.pack2(sw, resize = True)

    def rescan(self):
        self.get_child1().child.get_selection().emit('changed')

    def __changed(self, selection):
        self.emit('changed', selection)

    def __fill(self, selection, filelist):
        fselect = filelist.get_selection()
        fselect.handler_block(self.__sig)
        fmodel, frows = fselect.get_selected_rows()
        selected = [fmodel[row][0] for row in frows]
        fmodel = filelist.get_model()
        fmodel.clear()
        dmodel, rows = selection.get_selected_rows()
        dirs = [dmodel[row][0] for row in rows]
        files = []
        for dir in dirs:
            for file in filter(self.__filter, dircache.listdir(dir)):
                fmodel.append([os.path.join(dir, file)])
        def select_paths(model, path, iter, selection):
            if model[path][0] in selected:
                selection.select_path(path)
        if fmodel: fmodel.foreach(select_paths, fselect)
        fselect.handler_unblock(self.__sig)
        fselect.emit('changed')

gobject.type_register(FileSelector)

class MainWindow(gtk.Window):
    def __init__(self, dir = None):
        gtk.Window.__init__(self)
        self.set_title("Ex Falso")
        self.set_border_width(12)
        self.set_default_size(700, 500)
        self.add(gtk.HPaned())
        fs = FileSelector(dir)
        self.child.pack1(fs, resize = True)
        self.tips = gtk.Tooltips()
        nb = qltk.Notebook()
        for Page in [widgets.SongProperties.EditTags,
                     widgets.SongProperties.TagByFilename,
                     widgets.SongProperties.RenameFiles,
                     widgets.SongProperties.TrackNumbers]:
            nb.append_page(Page(self, self.__files_changed))
        self.child.pack2(nb, resize = False, shrink = False)
        fs.connect('changed', self.__changed, nb)
        self.__cache = {}

        self.connect('destroy', gtk.main_quit)

    def refill(self): pass
    def update(self): pass

    def __files_changed(self, song, error = False):
        if song is None: self.child.get_child1().rescan()

    def __changed(self, selector, selection, notebook):
        model, rows = selection.get_selected_rows()
        files = []
        for row in rows:
            filename = model[row][0]
            if not os.path.exists(filename): pass
            elif filename in self.__cache: files.append(self.__cache[filename])
            else: files.append(formats.MusicFile(model[row][0]))
        try:
            while True: files.remove(None)
        except ValueError: pass
        for child in notebook.get_children(): child.update(files)
        self.__cache.clear()
        self.__cache = dict([(song["~filename"], song) for song in files])

if __name__ == "__main__":
    import gettext
    gettext.install("quodlibet", unicode = True)

    import config, const
    config.init(const.CONFIG)

    sys.argv.append(None)
    w = MainWindow(sys.argv[1])
    w.show_all()
    gtk.main()
    w.destroy()
