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

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GLib, Gio, Gdk

from setzer.app.service_locator import ServiceLocator
from setzer.dialogs.dialog_locator import DialogLocator


class Actions(object):

    def __init__(self, workspace):
        self.workspace = workspace
        self.main_window = ServiceLocator.get_main_window()

        self.actions = dict()
        self.add_action('new-latex-document', self.new_latex_document)
        self.add_action('new-bibtex-document', self.new_bibtex_document)
        self.add_action('open-document-dialog', self.open_document_dialog)
        self.add_action('build', self.build)
        self.add_action('save-and-build', self.save_and_build)
        self.add_action('show-build-log', self.show_build_log)
        self.add_action('close-build-log', self.close_build_log)
        self.add_action('save', self.save)
        self.add_action('save-as', self.save_as)
        self.add_action('save-all', self.save_all)
        self.add_action('save-session', self.save_session)
        self.add_action('close-all-documents', self.close_all)
        self.add_action('close-active-document', self.close_active_document)

        self.add_action('show-document-wizard', self.start_wizard, None)
        self.add_action('insert-before-after', self.insert_before_after, GLib.VariantType('as'))
        self.add_action('insert-symbol', self.insert_symbol, GLib.VariantType('as'))
        self.add_action('insert-after-packages', self.insert_after_packages, GLib.VariantType('as'))
        self.add_action('insert-before-document-end', self.insert_before_document_end, GLib.VariantType('as'))
        self.add_action('add-packages', self.add_packages, GLib.VariantType('as'))
        self.add_action('include-bibtex-file', self.start_include_bibtex_file_dialog, None)
        self.add_action('include-latex-file', self.start_include_latex_file_dialog, None)
        self.add_action('add-remove-packages-dialog', self.start_add_remove_packages_dialog, None)
        self.add_action('toggle-comment', self.toggle_comment)

        self.add_action('cut', self.cut)
        self.add_action('copy', self.copy)
        self.add_action('paste', self.paste)
        self.add_action('delete-selection', self.delete_selection)
        self.add_action('select-all', self.select_all)
        self.add_action('undo', self.undo)
        self.add_action('redo', self.redo)
        self.add_action('show-about-dialog', self.show_about_dialog)

        self.actions['quit'] = Gio.SimpleAction.new('quit', None)
        self.main_window.add_action(self.actions['quit'])

        self.workspace.connect('document_removed', self.on_document_removed)
        self.workspace.connect('new_inactive_document', self.on_new_inactive_document)
        self.workspace.connect('new_active_document', self.on_new_active_document)

        self.update_actions()

    def add_action(self, name, callback, parameter=None):
        self.actions[name] = Gio.SimpleAction.new(name, parameter)
        self.main_window.add_action(self.actions[name])
        self.actions[name].connect('activate', callback)

    def on_document_removed(self, workspace, document):
        if self.workspace.active_document == None:
            self.activate_welcome_screen_mode()
            self.update_actions()

    def on_new_inactive_document(self, workspace, document):
        document.disconnect('modified_changed', self.on_modified_changed)
        document.source_buffer.connect('notify::can-undo', self.on_undo_changed)
        document.source_buffer.connect('notify::has-selection', self.on_has_selection_changed)

    def on_new_active_document(self, workspace, document):
        self.activate_document_mode()
        self.update_actions()
        document.connect('modified_changed', self.on_modified_changed)
        document.source_buffer.connect('notify::can-undo', self.on_undo_changed)
        document.source_buffer.connect('notify::has-selection', self.on_has_selection_changed)

    def on_modified_changed(self, document):
        self.update_actions()

    def on_undo_changed(self, buffer, can_undo):
        self.update_undo_redo()

    def on_redo_changed(self, buffer, can_redo):
        self.update_undo_redo()

    def on_has_selection_changed(self, buffer, has_selection):
        self.update_has_selection()

    def activate_welcome_screen_mode(self):
        self.actions['save-all'].set_enabled(False)

    def activate_document_mode(self):
        pass

    def update_actions(self):
        document = self.workspace.get_active_document()

        document_active = document != None
        self.actions['save-as'].set_enabled(document_active)
        self.actions['close-active-document'].set_enabled(document_active)
        self.actions['close-all-documents'].set_enabled(document_active)
        self.actions['save-session'].set_enabled(document_active)
        enable_save = document_active and (document.source_buffer.get_modified() or document.get_filename() == None)
        self.actions['save'].set_enabled(enable_save)
        self.actions['save-all'].set_enabled(self.workspace.get_unsaved_documents() != None)

        self.update_undo_redo()
        self.update_has_selection()

    def update_undo_redo(self):
        document = self.workspace.get_active_document()
        document_active = document != None

        self.actions['redo'].set_enabled(document_active and document.source_buffer.get_can_redo())
        self.actions['undo'].set_enabled(document_active and document.source_buffer.get_can_undo())

    def update_has_selection(self):
        document = self.workspace.get_active_document()
        if document == None:
            has_selection = False
        else:
            has_selection = self.workspace.get_active_document().source_buffer.get_has_selection()

        self.actions['cut'].set_enabled(has_selection)
        self.actions['copy'].set_enabled(has_selection)
        self.actions['delete-selection'].set_enabled(has_selection)

    def new_latex_document(self, action=None, parameter=None):
        document = self.workspace.create_latex_document()
        self.workspace.add_document(document)
        self.workspace.set_active_document(document)

    def new_bibtex_document(self, action=None, parameter=None):
        document = self.workspace.create_bibtex_document()
        self.workspace.add_document(document)
        self.workspace.set_active_document(document)

    def open_document_dialog(self, action=None, parameter=None):
        DialogLocator.get_dialog('open_document').run()

    def save_and_build(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        self.save()
        self.build()

    def build(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        document = self.workspace.get_root_or_active_latex_document()
        if document != None:
            document.build_widget.build_document_request()

    def show_build_log(self, action=None, parameter=''):
        self.workspace.set_show_build_log(True)

    def close_build_log(self, action=None, parameter=''):
        self.workspace.set_show_build_log(False)

    def save(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        active_document = self.workspace.get_active_document()
        if active_document.filename == None:
            self.save_as()
        else:
            active_document.save_to_disk()

    def save_as(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        document = self.workspace.get_active_document()
        DialogLocator.get_dialog('save_document').run(document)

    def save_all(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        active_document = self.workspace.get_active_document()
        return_to_active_document = False
        documents = self.workspace.get_unsaved_documents()
        if documents != None: 
            for document in documents:
                if document.get_filename() == None:
                    self.workspace.set_active_document(document)
                    return_to_active_document = True
                    DialogLocator.get_dialog('save_document').run(document)
                else:
                    document.save_to_disk()
            if return_to_active_document == True:
                self.workspace.set_active_document(document)

    def save_session(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        DialogLocator.get_dialog('save_session').run()

    def close_all(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        documents = self.workspace.get_all_documents()
        unsaved_documents = self.workspace.get_unsaved_documents()
        dialog = DialogLocator.get_dialog('close_confirmation')
        dialog.run({'unsaved_documents': unsaved_documents, 'documents': documents}, self.close_all_callback)

    def close_all_callback(self, parameters, response):
        not_save_to_close_documents = response['not_save_to_close_documents']
        for document in parameters['documents']:
            if document not in not_save_to_close_documents:
                self.workspace.remove_document(document)

    def close_active_document(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        document = self.workspace.get_active_document()
        if document.source_buffer.get_modified():
            dialog = DialogLocator.get_dialog('close_confirmation')
            dialog.run({'unsaved_documents': [document], 'document': document}, self.close_document_callback)
        else:
            self.workspace.remove_document(document)

    def close_document_callback(self, parameters, response):
        not_save_to_close = response['not_save_to_close_documents']
        if parameters['document'] not in not_save_to_close:
            self.workspace.remove_document(parameters['document'])

    def start_wizard(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        return #TODO
        document = self.workspace.get_active_document()
        DialogLocator.get_dialog('document_wizard').run(document)

    def insert_before_after(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return
        if parameter == None: return

        document = self.workspace.get_active_document()
        document.source_buffer.begin_user_action()

        before, after = parameter[0], parameter[1]
        bounds = document.source_buffer.get_selection_bounds()

        if len(bounds) > 1:
            text = before + document.source_buffer.get_text(*bounds, 0) + after
            document.source_buffer.delete_selection(False, False)
        else:
            text = before + '•' + after

        document.source_buffer.insert_at_cursor(text)
        document.select_first_dot_around_cursor(offset_before=len(text), offset_after=0)
        document.source_buffer.end_user_action()

    def insert_symbol(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return
        if parameter == None: return

        document = self.workspace.get_active_document()
        document.source_buffer.begin_user_action()

        text = parameter[0]
        bounds = document.source_buffer.get_selection_bounds()

        if len(bounds) > 1:
            document.source_buffer.delete_selection(False, False)

        document.source_buffer.insert_at_cursor(text)
        document.select_first_dot_around_cursor(offset_before=len(text), offset_after=0)
        document.source_buffer.end_user_action()

    def insert_after_packages(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        return #TODO
        document.insert_text_after_packages_if_possible(parameter[0])
        document.scroll_cursor_onscreen()

    def insert_before_document_end(self, action, parameter):
        if self.workspace.get_active_document() == None: return

        return #TODO
        document = self.workspace.get_active_document()
        document.insert_before_document_end(parameter[0])
        document.scroll_cursor_onscreen()

    def add_packages(self, action, parameter):
        if self.workspace.get_active_document() == None: return

        return #TODO
        if parameter == None: return
        document = self.workspace.get_active_document()
        if document.is_latex_document():
            document.add_packages(parameter)
            document.scroll_cursor_onscreen()

    def start_include_bibtex_file_dialog(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        return #TODO
        document = self.workspace.get_active_document()
        DialogLocator.get_dialog('include_bibtex_file').run(document)

    def start_include_latex_file_dialog(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        return #TODO
        document = self.workspace.get_active_document()
        DialogLocator.get_dialog('include_latex_file').run(document)

    def start_add_remove_packages_dialog(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        return #TODO
        document = self.workspace.get_active_document()
        DialogLocator.get_dialog('add_remove_packages').run(document)

    def toggle_comment(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        document = self.workspace.get_active_document()
        document.source_buffer.begin_user_action()

        bounds = document.source_buffer.get_selection_bounds()

        if len(bounds) > 1:
            end = (bounds[1].get_line() + 1) if (bounds[1].get_line_index() > 0) else bounds[1].get_line()
            line_numbers = list(range(bounds[0].get_line(), end))
        else:
            line_numbers = [document.source_buffer.get_iter_at_mark(document.source_buffer.get_insert()).get_line()]

        do_comment = False
        for line_number in line_numbers:
            line = document.get_line(line_number)
            if not line.lstrip().startswith('%'):
                do_comment = True

        if do_comment:
            for line_number in line_numbers:
                found, line_iter = document.source_buffer.get_iter_at_line(line_number)
                document.source_buffer.insert(line_iter, '%')
        else:
            for line_number in line_numbers:
                line = document.get_line(line_number)
                offset = len(line) - len(line.lstrip())
                found, start = document.source_buffer.get_iter_at_line(line_number)
                start.forward_chars(offset)
                end = start.copy()
                end.forward_char()
                document.source_buffer.delete(start, end)

        document.source_buffer.end_user_action()

    def cut(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        self.copy()
        self.workspace.get_active_document().delete_selection()

    def copy(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        self.workspace.get_active_document().source_view.emit('copy-clipboard')

    def paste(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        self.workspace.get_active_document().source_view.emit('paste-clipboard')

    def delete_selection(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        self.workspace.get_active_document().delete_selection()

    def select_all(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        self.workspace.get_active_document().select_all()

    def undo(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        self.workspace.get_active_document().source_buffer.undo()

    def redo(self, action=None, parameter=None):
        if self.workspace.get_active_document() == None: return

        self.workspace.get_active_document().source_buffer.redo()

    def show_about_dialog(self, action=None, parameter=''):
        DialogLocator.get_dialog('about').run()


