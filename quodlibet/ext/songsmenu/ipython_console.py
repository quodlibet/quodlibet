# Copyright 2021 Nick Boultbee
#
# Based on Accerciser by Eitan Isaacson,  Copyright (c) 2007 IBM Corporation (BSD)
# See https://gitlab.gnome.org/GNOME/accerciser/
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import re
import sys
from functools import reduce
from io import StringIO
from typing import Tuple, Dict, Any, Optional, IO, Callable, Iterable, List

from gi.repository import Gtk, Pango, Gdk, GLib

from quodlibet.qltk import Icons, add_css
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from traitlets.config.loader import Config
from quodlibet import _, ngettext, app
from quodlibet.util.collection import Collection
from quodlibet.util.songwrapper import SongWrapper

try:
    from IPython.core import interactiveshell
    from IPython.terminal.embed import InteractiveShellEmbed
    from IPython.utils import io as ipio
    from IPython.utils.coloransi import color_templates
except ImportError:
    from quodlibet import plugins
    raise plugins.MissingModulePluginException("IPython")


class IPythonConsole(SongsMenuPlugin):
    PLUGIN_ID = 'IPython Console'
    PLUGIN_NAME = _('IPython Console')
    PLUGIN_DESC = _('Interactive Python console. Opens a new window.')
    PLUGIN_ICON = Icons.UTILITIES_TERMINAL

    def plugin_songs(self, songs):
        desc = ngettext("%d song", "%d songs", len(songs)) % len(songs)
        win = Gtk.Window()
        win.set_default_size(700, 500)
        win.connect('delete-event', lambda x, y: Gtk.main_quit())
        swin = Gtk.ScrolledWindow()
        swin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        swin.set_shadow_type(Gtk.ShadowType.NONE)
        swin.add(IPythonView(songs))
        win.add(swin)
        win.set_icon_name(self.PLUGIN_ICON)
        win.set_title(_("{plugin_name} for {songs} ({app})").format(
            plugin_name=self.PLUGIN_NAME, songs=desc, app=app.name))
        win.show_all()


