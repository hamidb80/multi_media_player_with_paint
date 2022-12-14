# --- imports

import cairo
from gi.repository import Gtk, Gdk
from random import random
from gettext import gettext as _
import vlc
import ctypes
import sys
import gi
from gi.repository import Gtk
from gi.repository import Gdk

# --- init

gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
Gdk.threads_init()


# Create a single vlc.Instance() to be shared by (possible) multiple players.
if 'linux' in sys.platform:
    # Inform libvlc that Xlib is not initialized for threads
    instance = vlc.Instance("--no-xlib")
else:
    instance = vlc.Instance()

# --- utils


def random_color():
    return (random(), random(), random())


class Brush(object):
    def __init__(self, width, rgba_color):
        self.width = width
        self.rgba_color = rgba_color
        self.stroke = []

    def add_point(self, point):
        self.stroke.append(point)


def get_window_pointer(window):
    """ Use the window.__gpointer__ PyCapsule to get the C void* pointer to the window
    """
    # get the c gpointer of the gdk window
    ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
    ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object]
    return ctypes.pythonapi.PyCapsule_GetPointer(window.__gpointer__, None)


# --- ui


class Canvas(object):
    def __init__(self):
        self.draw_area = self.init_draw_area()
        self.brushes = []

    def draw(self, widget, cr):
        cr.set_source_rgba(1, 1, 1, 1)
        cr.paint()

        for brush in self.brushes:
            cr.new_path()
            cr.set_source_rgba(*brush.rgba_color)
            cr.set_line_width(brush.width)
            cr.set_line_cap(1)
            cr.set_line_join(cairo.LINE_JOIN_ROUND)
            for x, y in brush.stroke:
                cr.line_to(x, y)
            cr.stroke()

    def init_draw_area(self):
        draw_area = Gtk.DrawingArea()
        draw_area.connect('draw', self.draw)
        draw_area.connect('motion-notify-event', self.mouse_move)
        draw_area.connect('button-press-event', self.mouse_press)
        draw_area.connect('button-release-event', self.mouse_release)
        draw_area.set_events(draw_area.get_events() |
                             Gdk.EventMask.BUTTON_PRESS_MASK |
                             Gdk.EventMask.POINTER_MOTION_MASK |
                             Gdk.EventMask.BUTTON_RELEASE_MASK)
        return draw_area

    def mouse_move(self, widget, event):
        if event.state & Gdk.EventMask.BUTTON_PRESS_MASK:
            curr_brush = self.brushes[-1]
            curr_brush.add_point((event.x, event.y))
            widget.queue_draw()

    def mouse_press(self, widget, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            brush = Brush(12, random_color())
            brush.add_point((event.x, event.y))
            self.brushes.append(brush)
            widget.queue_draw()

        elif event.button == Gdk.BUTTON_SECONDARY:
            self.brushes = []

    def mouse_release(self, widget, event):
        widget.queue_draw()


class VLCWidget(Gtk.DrawingArea):
    __gtype_name__ = 'VLCWidget'
    player: None

    def __init__(self, width, height):
        Gtk.DrawingArea.__init__(self)
        self.player = instance.media_player_new()

        def handle_embed(*args):
            if sys.platform == 'win32':
                # get the win32 handle
                gdkdll = ctypes.CDLL('libgdk-3-0.dll')
                handle = gdkdll.gdk_win32_window_get_handle(
                    get_window_pointer(self.get_window()))
                self.player.set_hwnd(handle)
            elif sys.platform == 'darwin':
                # get the nsview pointer. NB need to manually specify function signature
                gdkdll = ctypes.CDLL('libgdk-3.0.dll')
                get_nsview = gdkdll.gdk_quaerz_window_get_nsview
                get_nsview.restype, get_nsview.argtypes = [
                    ctypes.c_void_p],  ctypes.c_void_p
                self.player.set_nsobject(get_nsview(
                    get_window_pointer(self.get_window())))
            else:
                self.player.set_xwindow(self.get_window().get_xid())
            return True

        self.connect("realize", handle_embed)
        self.set_size_request(width, height)


class ControlledVlcWidget(Gtk.VBox):
    __gtype_name__ = 'ControlledVlcWidget'
    vlc_widget: VLCWidget
    player: None

    def __init__(self, width, height):
        super(ControlledVlcWidget, self).__init__()
        self.vlc_widget = VLCWidget(width, height)
        self.player = self.vlc_widget.player
        self.add(self.vlc_widget)
        self.pack_start(self.get_player_control_toolbar(), False, False, 0)
        self.show_all()

    def set_media(self, path):
        self.vlc_widget.player.set_media(instance.media_new(path))

    def get_player_control_toolbar(self):
        tb = Gtk.Toolbar.new()

        for text, iconname, callback in (
            (_("Play"), 'gtk-media-play', lambda b: self.player.play()),
            (_("Pause"), 'gtk-media-pause', lambda b: self.player.pause()),
            (_("Stop"), 'gtk-media-stop', lambda b: self.player.stop()),
        ):
            i = Gtk.Image.new_from_icon_name(iconname, Gtk.IconSize.MENU)
            b = Gtk.ToolButton.new(i, text)
            b.set_tooltip_text(text)
            b.connect("clicked", callback)
            tb.insert(b, -1)

        return tb


# --- go -------------------------------------

def main(filenames):
    # Build main window
    window = Gtk.Window()
    wrapper = Gtk.VBox()
    videos = Gtk.HBox()
    canvas = Canvas()

    canvas.draw_area.set_size_request(400, 400)

    wrapper.add(videos)
    wrapper.pack_start(canvas.draw_area, True, True, 0)
    window.add(wrapper)

    # Create VLC widgets
    for fname in filenames:
        v = ControlledVlcWidget(400, 400)
        v.player.set_media(instance.media_new(fname))
        videos.add(v)

    window.set_title("multi video player + paint")
    window.show_all()
    window.connect("destroy", Gtk.main_quit)
    Gtk.main()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        quit('You must provide at least 1 movie filename')

    else:
        main(sys.argv[1:])

    instance.release()
