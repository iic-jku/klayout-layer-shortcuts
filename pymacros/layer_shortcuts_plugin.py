# --------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2025 Martin Jan Köhler
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-or-later
#--------------------------------------------------------------------------------

from __future__ import annotations
from pathlib import Path
import traceback
from typing import *

import pya

from klayout_plugin_utils.debugging import debug, Debugging
from klayout_plugin_utils.event_loop import EventLoop

from pdk_info import *


class LayerShortcutsPluginFactory(pya.PluginFactory):
    def __init__(self):
        super().__init__()
                
        try:
            mw = pya.MainWindow.instance()
            self._in_conflicting_shortcut_dialog = False
            self._hide_empty_layers_user_cfg = bool(mw.get_config('hide-empty-layers') == 'true')
            self._ignore_hide_empty_layers_change = False
            
            script_dir = Path(__file__).resolve().parent
            self.pdk_info_factory = PDKInfoFactory(search_path=[script_dir / '..' / 'pdks'])
            
            self.has_tool_entry = False
            self.register(-1000, "layer_shortcuts", "Layer Shortcuts")
        except Exception as e:
            print("LayerShortcutsPluginFactory.ctor caught an exception", e)
            traceback.print_exc()
    
    def on_current_view_changed(self):
        if Debugging.DEBUG:
             debug(f"LayerShortcutsPluginFactory.on_current_view_changed, self.view={self.view}")
             debug(f"LayerShortcutsPluginFactory.on_current_view_changed, self.view={self.view}, "
                   f"active cell name={'none' if self.cell_view is None else self.cell_view.cell_name}")

        if self.view is None:
            return

        try:
            if self.layout is None:
                if Debugging.DEBUG:
                    debug("LayerShortcutPlugin.on_current_view_changed: no layout yet, register callback")
                self.view.on_file_open.connect(self.layout_changed)
            else:
                self.layout_changed()
        except Exception as e:
            print("LayerShortcutsPluginFactory.on_current_view_changed caught an exception", e)
            traceback.print_exc()
        
    def on_view_created(self):
        if Debugging.DEBUG:
             debug(f"LayerShortcutsPluginFactory.on_view_created, self.view={self.view}, "
                   f"active cell name={'none' if self.cell_view is None else self.cell_view.cell_name}")

        # NOTE: sometimes when starting klayout -e directly with a layout file
        #       on_current_view_changed won't get emitted
        mw = pya.MainWindow.instance()
        menu = mw.menu()
        if not menu.is_menu("edit_menu.layer_navigation_group"):
            if Debugging.DEBUG:
                debug(f"LayerShortcutsPluginFactory.on_view_created, no menu found yet, "
                      f"seems we are in a startup situation, "
                      f"so we'll create the menu now")
            self.setup()

    def on_view_closed(self):
        if Debugging.DEBUG:
             debug("LayerShortcutsPluginFactory.on_view_closed")
      
    def menu_activated(self, symbol: str) -> bool:
        if Debugging.DEBUG:
            debug(f"LayerShortcutsPluginFactory.menu_activated: symbol={symbol}")
            
        if symbol == 'technology_selector:apply_technology':
            if Debugging.DEBUG:
                debug(f"LayerShortcutsPluginFactory.menu_activated: "
                      f"pya.CellView.active().technology().name={pya.CellView.active().technology} (NOTE: old, that's why we need defer)")
            # NOTE: we have to defer, otherwise the CellView won't have the new tech yet
            EventLoop.defer(self.technology_applied)
            
    def on_active_cellview_changed(self) -> bool:
        if Debugging.DEBUG:
            debug(f"LayerShortcutsPluginFactory.on_active_cellview_changed: {self.cell_view.cell_name}")
            
    @property
    def view(self) -> pya.LayoutView:
        return pya.LayoutView.current()
            
    @property
    def cell_view(self) -> pya.CellView:
        return pya.CellView.active()

    @property
    def layout(self) -> pya.Layout:
        return self.cell_view.layout()

    @property
    def tech(self) -> pya.Technology:
        return self.layout.technology()

    def clear_menu(self):
        if Debugging.DEBUG:
            debug("LayerShortcutsPluginFactory.clear_menu")
                
        mw = pya.MainWindow.instance()
        menu = mw.menu()
        menu.clear_menu("edit_menu.layer_navigation_group")
    
    def select_layer(self, list_idx: int, layer: pya.LayerProperties):
        iter = self.view.begin_layers(list_idx)
        while not iter.at_end():
            if iter.current().name == layer.name:
                self.view.current_layer = iter
                break
            iter.next()
    
    def layer_list_index_for_tab_name(self, name: str) -> int:
        lv: pya.LayoutView = self.view
        if 'layer_list_name' in dir(lv):  # Only KLayout >=0.30.4 supports LayerView.layer_list_name()!
            for attempt in range(0, 3):
                names = []
                for i in range(0, lv.num_layer_lists()):
                    list_name = lv.layer_list_name(i)
                    if name == list_name:  # THIS API function
                        return i
                    names.append(list_name)
                if Debugging.DEBUG:
                    debug(f"LayerShortcutsPluginFactory.layer_list_index_for_tab_name: {name}, "
                          f"could not find a layer, names were: {names} (attempt #{attempt})")
            
        return -1
    
    def update_layer_list(self, 
                          name: str, 
                          visible_layers: List[pya.LayerProperties],
                          selected_layer: Optional[pya.LayerProperties]) -> int:
        if Debugging.DEBUG:
            debug(f"LayerShortcutsPluginFactory.update_layer_list: {name}, "
                  f"{len(visible_layers)} layers, selected_layer={selected_layer.name if selected_layer else 'none'}")
        
        list_idx = self.layer_list_index_for_tab_name(name)
        
        if list_idx == -1:
            list_idx = self.view.num_layer_lists()
            self.view.insert_layer_list(list_idx)
            self.view.rename_layer_list(list_idx, name)
        else:
            # NOTE: as of KLayout 0.30.3, clear_layers() also deletes the name of the layer list tab!
            #       this will be fixed above 0.30.4, but as a workaround we will always re-set the name!
            self.view.clear_layers(list_idx)
            self.view.rename_layer_list(list_idx, name)

        self.view.current_layer_list = list_idx

        for l in visible_layers:
            l.visible = True
            self.view.insert_layer(list_idx, self.view.end_layers(), l)
    
        if selected_layer is not None:
            # FIXME: currently, the KLayout Scripting API won't set the selection
            #        unless we defer in the event loop
            #        self.view.update_content()  # does also not help
            
            mw = pya.Application.instance().main_window()
        
            EventLoop.defer(lambda li=list_idx, sl=selected_layer: self.select_layer(li, sl))
        
        return list_idx
    
    def remove_layer_list(self, name: str):
        list_idx = self.layer_list_index_for_tab_name(name)
        if list_idx != -1:
            self.view.delete_layer_list(list_idx)
        else:
            if Debugging.DEBUG:
                debug(f"LayerShortcutsPluginFactory.remove_layer_list: no tab list found for name {name}")
    
    def set_config_hide_empty_layers(self, hide: bool):
        self._ignore_hide_empty_layers_change = True  # ensure self.config does not interpret this as a user-triggered change
        mw = pya.MainWindow.instance()
        mw.set_config('hide-empty-layers', 'true' if hide else 'false')
        self._ignore_hide_empty_layers_change = False
    
    def trigger_shortcut(self, action: pya.Action, pdk_info: PDKInfo, shortcut: Shortcut):
        if Debugging.DEBUG:
            debug(f"LayerShortcutsPluginFactory.trigger_shortcut: {action} {action.title}")
        
        source_list_idx = 0
        visible_layers: List[pya.LayerProperties] = []
        selected_layer = None
        
        def apply_function(layer_descriptor: LayerDescriptor,
                           incl_function: Callable[pya.LayerPropertiesIterator, pya.LayerPropertiesNodeRef], 
                           excl_function: Callable[pya.LayerPropertiesIterator, pya.LayerPropertiesNodeRef]):
                match layer_descriptor.kind:
                    case LayerDescriptorKind.ALL:
                        iter = self.view.begin_layers(source_list_idx)
                        while not iter.at_end():
                            lp = iter.current()
                            incl_function(iter, lp)
                            iter.next()
                    case LayerDescriptorKind.NONE:
                        iter = self.view.begin_layers(source_list_idx)
                        while not iter.at_end():
                            lp = iter.current()
                            excl_function(iter, lp)
                            iter.next()
                    case LayerDescriptorKind.LAYERS:
                        iter = self.view.begin_layers(source_list_idx)
                        while not iter.at_end():
                            lp = iter.current()
                            if lp.name in layer_descriptor.layers:
                                incl_function(iter, lp)
                            else:
                                excl_function(iter, lp)
                            iter.next()
                    case LayerDescriptorKind.LAYER_GROUPS:
                        layer_groups = pdk_info.layer_groups(layer_descriptor.layer_groups)
                        layer_names = {l for g in layer_groups for l in g.layers}
                        
                        iter = self.view.begin_layers(source_list_idx)
                        while not iter.at_end():
                            lp = iter.current()
                            lname = lp.name or lp.source
                            if lname is None:
                                continue
                            if lname in layer_names:
                                incl_function(iter, lp)
                            else:
                                excl_function(iter, lp)
                            iter.next()
        
        def hide_incl(iter: pya.LayerPropertiesIterator, lp: pya.LayerPropertiesNodeRef):
            pass
        
        def hide_excl(iter: pya.LayerPropertiesIterator, lp: pya.LayerPropertiesNodeRef):
            visible_layers.append(lp)
        
        def show_incl(iter: pya.LayerPropertiesIterator, lp: pya.LayerPropertiesNodeRef):
            visible_layers.append(lp)
        
        def show_excl(iter: pya.LayerPropertiesIterator, lp: pya.LayerPropertiesNodeRef):
            pass
            
        def select_incl(iter: pya.LayerPropertiesIterator, lp: pya.LayerPropertiesNodeRef):
            nonlocal selected_layer
            selected_layer = lp
            
        def select_excl(iter: pya.LayerPropertiesIterator, lp: pya.LayerPropertiesNodeRef): 
            pass

        for action in shortcut.actions:
            match action.kind:
                case ActionKind.RESET_AND_SHOW_ALL_LAYERS:
                    self.view.current_layer_list = 0
                    self.remove_layer_list('LayNav')
                    for lp in self.view.each_layer():  # not using apply_function, it works only with LayTab tab
                        lp.visible = True
                    self.view.update_content()
                    if self._hide_empty_layers_user_cfg:
                        self.set_config_hide_empty_layers(True)
                    return
                case ActionKind.RESET_AND_HIDE_ALL_LAYERS:
                    self.view.current_layer_list = 0
                    self.remove_layer_list('LayNav')
                    for lp in self.view.each_layer():  # not using apply_function, it works only with LayTab tab
                        lp.visible = False
                    self.view.update_content()
                    if self._hide_empty_layers_user_cfg:
                        self.set_config_hide_empty_layers(True)
                    return
                case ActionKind.HIDE_LAYERS:
                    apply_function(action.layers, hide_incl, hide_excl)
                case ActionKind.SHOW_LAYERS:
                    apply_function(action.layers, show_incl, show_excl)
                case ActionKind.SELECT_LAYER:
                    apply_function(action.layers, select_incl, select_excl)
                case _:
                    raise NotImplementedError()

        # NOTE: When the user executes any focus commands, 
        #       we can assume that the layers should be made visible
        self.set_config_hide_empty_layers(False)

        self.update_layer_list('LayNav', visible_layers, selected_layer)
        
    def set_menu_for_current_tech(self):
        if Debugging.DEBUG:
            debug(f"LayerShortcutsPluginFactory.set_menu_for_current_tech, tech {self.tech.name}")
        
        pdk_info = self.pdk_info_factory.pdk_info(self.tech.name)
        if pdk_info is None:
            print(f"ERROR: no PDK info found for tech {self.tech.name}")
            return
        
        mw = pya.MainWindow.instance()
        menu = mw.menu()
        
        menu.insert_separator("edit_menu.end", "layer_navigation_separator")
        menu.insert_menu("edit_menu.end", "layer_navigation_group",  "Layer Navigation")

        for i, s in enumerate(pdk_info.shortcuts):
            action = pya.Action()
            action.default_shortcut = s.key
            action.shortcut = s.key
            action.title = s.title
            action.on_triggered += lambda a=action, p=pdk_info, s=s: self.trigger_shortcut(a, p, s)
            menu.insert_item(f"edit_menu.layer_navigation_group.#{i}", f"shortcut_{i}", action)

    def setup(self):
        if self._in_conflicting_shortcut_dialog:
            if Debugging.DEBUG:
                debug(f"LayerShortcutsPluginFactory.setup, "
                      f"conflicting shortcut dialog already displayed, early exit")
            return
          
        try:
            if Debugging.DEBUG:
                msg = f"LayerShortcutsPluginFactory.setup, "\
                      f"for cell view {self.cell_view.cell_name}, "
                if self.layout is None:
                    msg += "no layout yet"
                else:
                    msg += f"tech: {self.tech.name}, "\
                           f"self.tech.name: {self.tech.name}"
                debug(msg)
    
            if self.layout is None:
                self.clear_menu()
            else:
                self.check_for_ambiguous_shortcuts()
                self.reset_menu()
        except Exception as e:
            print("LayerShortcutsPluginFactory.setup caught an exception", e)
            traceback.print_exc()            

    @staticmethod
    def is_key_bound(key: str) -> bool:
        return key is not None and key != '' and key != 'none'

    def all_actions_with_keybindings(self) -> List[pya.Action]:
        mw = pya.MainWindow.instance()
        menu = mw.menu()
        
        def actions_with_keybindings(path: str) -> List[Tuple[str, pya.Action]]:
            actions = []
        
            action = menu.action(path)
            if action and self.is_key_bound(action.effective_shortcut()):
                actions.append((path, action))
                
            for subpath in menu.items(path):
                actions += actions_with_keybindings(subpath)
            return actions
            
        return actions_with_keybindings(path="")

    def check_for_ambiguous_shortcuts(self):
        pdk_info = self.pdk_info_factory.pdk_info(self.tech.name)
        if pdk_info is None:
            print(f"ERROR: no PDK info found for tech {self.tech.name}")
            return
        
        configured_shortcuts: List[Tuple[str, str]] = []
        configured_shortcut_keys: Set[str] = set()
        for i, s in enumerate(pdk_info.shortcuts):
            if s.key in configured_shortcuts:
                print(f"[ERROR] in LayerShortcuts configuration for {self.tech.name}, shortcut '{s.key}' is defined multiple times")
            configured_shortcuts.append((s.title, s.key))
            configured_shortcut_keys.add(s.key)

        conflicts: List[Tuple[str, pya.Action]] = []
        conflict_keys: Set[str] = set()
        
        mw = pya.MainWindow.instance()
        menu = mw.menu()
        
        for path, action in self.all_actions_with_keybindings():
            # skip those added by this plugin
            if path.startswith('edit_menu.layer_navigation_group.'):
                continue
        
            shortcut = action.effective_shortcut()
            if not shortcut:
                continue
                
            if shortcut in configured_shortcut_keys:
                conflicts.append((path, action))
                conflict_keys.add(shortcut)
        
        if conflicts:
            msg = "The <i>LayerShortcuts</i> plugin wants to configure new shortcuts:<br/>"
            for title, key in configured_shortcuts:
                if key in conflict_keys:
                    msg += "<font color='red'>"
                msg += f"&nbsp;&nbsp;&nbsp;&nbsp;• <i>{title}</i> (<code>{key}</code>)<br/>"
                if key in conflict_keys:
                    msg += "</font>"
            
            msg += "<br/>Some shortcuts are already in use:<br/>"
            for path, action in conflicts:
                key = action.effective_shortcut()
                if key in conflict_keys:
                    msg += "<font color='red'>"
                msg += f"&nbsp;&nbsp;&nbsp;&nbsp;• <i>{action.title}</i> (<code>{key}</code>)<br/>"
                if key in conflict_keys:
                    msg += "</font>"
            msg += "<br/>Do you want to remove these conflicting shortcuts?"
            
            # Ask the user
            try:
                self._in_conflicting_shortcut_dialog = True
                reply = pya.QMessageBox.question(mw, "Shortcut Conflict", msg,
                                                 pya.QMessageBox.Yes | pya.QMessageBox.No)
                if reply == pya.QMessageBox.Yes:
                    for path, action in conflicts:
                        mw.set_key_bindings({path: 'none'})   # remove conflicting shortcut
                else:
                    pass  # user canceled
            finally:
                self._in_conflicting_shortcut_dialog = False
            
    def reset_menu(self):
        self.clear_menu()
        self.set_menu_for_current_tech()

    def layout_changed(self):
        if Debugging.DEBUG:
            debug(f"LayerShortcutsPluginFactory.layout_changed, "
                  f"for cell view {self.cell_view.cell_name}")
        
        try:
            self.setup()
            
            self.view.on_active_cellview_changed += self.on_active_cellview_changed
        except Exception as e:
            print("LayerShortcutsPluginFactory.layout_changed caught an exception", e)
            traceback.print_exc()        

    def technology_applied(self):
        new_tech_name = pya.CellView.active().technology
        if Debugging.DEBUG:
            debug(f"LayerShortcutsPluginFactory.technology_applied, "
                  f"for cell view {self.cell_view.cell_name}, "
                  f"tech: {new_tech_name}")
            
        try:
            self.setup()
            # NOTE: this configure-triggered event is sometimes called before the tech 
            #       of the layout really is updated, so we defer this in the event loop
            ## EventLoop.defer(self.setup)
        except Exception as e:
            print("LayerShortcutsPluginFactory.technology_applied caught an exception", e)
            traceback.print_exc()        
    
    def configure(self, name: str, value: str) -> bool:
        if Debugging.DEBUG:
            debug(f"LayerShortcutsPluginFactory.configure, name={name}, value={value}")
            
        if name == 'initial-technology':
            EventLoop.defer(self.technology_applied)
        elif name == 'hide-empty-layers' and not self._ignore_hide_empty_layers_change:
            self._hide_empty_layers_user_cfg = bool(value == 'true')
            
        return False
            