class IterableIPShell:
    """
    Create an IPython instance.
    Does not start a blocking event loop, instead allow single iterations.
    This allows embedding in GTK+ without blockage.

    @ivar IP: IPython instance.
    @type IP: IPython.iplib.InteractiveShell
    @ivar iter_more: Indicates if the line executed was a complete command,
    or we should wait for more.
    @type iter_more: integer
    @ivar history_level: The place in history where we currently are
    when pressing up/down.
    @type history_level: integer
    @ivar complete_sep: Seperation delimeters for completion function.
    @type complete_sep: _sre.SRE_Pattern
    """

    def __init__(self, user_ns: Optional[Dict] = None, cin: IO = None, cout: IO = None,
                 cerr: IO = None, input_func: Optional[Callable[[str], str]] = None):
        """
        :param user_ns: User namespace.
        :param cin: Console standard input.
        :param cout: Console standard output.
        :param cerr: Console standard error.
        :param input_func: Replacement for builtin raw_input()
        """
        if input_func:
            interactiveshell.raw_input_original = input_func
        if cin:
            ipio.stdin = cin
        if cout:
            ipio.stdout = cout
        if cerr:
            ipio.stderr = cerr

        # This is to get rid of the blockage that occurs during
        # IPython.Shell.InteractiveShell.user_setup()

        ipio.raw_input = lambda x: None

        os.environ['TERM'] = 'dumb'
        excepthook = sys.excepthook

        cfg = Config()
        cfg.InteractiveShell.colors = "Linux"
        cfg.Completer.use_jedi = False

        # InteractiveShell inherits from SingletonConfigurable, so use instance()
        self.IP = InteractiveShellEmbed.instance(config=cfg, user_ns=user_ns)

        self.IP.system = lambda cmd: self.shell(self.IP.var_expand(cmd),
                                                header='IPython system call: ')

        self.IP.raw_input = input_func
        sys.excepthook = excepthook
        self.iter_more = 0
        self.history_level = 0
        self.complete_sep = re.compile(r'[\s\{\}\[\]\(\)]')
        self.update_namespace({'exit': lambda: None})
        self.update_namespace({'quit': lambda: None})

        self.no_input_splitter = True
        self.lines: List[str] = []
        self.indent_spaces = ''

    def execute(self) -> None:
        """
        Executes the current line provided by the shell object.
        """
        self.history_level = 0

        # this is needed because some functions in IPython use 'print' to print
        # output (like 'who')
        orig_stdout = sys.stdout
        sys.stdout = ipio.stdout

        orig_stdin = sys.stdin
        sys.stdin = ipio.stdin
        self.prompt = self.generate_prompt(bool(self.iter_more))

        self.IP.hooks.pre_prompt_hook()
        if self.iter_more:
            try:
                self.prompt = self.generate_prompt(True)
            except:
                self.IP.showtraceback()
            if self.IP.autoindent:
                self.IP.rl_do_indent = True

        try:
            line = self.IP.raw_input(self.prompt)
        except KeyboardInterrupt:
            self.IP.write('\nKeyboardInterrupt\n')
            if self.no_input_splitter:
                self.lines = []
            else:
                self.IP.input_splitter.reset()
        except:
            self.IP.showtraceback()
        else:
            if self.no_input_splitter:
                self.lines.append(line)
                (status, self.indent_spaces) = self.IP.check_complete(self.text)
                self.iter_more = status == 'incomplete'
            else:
                self.IP.input_splitter.push(line)
                self.iter_more = self.IP.input_splitter.push_accepts_more()
            self.prompt = self.generate_prompt(bool(self.iter_more))
            if not self.iter_more:
                if self.no_input_splitter:
                    source_raw = self.text
                    self.lines = []
                else:
                    source_raw = self.IP.input_splitter.raw_reset()
                self.IP.run_cell(source_raw, store_history=True)
                self.IP.rl_do_indent = False
            else:
                # TODO: Auto-indent
                #
                self.IP.rl_do_indent = True
                pass

        sys.stdout = orig_stdout
        sys.stdin = orig_stdin

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    def generate_prompt(self, is_continuation: bool) -> str:
        """
        Generate prompt depending on is_continuation value

        :param is_continuation: Whether it's a continuation line

        :returns: The prompt string representation
        """

        # TODO: update to IPython 5.x and later
        prompt = f"In [{self.IP.execution_count}]: "
        return prompt

    def history_back(self) -> str:
        """
        Provides one history command back.

        :returns: The command string.
        """
        self.history_level -= 1
        if not self._get_history():
            self.history_level += 1
        return self._get_history()

    def history_forward(self) -> str:
        """
        Provides one history command forward.

        :returns: The command string.
        """
        if self.history_level < 0:
            self.history_level += 1
        return self._get_history()

    def _get_history(self) -> str:
        """
        Gets the command string of the current history level.

        :returns: Historic command string.
        """
        try:
            rv = self.IP.user_ns['In'][self.history_level].strip('\n')
        except IndexError:
            rv = ''
        return rv

    def update_namespace(self, ns_dict: Dict[str, Any]):
        """
        Add the current dictionary to the shell namespace.

        :param ns_dict: A dictionary of symbol-values.
        """
        self.IP.user_ns.update(ns_dict)

    def complete(self, line: str) -> Tuple[str, str]:
        """
        Returns an auto completed line and/or possibilities for completion.

        :param line: Given line so far.

        :returns: Line completed as for as possible, and possible further completions.
        """
        split_line = self.complete_sep.split(line)
        if split_line[-1]:
            possibilities = self.IP.complete(split_line[-1])
        else:
            completed = line
            possibilities = ['', []]
        if possibilities:
            def _common_prefix(str1: str, str2: str) -> str:
                """
                Reduction function. returns common prefix of two given strings.

                :param str1: First string.
                :param str2: Second string

                :returns: Common prefix to both strings.
                """
                for i in range(len(str1)):
                    if not str2.startswith(str1[:i + 1]):
                        return str1[:i]
                return str1

            if possibilities[1]:
                common_prefix = reduce(_common_prefix, possibilities[1]) or split_line[
                    -1]
                completed = line[:-len(split_line[-1])] + common_prefix
            else:
                completed = line
        else:
            completed = line
        return completed, possibilities[1]

    def shell(self, cmd: str, verbose: int = 0, debug: int = 0, header: str = ''):
        """
        Replacement method to allow shell commands without them blocking.

        :param cmd: Shell command to execute.
        :param verbose: Verbosity
        :param debug: Debug level
        :param header: Header to be printed before output
        """
        if verbose or debug:
            print(header + cmd)
        # flush stdout so we don't mangle python's buffering
        if not debug:
            output = os.popen(cmd)
            print(output.read())
            output.close()


