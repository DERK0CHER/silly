#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import gi
import threading
import signal

# Setup paths
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Create translation function
def _(text):
    return text

# Make it globally available
import builtins
builtins._ = _

# Setup GTK
gi.require_version('Gtk', '4.0')
gi.require_version('GtkSource', '5')
gi.require_version('Adw', '1')
from gi.repository import Gtk, GLib, Gio, Adw, GtkSource, Gdk, Pango

# Import application modules
from app.service_locator import ServiceLocator

# Print process ID for debugging
print(f"Running as PID: {os.getpid()}")

# Set application resources path
resources_path = os.path.join(project_dir, 'resources')
if not os.path.exists(resources_path):
    os.makedirs(resources_path, exist_ok=True)
    os.makedirs(os.path.join(resources_path, 'icons'), exist_ok=True)
    os.makedirs(os.path.join(resources_path, 'language-specs'), exist_ok=True)
    os.makedirs(os.path.join(resources_path, 'themes'), exist_ok=True)

app_icons_path = os.path.join(resources_path, 'icons')
ServiceLocator.set_resources_path(resources_path)
ServiceLocator.set_app_icons_path(app_icons_path)
ServiceLocator.set_setzer_version('2.0.0')

# Helper functions for UI
def create_button(icon_name, tooltip_text, clicked_callback=None):
    button = Gtk.Button()
    button.set_tooltip_text(tooltip_text)
    
    icon = Gtk.Image.new_from_icon_name(icon_name)
    button.set_child(icon)
    
    if clicked_callback:
        button.connect("clicked", clicked_callback)
    
    return button

def create_menu_button(icon_name, tooltip_text, menu_model):
    button = Gtk.MenuButton()
    button.set_tooltip_text(tooltip_text)
    
    icon = Gtk.Image.new_from_icon_name(icon_name)
    button.set_child(icon)
    button.set_menu_model(menu_model)
    
    return button

# Fixed width label helper for UI components
class FixedWidthLabel(Gtk.Box):
    def __init__(self, width):
        Gtk.Box.__init__(self)
        self.label = Gtk.Label()
        self.append(self.label)
        self.set_size_request(width, -1)
        
    def set_text(self, text):
        self.label.set_text(text)
        
    def get_text(self):
        return self.label.get_text()

