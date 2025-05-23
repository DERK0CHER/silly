#!/usr/bin/env python3
# coding: utf-8

# Copyright (C) 2017-present Robert Griesel
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import os
# Force X11 backend to avoid Wayland protocol errors during development
#os.environ.setdefault('GDK_BACKEND', 'x11')
import sys
import gi
import gettext
import argparse

# Projekt-Root ermitteln und ins Modul-Suchpath aufnehmen
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# GTK/Adwaita Versionen
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gio, Adw

# Setzer-Module imports
from setzer.workspace.workspace import Workspace
import setzer.workspace.workspace_viewgtk as view
import setzer.keyboard_shortcuts.shortcuts as shortcuts
from setzer.app.service_locator import ServiceLocator
from setzer.dialogs.dialog_locator import DialogLocator
from setzer.app.color_manager import ColorManager
from setzer.app.font_manager import FontManager
from setzer.popovers.popover_manager import PopoverManager
from setzer.app.latex_db import LaTeXDB
from setzer.settings.document_settings import DocumentSettings
from setzer.helpers.timer import timer

class MainApplicationController(Adw.Application):

    def __init__(self):
        super().__init__(application_id='org.cvfosammmm.Setzer', flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.is_active = False

    def do_open(self, files, number_of_files, hint=""):
        if not self.is_active:
            self.activate()
            self.is_active = True

    def do_activate(self):
        if not self.is_active:
            self.activate()
            self.is_active = True

    def activate(self):
        # Pfade für Übersetzungen und Assets
        localedir = os.path.join(PROJECT_ROOT, 'po')
        resources_path = os.path.join(PROJECT_ROOT, 'data', 'resources')
        app_icons_path = os.path.join(PROJECT_ROOT, 'data')

        # gettext initialisieren
        gettext.install('setzer', names=('ngettext',), localedir=localedir)

        # Einstellungen und Theme
        self.settings = ServiceLocator.get_settings()
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)

        # ServiceLocator konfigurieren
        ServiceLocator.set_setzer_version('@setzer_version@')
        ServiceLocator.set_resources_path(resources_path)
        ServiceLocator.set_app_icons_path(app_icons_path)

        # Hauptfenster, Model und Dialoge initialisieren
        self.main_window = view.MainWindow(self)
        icon_theme = Gtk.IconTheme.get_for_display(self.main_window.get_display())
        icon_theme.add_search_path(os.path.join(resources_path, 'icons'))
        icon_theme.add_search_path(app_icons_path)
        for folder in ['arrows', 'greek_letters', 'misc_math', 'misc_text', 'operators', 'relations']:
            icon_theme.add_search_path(os.path.join(resources_path, 'symbols', folder))

        ServiceLocator.set_main_window(self.main_window)
        ColorManager.init(self.main_window)
        FontManager.init(self.main_window)

        self.workspace = Workspace()
        PopoverManager.init(self.main_window, self.workspace)
        LaTeXDB.init(resources_path)
        self.main_window.create_widgets()
        ServiceLocator.set_workspace(self.workspace)
        DialogLocator.init_dialogs(self.main_window, self.workspace)

        # Fensterzustand wiederherstellen und anzeigen
        if self.settings.get_value('window_state', 'is_maximized'):
            self.main_window.maximize()
        else:
            self.main_window.unmaximize()
        width = self.settings.get_value('window_state', 'width')
        height = self.settings.get_value('window_state', 'height')
        self.main_window.set_default_size(width, height)
        self.main_window.present()
        # Signale verbinden
        self.main_window.connect('close-request', self.on_window_close)

        # Controller und Shortcuts
        self.workspace.init_workspace_controller()
        self.shortcuts = shortcuts.Shortcuts()
    # Signal-Handler implementieren
    def on_window_close(self, window, parameter=None):
        self.save_quit()
        return True

    def on_quit_action(self, action, parameter=None):
        self.save_quit()

    # Bestehende Methoden: save_quit, save_quit_callback, save_callback, save_state_and_quit
    # ...

if __name__ == '__main__':
    main_controller = MainApplicationController()
    exit_status = main_controller.run(sys.argv)
    sys.exit(exit_status)