class ConsoleView(Gtk.TextView):
    """
    Specialized text view for console-like workflow.
    """

    def __init__(self):
        super().__init__()
        add_css(self, "* { padding: 6px; } ")
        self.set_wrap_mode(Gtk.WrapMode.CHAR)
        self.modify_font(Pango.font_description_from_string('Monospace'))
        self.set_cursor_visible(True)
        self.text_buffer = self.get_buffer()
        self.mark = self.text_buffer.create_mark('scroll_mark',
                                                 self.text_buffer.get_end_iter(),
                                                 False)
        for name, code in color_templates:
            self.text_buffer.create_tag(code, foreground=name, weight=500)
        self.text_buffer.create_tag("0")
        self.text_buffer.create_tag("notouch", editable=False)
        self.color_pat = re.compile(r"\x01?\x1b\[(.*?)m\x02?")
        self.line_start = self.text_buffer.create_mark("line_start",
                                                       self.text_buffer.get_end_iter(),
                                                       True)
        self.connect('key-press-event', self.on_key_press)

    def write(self, text, editable=False):
        GLib.idle_add(self._write, text, editable)

    def _write(self, text: str, editable: bool = False):
        """
        Write given text to buffer.

        :param text: Text to append.
        :param editable: If true, added text is editable.
        """
        segments = self.color_pat.split(text)
        segment = segments.pop(0)
        end_iter = self.text_buffer.get_end_iter()
        start_mark = self.text_buffer.create_mark(None, end_iter, True)
        self.text_buffer.insert(end_iter, segment)

        if segments:
            ansi_tags = self.color_pat.findall(text)
            for tag in ansi_tags:
                i = segments.index(tag)
                self.text_buffer.insert_with_tags_by_name(
                    end_iter,
                    segments[i + 1], tag)
                segments.pop(i)
        if not editable:
            start_iter = self.text_buffer.get_iter_at_mark(start_mark)
            self.text_buffer.apply_tag_by_name("notouch", start_iter, end_iter)
        self.text_buffer.delete_mark(start_mark)
        self.scroll_mark_onscreen(self.mark)

    def show_prompt(self, prompt):
        GLib.idle_add(self._show_prompt, prompt)

    def _show_prompt(self, prompt: str) -> None:
        """
        Prints prompt at start of line.

        :param prompt: Prompt to print.
        """
        self._write(prompt)
        self.text_buffer.move_mark(self.line_start,
                                   self.text_buffer.get_end_iter())

    def change_line(self, text: Optional[str]) -> None:
        if text:
            GLib.idle_add(self._change_line, text)

    def _change_line(self, text: str):
        """
        Replace currently entered command line with given text.

        :param text: Text to use as replacement.
        """
        end_iter = self.text_buffer.get_iter_at_mark(self.line_start)
        end_iter.forward_to_line_end()
        start_iter = self.text_buffer.get_iter_at_mark(self.line_start)
        self.text_buffer.delete(start_iter, end_iter)
        self._write(text, True)

    def get_current_line(self) -> str:
        """
        Get text in current command line.

        :returns: Text of current command line.
        """
        rv = self.text_buffer.get_slice(
            self.text_buffer.get_iter_at_mark(self.line_start),
            self.text_buffer.get_end_iter(), False)
        return rv

    def show_returned(self, text):
        GLib.idle_add(self._show_returned, text)

    def _show_returned(self, text: str) -> None:
        """
        Show returned text from last command and print new prompt.

        :param text: Text to show.
        """
        iter = self.text_buffer.get_iter_at_mark(self.line_start)
        iter.forward_to_line_end()
        self.text_buffer.apply_tag_by_name(
            'notouch',
            self.text_buffer.get_iter_at_mark(self.line_start),
            iter)
        self._write(f"\n{text}\n" if text is not None else "\n")
        self._show_prompt(self.prompt)
        self.text_buffer.move_mark(self.line_start, self.text_buffer.get_end_iter())
        self.text_buffer.place_cursor(self.text_buffer.get_end_iter())

        if self.IP.rl_do_indent:
            if self.no_input_splitter:
                indentation = self.indent_spaces
            else:
                indentation = self.IP.input_splitter.indent_spaces * ' '
            self.text_buffer.insert_at_cursor(indentation)

    def on_key_press(self, widget: Gtk.Widget, event: Gdk.Event) -> bool:
        """
        Key press callback used for correcting behavior for console-like
        interfaces.
        For example 'home' should go to prompt, not to beginning of line.

        :param widget: Widget that key press occurred in.
        :param event: Event object

        :returns: Return True if event should not trickle.
        """
        insert_mark = self.text_buffer.get_insert()
        insert_iter = self.text_buffer.get_iter_at_mark(insert_mark)
        selection_mark = self.text_buffer.get_selection_bound()
        selection_iter = self.text_buffer.get_iter_at_mark(selection_mark)
        start_iter = self.text_buffer.get_iter_at_mark(self.line_start)
        state = event.state
        MT = Gdk.ModifierType
        if event.keyval == Gdk.KEY_Home:
            if state & MT.CONTROL_MASK or state & MT.MOD1_MASK:
                pass
            elif state & MT.SHIFT_MASK:
                self.text_buffer.move_mark(insert_mark, start_iter)
                return True
            else:
                self.text_buffer.place_cursor(start_iter)
                return True
        elif event.keyval == Gdk.KEY_Left:
            insert_iter.backward_cursor_position()
            if not insert_iter.editable(True):
                return True
        elif not event.string:
            pass
        elif (start_iter.compare(insert_iter) <= 0
              and start_iter.compare(selection_iter) <= 0):
            pass
        elif (start_iter.compare(insert_iter) > 0
              and start_iter.compare(selection_iter) > 0):
            self.text_buffer.place_cursor(start_iter)
        elif insert_iter.compare(selection_iter) < 0:
            self.text_buffer.move_mark(insert_mark, start_iter)
        elif insert_iter.compare(selection_iter) > 0:
            self.text_buffer.move_mark(selection_mark, start_iter)

        return bool(self.on_key_press_extend(event))

    def on_key_press_extend(self, event: Gdk.Event) -> bool:
        """
        For some reason we can't extend onKeyPress directly (bug #500900).
        """
        pass