# Scrolling widget for preview area
class ScrollingWidget(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        
        # Create scrolled window
        self.view = Gtk.ScrolledWindow()
        self.view.set_vexpand(True)
        
        # Create viewport for content
        self.viewport = Gtk.Viewport()
        self.view.set_child(self.viewport)
        
        # Create drawing area for content
        self.content = Gtk.DrawingArea()
        self.content.set_draw_func(self.on_draw)
        self.content.set_size_request(500, 700)
        self.viewport.set_child(self.content)
        
    def on_draw(self, drawing_area, cr, width, height, user_data=None):
        # This function would render the PDF document
        # For now, we just show a placeholder
        cr.set_source_rgb(1, 1, 1)  # White background
        cr.paint()
        
        cr.set_source_rgb(0.5, 0.5, 0.5)  # Gray text
        cr.select_font_face("Sans", 0, 0)
        cr.set_font_size(20)
        
        # Draw text
        text = "PDF Preview Placeholder"
        x_bearing, y_bearing, text_width, text_height, x_advance, y_advance = cr.text_extents(text)
        
        cr.move_to((width - text_width) / 2, (height - text_height) / 2)
        cr.show_text(text)
        
        text = "Build your document to see the actual PDF"
        x_bearing, y_bearing, text_width, text_height, x_advance, y_advance = cr.text_extents(text)
        
        cr.move_to((width - text_width) / 2, (height - text_height) / 2 + 30)
        cr.show_text(text)

# Blank slate for empty preview
class BlankSlateView(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        
        image = Gtk.Image.new_from_icon_name("document-print-preview-symbolic")
        image.set_pixel_size(64)
        image.set_margin_bottom(12)
        
        label = Gtk.Label()
        label.set_markup("<b>No Preview Available</b>")
        label.set_margin_bottom(12)
        
        subtitle = Gtk.Label()
        subtitle.set_markup("Build your document to generate a preview")
        subtitle.set_margin_bottom(24)
        
        button = Gtk.Button.new_with_label("Build Document")
        button.set_halign(Gtk.Align.CENTER)
        button.connect("clicked", self.on_build_clicked)
        
        self.append(image)
        self.append(label)
        self.append(subtitle)
        self.append(button)
    
    def on_build_clicked(self, button):
        print("Build document clicked from blank slate")

# Build log view
class BuildLogView(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header.set_margin_top(6)
        header.set_margin_bottom(6)
        header.set_margin_start(6)
        header.set_margin_end(6)
        
        label = Gtk.Label(label="Build Log")
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        
        clear_button = create_button("edit-clear-symbolic", "Clear Build Log", self.on_clear_clicked)
        
        header.append(label)
        header.append(clear_button)
        
        # Log content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(False)
        self.text_view.set_monospace(True)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.text_view.set_margin_start(6)
        self.text_view.set_margin_end(6)
        
        self.buffer = self.text_view.get_buffer()
        scrolled.set_child(self.text_view)
        
        # Add to main container
        self.append(header)
        self.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self.append(scrolled)
        
        # Add sample content
        self.append_to_log("LaTeX build will be shown here.\n")
    
    def on_clear_clicked(self, button):
        self.buffer.set_text("")
    
    def append_to_log(self, text):
        end_iter = self.buffer.get_end_iter()
        self.buffer.insert(end_iter, text)
        
        # Scroll to end
        mark = self.buffer.create_mark(None, end_iter, False)
        self.text_view.scroll_to_mark(mark, 0.0, False, 0.0, 0.0)
        self.buffer.delete_mark(mark)

# Enhanced window for Setzer UI
class SetzerWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        Adw.ApplicationWindow.__init__(self, application=app)
        self.set_default_size(1100, 700)
        self.set_title("Setzer - LaTeX Editor")
        
        # Setup global CSS for the application
        self.setup_css()
        
        # Create all UI components
        self.create_widgets()
        
        # Apply settings
        try:
            self.apply_settings()
        except Exception as e:
            print(f"Error applying settings: {e}")
            import traceback
            traceback.print_exc()
        
    def setup_css(self):
        # Create CSS provider
        css_provider = Gtk.CssProvider()
        
        # CSS data with modern styling
        css = '''
        .sidebar {
            background-color: #f5f5f5;
            border-right: 1px solid #ddd;
        }
        
        .editor {
            background-color: #ffffff;
        }
        
        .toolbar {
            background-color: #f8f9fa;
            border-bottom: 1px solid #ddd;
        }
        
        .statusbar {
            background-color: #f8f9fa;
            border-top: 1px solid #ddd;
            font-size: 0.9em;
        }
        
        .structure-item {
            padding: 4px 8px;
        }
        
        .structure-item.level-0 {
            font-weight: bold;
        }
        
        .structure-item.level-1 {
            margin-left: 16px;
        }
        
        .structure-item.level-2 {
            margin-left: 32px;
        }
        
        textview {
            font-family: monospace;
            font-size: 11pt;
        }
        
        .preview {
            background-color: #f0f0f0;
        }
        
        .target-label {
            background-color: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            margin: 8px;
        }
        
        .preview-content {
            background-color: #ffffff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
            margin: 16px;
        }
        
        .highlight {
            background-color: #e2eefe;
        }
        
        button.active {
            background-color: #e9ecef;
            color: #495057;
        }
        
        .zoom-level-button {
            min-width: 66px;
        }
        
        .scbar {
            padding: 2px;
        }
        
        .paging-widget {
            min-width: 100px;
        }
        '''
        
        # Load CSS data
        css_provider.load_from_data(css.encode())
        
        # Add provider for the display
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def create_widgets(self):
        # Main layout container
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Create header bar with toolbar
        self.header = self.create_header_bar()
        
        # Main content paned (content + preview)
        self.main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        
        # Content area (sidebar + editor)
        self.content_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        
        # Create sidebar
        self.sidebar = self.create_sidebar()
        self.sidebar.set_size_request(250, -1)
        
        # Create editor area
        self.editor_box = self.create_editor_area()
        
        # Create editor and buildlog paned
        self.editor_buildlog_paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.editor_buildlog_paned.set_start_child(self.editor_box)
        
        # Create build log
        self.build_log = BuildLogView()
        self.build_log.set_size_request(-1, 150)
        self.editor_buildlog_paned.set_end_child(self.build_log)
        
        # Initially hide build log by setting position to maximum
        self.editor_buildlog_paned.set_position(10000)
        
        # Add sidebar and editor to content paned
        self.content_paned.set_start_child(self.sidebar)
        self.content_paned.set_end_child(self.editor_buildlog_paned)
        self.content_paned.set_resize_start_child(False)
        
        # Create preview area
        self.preview_box = self.create_preview_area()
        
        # Add content and preview to main paned
        self.main_paned.set_start_child(self.content_paned)
        self.main_paned.set_end_child(self.preview_box)
        
        # Set initial position for the main paned
        self.main_paned.set_position(650)
        
        # Create status bar
        self.statusbar = self.create_statusbar()
        
        # Add all components to main box
        self.main_box.append(self.header)
        self.main_box.append(self.main_paned)
        self.main_box.append(self.statusbar)
        
        # Set content
        self.set_content(self.main_box)
    
    def create_header_bar(self):
        headerbar = Adw.HeaderBar()
        headerbar.add_css_class("toolbar")
        
        # Document actions
        new_button = create_button("document-new-symbolic", "New Document", self.on_new_document)
        headerbar.pack_start(new_button)
        
        open_button = create_button("document-open-symbolic", "Open Document", self.on_open_document)
        headerbar.pack_start(open_button)
        
        save_button = create_button("document-save-symbolic", "Save Document", self.on_save_document)
        headerbar.pack_start(save_button)
        
        # Build actions
        build_button = create_button("system-run-symbolic", "Build Document", self.on_build_document)
        headerbar.pack_end(build_button)
        
        # Build log toggle
        self.build_log_toggle = Gtk.ToggleButton()
        icon = Gtk.Image.new_from_icon_name("terminal-symbolic")
        self.build_log_toggle.set_child(icon)
        self.build_log_toggle.set_tooltip_text("Toggle Build Log")
        self.build_log_toggle.connect("toggled", self.on_build_log_toggled)
        headerbar.pack_end(self.build_log_toggle)
        
        # Preview toggle button
        self.preview_toggle = Gtk.ToggleButton()
        icon = Gtk.Image.new_from_icon_name("view-paged-symbolic")
        self.preview_toggle.set_child(icon)
        self.preview_toggle.set_tooltip_text("Toggle Preview")
        self.preview_toggle.connect("toggled", self.on_preview_toggled)
        self.preview_toggle.set_active(True)  # Preview enabled by default
        headerbar.pack_end(self.preview_toggle)
        
        # Settings menu
        menu_builder = Gtk.Builder()
        menu_builder.add_from_string('''
        <?xml version="1.0" encoding="UTF-8"?>
        <interface>
          <menu id="app-menu">
            <section>
              <item>
                <attribute name="label">Preferences</attribute>
                <attribute name="action">app.preferences</attribute>
              </item>
              <item>
                <attribute name="label">Keyboard Shortcuts</attribute>
                <attribute name="action">app.shortcuts</attribute>
              </item>
            </section>
            <section>
              <item>
                <attribute name="label">About Setzer</attribute>
                <attribute name="action">app.about</attribute>
              </item>
            </section>
          </menu>
        </interface>
        ''')
        menu_model = menu_builder.get_object('app-menu')
        
        menu_button = create_menu_button("open-menu-symbolic", "Settings", menu_model)
        headerbar.pack_end(menu_button)
        
        self.headerbar = headerbar
        return headerbar
    
    def create_sidebar(self):
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar_box.add_css_class("sidebar")
        
        # Sidebar header
        sidebar_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sidebar_header.set_margin_top(10)
        sidebar_header.set_margin_bottom(10)
        sidebar_header.set_margin_start(10)
        sidebar_header.set_margin_end(10)
        
        sidebar_label = Gtk.Label(label="Document Structure")
        sidebar_label.set_halign(Gtk.Align.START)
        sidebar_label.set_hexpand(True)
        
        refresh_button = create_button("view-refresh-symbolic", "Refresh Structure", self.on_refresh_structure)
        refresh_button.set_valign(Gtk.Align.CENTER)
        
        sidebar_header.append(sidebar_label)
        sidebar_header.append(refresh_button)
        
        # Document structure list using GTK4 ListBox
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_vexpand(True)
        
        # Create a ListBox for document structure
        self.structure_list = Gtk.ListBox()
        self.structure_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.structure_list.set_activate_on_single_click(True)
        self.structure_list.connect("row-activated", self.on_structure_item_activated)
        
        # Add structure items
        self.populate_document_structure()
        
        scrolled_window.set_child(self.structure_list)
        
        # Put everything in the sidebar
        sidebar_box.append(sidebar_header)
        sidebar_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        sidebar_box.append(scrolled_window)
        
        return sidebar_box
    
    def populate_document_structure(self):
        # Sample document structure
        structure = [
            {"title": "Introduction", "level": 0, "children": [
                {"title": "Background", "level": 1, "children": []},
                {"title": "Motivation", "level": 1, "children": []}
            ]},
            {"title": "Methods", "level": 0, "children": [
                {"title": "Experiment Setup", "level": 1, "children": []},
                {"title": "Data Collection", "level": 1, "children": []}
            ]},
            {"title": "Results", "level": 0, "children": []},
            {"title": "Discussion", "level": 0, "children": []},
            {"title": "Conclusion", "level": 0, "children": []},
            {"title": "References", "level": 0, "children": []}
        ]
        
        # Clear existing items
        while True:
            row = self.structure_list.get_row_at_index(0)
            if row is None:
                break
            self.structure_list.remove(row)
        
        # Add items recursively
        for item in structure:
            self.add_structure_item(item)
            for child in item.get("children", []):
                self.add_structure_item(child)
    
    def add_structure_item(self, item):
        # Create row for the item
        row = Gtk.ListBoxRow()
        
        # Create the box for the content
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_margin_top(2)
        box.set_margin_bottom(2)
        box.set_margin_start(4 + (item["level"] * 16))  # Indent based on level
        box.set_margin_end(4)
        
        # Add icon
        icon = Gtk.Image.new_from_icon_name("text-x-generic")
        icon.set_margin_end(8)
        box.append(icon)
        
        # Add label
        label = Gtk.Label(label=item["title"])
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        box.append(label)
        
        # Set the box as the child of the row
        row.set_child(box)
        
        # Add CSS classes based on level
        row.add_css_class("structure-item")
        row.add_css_class(f"level-{item['level']}")
        
        # Add to list
        self.structure_list.append(row)
    
    def create_editor_area(self):
        editor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        editor_box.add_css_class("editor")
        
        # LaTeX formatting toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        toolbar.add_css_class("toolbar")
        toolbar.set_margin_start(5)
        toolbar.set_margin_end(5)
        toolbar.set_margin_top(5)
        toolbar.set_margin_bottom(5)
        toolbar.set_spacing(5)
        
        # Add LaTeX command buttons
        buttons = [
            ("Bold", "\\textbf{}", "format-text-bold-symbolic"),
            ("Italic", "\\textit{}", "format-text-italic-symbolic"),
            ("Underline", "\\underline{}", "format-text-underline-symbolic"),
            ("Math Mode", "$", "accessories-calculator-symbolic"),
            ("Enumerate", "\\begin{enumerate}\n\\item \n\\end{enumerate}", "view-list-symbolic"),
            ("Itemize", "\\begin{itemize}\n\\item \n\\end{itemize}", "view-list-bullet-symbolic"),
            ("Figure", "\\begin{figure}\n\\centering\n\\includegraphics{}\n\\caption{}\n\\label{fig:}\n\\end{figure}", "insert-image-symbolic"),
            ("Table", "\\begin{table}\n\\centering\n\\caption{}\n\\label{tab:}\n\\begin{tabular}{}\n\\end{tabular}\n\\end{table}", "x-office-spreadsheet-symbolic"),
        ]
        
        for tooltip, text, icon in buttons:
            button = create_button(icon, tooltip, lambda btn, t=text: self.insert_latex_command(t))
            toolbar.append(button)
        
        # Create a scrolled window for the text editor
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_vexpand(True)
        
        # Create source view for editing
        self.source_view = GtkSource.View()
        self.source_view.set_monospace(True)
        self.source_view.set_auto_indent(True)
        self.source_view.set_indent_width(2)
        self.source_view.set_insert_spaces_instead_of_tabs(True)
        self.source_view.set_tab_width(2)
        self.source_view.set_show_line_numbers(True)
        self.source_view.set_highlight_current_line(True)
        
        # Create buffer
        self.buffer = GtkSource.Buffer()
        self.buffer.set_text(self.get_sample_document())
        
        # Set syntax highlighting for LaTeX
        source_manager = GtkSource.LanguageManager()
        latex_lang = source_manager.get_language("latex")
        if latex_lang:
            self.buffer.set_language(latex_lang)
        
        # Set style scheme
        style_manager = GtkSource.StyleSchemeManager()
        style = style_manager.get_scheme("classic")
        if style:
            self.buffer.set_style_scheme(style)
        
        self.source_view.set_buffer(self.buffer)
        scrolled_window.set_child(self.source_view)
        
        # Add toolbar and editor to the box
        editor_box.append(toolbar)
        editor_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        editor_box.append(scrolled_window)
        
        return editor_box
    
    def create_preview_area(self):
        # Preview area
        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        preview_box.add_css_class("preview")
        
        # Preview toolbar
        preview_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        preview_toolbar.add_css_class("toolbar")
        preview_toolbar.set_spacing(5)
        preview_toolbar.set_margin_start(5)
        preview_toolbar.set_margin_end(5)
        preview_toolbar.set_margin_top(5)
        preview_toolbar.set_margin_bottom(5)
        
        # Zoom out button
        self.zoom_out_button = create_button("zoom-out-symbolic", "Zoom Out", self.on_zoom_out)
        self.zoom_out_button.add_css_class("scbar")
        preview_toolbar.append(self.zoom_out_button)
        
        # Zoom level button
        self.zoom_level_label = FixedWidthLabel(66)
        self.zoom_level_label.set_text("100%")
        self.zoom_level_label.add_css_class("zoom-level-button")
        
        self.zoom_level_button = Gtk.Button()
        self.zoom_level_button.set_tooltip_text("Set Zoom Level")
        self.zoom_level_button.add_css_class("scbar")
        self.zoom_level_button.set_child(self.zoom_level_label)
        self.zoom_level_button.connect("clicked", self.on_zoom_level_clicked)
        preview_toolbar.append(self.zoom_level_button)
        
        # Zoom in button
        self.zoom_in_button = create_button("zoom-in-symbolic", "Zoom In", self.on_zoom_in)
        self.zoom_in_button.add_css_class("scbar")
        preview_toolbar.append(self.zoom_in_button)
        
        # Add spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        preview_toolbar.append(spacer)
        
        # Recolor PDF toggle
        self.recolor_pdf_toggle = Gtk.ToggleButton()
        icon = Gtk.Image.new_from_icon_name("color-select-symbolic")  # Using a standard icon
        self.recolor_pdf_toggle.set_child(icon)
        self.recolor_pdf_toggle.set_tooltip_text("Match Theme Colors")
        self.recolor_pdf_toggle.add_css_class("scbar")
        self.recolor_pdf_toggle.connect("toggled", self.on_recolor_pdf_toggled)
        preview_toolbar.append(self.recolor_pdf_toggle)
        
        # External viewer button
        self.external_viewer_button = create_button("document-open-symbolic", "Open in External Viewer", self.on_external_viewer)
        self.external_viewer_button.add_css_class("scbar")
        preview_toolbar.append(self.external_viewer_button)
        
        # Create preview view
        self.preview_view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.preview_view.set_vexpand(True)
        self.preview_view.add_css_class("preview")
        
        # Content area for PDF preview
        self.preview_content = ScrollingWidget()
        self.drawing_area = self.preview_content.content
        
        # Blank slate for no PDF
        self.blank_slate = BlankSlateView()
        
        # Stack to switch between blank and PDF
        self.preview_stack = Gtk.Stack()
        self.preview_stack.set_vexpand(True)
        self.preview_stack.add_named(self.blank_slate, "blank_slate")
        self.preview_stack.add_named(self.preview_content.view, "pdf")
        
        # Show blank slate by default
        self.preview_stack.set_visible_child_name("blank_slate")
        
        # Overlay for link targets
        self.preview_overlay = Gtk.Overlay()
        self.preview_overlay.set_vexpand(True)
        self.preview_overlay.set_child(self.preview_stack)
        
        # Target label for showing link info
        self.target_label = Gtk.Label()
        self.target_label.set_halign(Gtk.Align.START)
        self.target_label.set_valign(Gtk.Align.END)
        self.target_label.add_css_class("target-label")
        self.target_label.set_visible(False)
        self.preview_overlay.add_overlay(self.target_label)
        
        # Paging label
        self.paging_label = FixedWidthLabel(100)
        self.paging_label.set_text("Page 1 / 1")
        self.paging_label.add_css_class("paging-widget")
        
        # Status bar for preview
        preview_statusbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        preview_statusbar.set_spacing(5)
        preview_statusbar.set_margin_start(5)
        preview_statusbar.set_margin_end(5)
        preview_statusbar.set_margin_top(5)
        preview_statusbar.set_margin_bottom(5)
        preview_statusbar.append(self.paging_label)
        
        # Add everything to preview box
        preview_box.append(preview_toolbar)
        preview_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        preview_box.append(self.preview_overlay)
        preview_box.append(preview_statusbar)
        
        return preview_box
    
    def create_statusbar(self):