#--------------------------------------------------------------------------------

def on_current_view_changed():
    try:
      if Debugging.DEBUG:
          debug(f"(GLOBAL) on_current_view_changed")
      inst = LayerShortcutsPluginFactory.instance
      EventLoop.defer(inst.on_current_view_changed)
    except Exception as e:
        print("(GLOBAL) on_current_view_changed caught an exception", e)
        traceback.print_exc()
    
def on_view_created():
    try:
      if Debugging.DEBUG:
          debug("(GLOBAL) on_view_created")
      inst = LayerShortcutsPluginFactory.instance
      EventLoop.defer(inst.on_view_created)
    except Exception as e:
        print("(GLOBAL) on_view_created caught an exception", e)
        traceback.print_exc()


def on_view_closed():
    try:
      if Debugging.DEBUG:
          debug("(GLOBAL) on_view_closed")
      inst = LayerShortcutsPluginFactory.instance
      EventLoop.defer(inst.on_view_closed)
    except Exception as e:
        print("(GLOBAL) on_view_closed caught an exception", e)
        traceback.print_exc()


#--------------------------------------------------------------------------------

# NOTE: need to keep an instance currently.
# (will be fixed in 0.30.4, so we can pull a temporary instance)
mw = pya.MainWindow.instance()

mw.on_current_view_changed += on_current_view_changed
mw.on_view_created += on_view_created
mw.on_view_closed += on_view_closed
