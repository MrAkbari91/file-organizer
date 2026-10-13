"""Native windows that recolor their caption without hiding or recreating them.

CustomTkinter 5.2.2 hides Windows windows in its title-bar color hook. This small
adapter replaces that hook only; widget themes still use set_appearance_mode().
Keep the regression test when upgrading the pinned toolkit version.
"""

import ctypes
import sys
import customtkinter as ctk


class StableCaption:
    def _windows_set_titlebar_color(self, color_mode):
        if sys.platform != "win32":
            return
        try:
            user32 = ctypes.windll.user32
            user32.GetParent.argtypes = [ctypes.c_void_p]
            user32.GetParent.restype = ctypes.c_void_p
            handle = user32.GetParent(self.winfo_id())
            if not handle:
                return
            setter = ctypes.windll.dwmapi.DwmSetWindowAttribute
            setter.argtypes = [
                ctypes.c_void_p,
                ctypes.c_uint,
                ctypes.c_void_p,
                ctypes.c_uint,
            ]
            setter.restype = ctypes.c_long
            dark = ctypes.c_int(color_mode.lower() == "dark")
            # Windows 10 before 20H1 used attribute 19; unsupported systems
            # simply keep their OS caption while the application theme changes.
            for attribute in (20, 19):
                if (
                    setter(handle, attribute, ctypes.byref(dark), ctypes.sizeof(dark))
                    == 0
                ):
                    break
        except (AttributeError, OSError):
            pass


class MainWindow(StableCaption, ctk.CTk):
    pass


class AppToplevel(StableCaption, ctk.CTkToplevel):
    pass
