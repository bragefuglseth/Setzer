#!/usr/bin/env python3
# coding: utf-8

# Copyright (C) 2017, 2018 Robert Griesel
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

import os.path
import time

import setzer.document.build_system.build_system as build_system
import setzer.document.document_viewgtk as document_view
import setzer.document.search.search as search
import setzer.document.code_folding.code_folding as code_folding
import setzer.document.preview.preview as preview
import setzer.document.source_buffer.source_buffer as source_buffer
from setzer.helpers.observable import Observable
from setzer.app.service_locator import ServiceLocator


class Document(Observable):

    def __init__(self):
        Observable.__init__(self)

        self.settings = ServiceLocator.get_settings()

        self.displayname = ''
        self.filename = None
        self.save_date = None
        self.deleted_on_disk_dialog_shown_after_last_save = False
        self.last_activated = 0
        self.dark_mode = False

        self.parser = None
        self.build_system = None
        self.source_buffer = source_buffer.SourceBuffer(self)
        self.source_buffer.connect('changed', self.on_buffer_changed)
        self.source_buffer.connect('modified-changed', self.on_modified_changed)

    def set_search_text(self, search_text):
        self.source_buffer.search_settings.set_search_text(search_text)

    def on_buffer_changed(self, buffer):
        buffer.update_indentation_tags()

        if self.parser != None:
            self.parser.on_buffer_changed()

        try: self.code_folding.on_buffer_changed(buffer)
        except AttributeError: pass

        self.source_buffer.update_placeholder_selection()

        if self.is_empty():
            self.add_change_code('document_not_empty')
        else:
            self.add_change_code('document_empty')

        self.add_change_code('buffer_changed')

    def on_modified_changed(self, buffer):
        self.add_change_code('modified_changed')

    def set_dark_mode(self, dark_mode):
        self.dark_mode = dark_mode
        self.get_buffer().set_use_dark_scheme(dark_mode)

    def get_buffer(self):
        return self.source_buffer

    def get_search_context(self):
        return self.source_buffer.search_context

    def set_filename(self, filename):
        if filename == None:
            self.filename = filename
        else:
            self.filename = os.path.realpath(filename)
        self.add_change_code('filename_change', filename)

    def get_filename(self):
        return self.filename
        
    def get_dirname(self):
        if self.filename != None:
            return os.path.dirname(self.filename)
        else:
            return ''

    def get_displayname(self):
        if self.filename != None:
            return self.get_filename()
        else:
            return self.displayname
        
    def set_displayname(self, displayname):
        self.displayname = displayname
        self.add_change_code('displayname_change')

    def get_basename(self):
        if self.filename != None:
            return os.path.basename(self.filename)
        else:
            return self.displayname

    def get_last_activated(self):
        return self.last_activated
        
    def set_last_activated(self, date):
        self.last_activated = date

    def get_modified(self):
        return self.get_buffer().get_modified()

    def populate_from_filename(self):
        if self.filename == None: return False
        if not os.path.isfile(self.filename):
            self.set_filename(None)
            return False
        if self.get_buffer() == None: return False

        with open(self.filename) as f:
            text = f.read()
        self.initially_set_text(text)
        self.place_cursor(0, 0)
        self.update_save_date()
        return True
                
    def save_to_disk(self):
        if self.filename == None: return False
        if self.get_buffer() == None: return False
        else:
            text = self.get_text()
            if text != None:
                with open(self.filename, 'w') as f:
                    f.write(text)
                self.update_save_date()
                self.deleted_on_disk_dialog_shown_after_last_save = False
                self.get_buffer().set_modified(False)

    def update_save_date(self):
        self.save_date = os.path.getmtime(self.filename)

    def get_changed_on_disk(self):
        return self.save_date <= os.path.getmtime(self.filename) - 0.001

    def get_deleted_on_disk(self):
        return not os.path.isfile(self.filename)

    def initially_set_text(self, text):
        self.get_buffer().initially_set_text(text)

    def get_text(self):
        return self.get_buffer().get_all_text()

    def get_text_after_offset(self, offset):
        return self.get_buffer().get_text_after_offset(offset)

    def get_selected_text(self):
        return self.get_buffer().get_selected_text()

    def get_line_at_cursor(self):
        return self.get_buffer().get_line_at_cursor()

    def get_char_at_cursor(self):
        return self.get_buffer().get_char_at_cursor()

    def get_line(self, line_number):
        return self.get_buffer().get_line(line_number)

    def is_empty(self):
        return self.source_buffer.is_empty()

    def set_initial_folded_regions(self, folded_regions):
        self.code_folding.set_initial_folded_regions(folded_regions)
        
    def place_cursor(self, line_number, offset=0):
        self.get_buffer().place_cursor_and_scroll(line_number, offset)

    def get_cursor_offset(self):
        return self.get_buffer().get_cursor_offset()

    def get_cursor_line_offset(self):
        return self.get_buffer().get_cursor_line_offset()

    def cursor_inside_latex_command_or_at_end(self):
        current_word = self.get_latex_command_at_cursor()
        if ServiceLocator.get_regex_object(r'\\(\w*(?:\*){0,1})').fullmatch(current_word):
            return True
        return False

    def cursor_at_latex_command_end(self):
        current_word = self.get_latex_command_at_cursor()
        if ServiceLocator.get_regex_object(r'\\(\w*(?:\*){0,1})').fullmatch(current_word):
            return self.get_buffer().cursor_ends_word()
        return False

    def insert_before_document_end(self, text):
        self.get_buffer().insert_before_document_end(text)

    def add_packages(self, packages):
        self.get_buffer().add_packages(packages)

    def get_packages(self):
        return self.parser.symbols['packages']

    def get_package_details(self):
        return self.parser.symbols['packages_detailed']

    def remove_packages(self, packages):
        self.get_buffer().remove_packages(packages)

    def insert_text(self, line_number, offset, text, indent_lines=True):
        self.get_buffer().insert_text(line_number, offset, text, indent_lines)

    def insert_text_at_cursor(self, text, indent_lines=True, scroll=True, select_dot=True):
        self.get_buffer().insert_text_at_cursor(text, indent_lines, scroll, select_dot)

    def replace_range(self, offset, length, text, indent_lines=True, select_dot=True):
        self.get_buffer().replace_range_by_offset_and_length(offset, length, text, indent_lines, select_dot)

    def insert_before_after(self, before, after):
        self.get_buffer().insert_before_after(before, after)

    def add_backslash_with_space(self):
        self.get_buffer().add_backslash_with_space()

    def autoadd_latex_brackets(self, char):
        self.get_buffer().autoadd_latex_brackets(char)

    def undo(self):
        self.get_buffer().undo()

    def redo(self):
        self.get_buffer().redo()

    def cut(self):
        self.get_buffer().cut()

    def copy(self):
        self.get_buffer().copy()

    def paste(self):
        self.get_buffer().paste()

    def delete_selection(self):
        self.get_buffer().delete_selection(True, True)

    def select_all(self):
        self.get_buffer().select_all()


