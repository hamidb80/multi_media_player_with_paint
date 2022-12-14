# https://github.com/oaubert/python-vlc/blob/master/examples/gtkvlc.py
# https://stackoverflow.com/questions/56045346/python-vlc-will-not-embed-gtk-widget-into-window-but-open-a-new-window-instead

# https://stackoverflow.com/questions/38143037/cairo-gtk-draw-a-line-with-transparency-like-a-highlighter-pen

# --- imports

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

# --- def


def get_window_pointer(window):
    """ Use the window.__gpointer__ PyCapsule to get the C void* pointer to the window
    """
    # get the c gpointer of the gdk window
    ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
    ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object]
    return ctypes.pythonapi.PyCapsule_GetPointer(window.__gpointer__, None)


class VLCWidget(Gtk.DrawingArea):
    __gtype_name__ = 'VLCWidget'
    player: None

    def __init__(self, *p):
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
        self.set_size_request(320, 200)


class ControlledVlcWidget(Gtk.VBox):
    __gtype_name__ = 'ControlledVlcWidget'
    vlc_widget: VLCWidget
    player: None

    def __init__(self, *p):
        super(ControlledVlcWidget, self).__init__()
        self.vlc_widget = VLCWidget(*p)
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


class Canvas(Gtk.DrawingArea):
    ...


def main(filenames):
    # Build main window
    window = Gtk.Window()
    mainbox = Gtk.VBox()
    videos = Gtk.HBox()

    mainbox.add(videos)
    window.add(mainbox)

    # Create VLC widgets
    for fname in filenames:
        v = ControlledVlcWidget()
        v.player.set_media(instance.media_new(fname))
        videos.add(v)

    window.show_all()
    window.connect("destroy", Gtk.main_quit)
    Gtk.main()

# --- go -------------------------------------


if __name__ == '__main__':
    if not sys.argv[1:]:
        quit('You must provide at least 1 movie filename')

    else:
        main(sys.argv[1:])

    instance.release()