def namespace_for(song_wrappers):
    files = [song('~filename') for song in song_wrappers]
    song_dicts = [song._song for song in song_wrappers]
    collection = Collection()
    collection.songs = song_dicts
    return {
        'songs': song_wrappers,
        'files': files,
        'sdict': song_dicts,
        'col': collection,
        'app': app}


class IPythonView(ConsoleView, IterableIPShell):
    """
    Sub-class of both modified IPython shell and L{ConsoleView} this makes
    a GTK+ IPython console.
    """

    def __init__(self, songs: Iterable[SongWrapper]):
        """
        Initialize. Redirect I/O to console.
        """
        ConsoleView.__init__(self)
        self.cout = StringIO()

        IterableIPShell.__init__(self, cout=self.cout, cerr=self.cout,
                                 input_func=self.raw_input,
                                 user_ns=namespace_for(songs))
        self.interrupt = False
        self.execute()
        self.prompt = self.generate_prompt(False)
        self.cout.truncate(0)
        self.show_prompt(self.prompt)

    def raw_input(self, prompt: str = "") -> str:
        """
        Custom raw_input() replacement. Get's current line from console buffer.

        :param prompt: Prompt to print. Here for compatibility as replacement.

        :returns: The current command line text.
        """
        if self.interrupt:
            self.interrupt = False
            raise KeyboardInterrupt
        return self.get_current_line()

    def on_key_press_extend(self, event: Gdk.Event) -> bool:
        """
        Key press callback with plenty of shell goodness, like history,
        autocompletions, etc.

        :param event: Event object.

        :returns: True if event should not trickle.
        """
        if event.state & Gdk.ModifierType.CONTROL_MASK and event.keyval == 99:
            self.interrupt = True
            self._process_line()
            return True
        elif event.keyval == Gdk.KEY_Return:
            self._process_line()
            return True
        elif event.keyval == Gdk.KEY_Up:
            self.change_line(self.history_back())
            return True
        elif event.keyval == Gdk.KEY_Down:
            self.change_line(self.history_forward())
            return True
        elif event.keyval == Gdk.KEY_Tab:
            if not self.get_current_line().strip():
                return False
            completed, possibilities = self.complete(self.get_current_line())
            line = None
            if len(possibilities) > 1:
                line = self.get_current_line()
                self.write('\n')
                for symbol in possibilities:
                    self.write(symbol + '\n')
                self.show_prompt(self.prompt)
            self.change_line(completed or line)
            return True
        return False

    def _process_line(self) -> None:
        """
        Process current command line.
        """
        self.history_pos = 0
        self.execute()
        rv = self.cout.getvalue()
        if rv:
            rv = rv.strip('\n')
        self.show_returned(rv)
        self.cout.truncate(0)
        self.cout.seek(0)


if __name__ == "__main__":
    window = Gtk.Window()
    window.set_default_size(700, 500)
    window.connect('delete-event', lambda x, y: Gtk.main_quit())
    swin = Gtk.ScrolledWindow()
    swin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    swin.add(IPythonView([]))
    window.add(swin)
    window.show_all()
    Gtk.main()
