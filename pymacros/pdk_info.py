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
from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path
import sys
from typing import *
import unittest

from klayout_plugin_utils.debugging import debug, Debugging
from klayout_plugin_utils.str_enum_compat import StrEnum
from klayout_plugin_utils.dataclass_dict_helpers import dataclass_from_dict


LayerUniqueName = str
LayerGroupUniqueName = str


@dataclass
class NamedLayerGroup:
    name: LayerGroupUniqueName
    layers: List[LayerUniqueName]


class LayerDescriptorKind(StrEnum):
    NONE = 'none'
    ALL = 'all'
    LAYERS = 'layers'
    LAYER_GROUPS = 'layer_groups'


@dataclass
class LayerDescriptor:
    kind: LayerDescriptorKind
    layers: Optional[List[LayerUniqueName]] = None
    layer_groups: Optional[List[LayerGroupUniqueName]] = None


class ActionKind(StrEnum):
    RESET_AND_SHOW_ALL_LAYERS = 'reset_and_show_all_layers'
    RESET_AND_HIDE_ALL_LAYERS = 'reset_and_hid_all_layers'
    HIDE_LAYERS = 'hide_layers'
    SHOW_LAYERS = 'show_layers'
    SELECT_LAYER = 'select_layers'


@dataclass
class Action:
    kind: ActionKind
    layers: LayerDescriptor


@dataclass
class Shortcut:
    title: str
    key: str
    actions: List[Action]

#--------------------------------------------------------------------------------

@dataclass
class PDKInfo:
    tech_name: str
    layer_group_definitions: List[NamedLayerGroup]
    shortcuts: List[Shortcut]
    
    @classmethod
    def read_json(cls, path: Path) -> PDKInfo:
        with open(path) as f:
            data = json.load(f)
            return dataclass_from_dict(cls, data)
        
    def write_json(self, path: Path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=4)
            
    def layer_groups(self, names: List[LayerGroupUniqueName]) -> List[NamedLayerGroup]:
        return [g for g in self.layer_group_definitions if g.name in names]


class PDKInfoFactory:
    def __init__(self, search_path: List[Path]):
        self._pdk_infos_by_tech_name: Dict[str, PDKInfo] = {}
        
        json_files = sorted({f for p in search_path for f in p.glob('*.json')})
        for f in json_files:
            try:
                pdk_info = PDKInfo.read_json(f)
                self._pdk_infos_by_tech_name[pdk_info.tech_name] = pdk_info
            except Exception as e:
                print(f"Failed to parse PDK info file {f}, skipping this file…", e)
                
    def pdk_info(self, tech_name: str) -> Optional[PDKInfo]:
        return self._pdk_infos_by_tech_name.get(tech_name, None)
            
#--------------------------------------------------------------------------------

def build_example_pdk_info() -> PDKInfo:
    def met_layers(name: str) -> List[str]:
        return [f"{name}.drawing", f"{name}.pin", f"{name}.text", f"{name}.label"]

    def met_shortcut(prefix: str, key: str, i: int) -> List[Shortcut]:
        return [
            Shortcut(title=f"Focus on {prefix}{i} layers", key=key, actions=[
                Action(kind=ActionKind.HIDE_LAYERS, layers=LayerDescriptor(kind=LayerDescriptorKind.ALL)),
                Action(kind=ActionKind.SHOW_LAYERS, layers=LayerDescriptor(kind=LayerDescriptorKind.LAYER_GROUPS, layer_groups=[f"{prefix}{i}.Visible"])),
                Action(kind=ActionKind.SELECT_LAYER, layers=LayerDescriptor(kind=LayerDescriptorKind.LAYER_GROUPS, layer_groups=[f"{prefix}{i}.Selected"])),
            ]),
        ]
        
    layer_group_definitions: List[NamedLayerGroup] = []
    shortcuts: List[Shortcut] = [
        Shortcut(title='Show default layers', key='0', actions=[
            Action(kind=ActionKind.RESET_AND_SHOW_ALL_LAYERS, layers=LayerDescriptor(kind=LayerDescriptorKind.ALL))
        ]),
        Shortcut(title='Hide default layers', key=',', actions=[
            Action(kind=ActionKind.RESET_AND_HIDE_ALL_LAYERS, layers=LayerDescriptor(kind=LayerDescriptorKind.ALL))
        ]),
    ]
    for i in range(1, 6):
        shortcuts += met_shortcut(prefix='Metal', key=str(i), i=i)
    for i in range(1, 3):
        shortcuts += met_shortcut(prefix='TopMetal', key=str(5+i), i=i)
    shortcuts += [
            Shortcut(title='Focus on GatPoly layers', key='8', actions=[
                Action(kind=ActionKind.HIDE_LAYERS, layers=LayerDescriptor(kind=LayerDescriptorKind.ALL)),
                Action(kind=ActionKind.SHOW_LAYERS, layers=LayerDescriptor(kind=LayerDescriptorKind.LAYER_GROUPS, layer_groups=['GatPoly.Visible'])),
                Action(kind=ActionKind.SELECT_LAYER, layers=LayerDescriptor(kind=LayerDescriptorKind.LAYER_GROUPS, layer_groups=['GatPoly.Selected'])),
            ]),
            Shortcut(title='Focus on Activ layers', key='9', actions=[
                Action(kind=ActionKind.HIDE_LAYERS, layers=LayerDescriptor(kind=LayerDescriptorKind.ALL)),
                Action(kind=ActionKind.SHOW_LAYERS, layers=LayerDescriptor(kind=LayerDescriptorKind.LAYER_GROUPS, layer_groups=['Activ.Visible'])),
                Action(kind=ActionKind.SELECT_LAYER, layers=LayerDescriptor(kind=LayerDescriptorKind.LAYER_GROUPS, layer_groups=['Activ.Selected'])),
            ]),
    ]

    pi = PDKInfo(
        tech_name='sg13g2',
        layer_group_definitions = [
            NamedLayerGroup(name='Metal1.Visible',  layers=met_layers('Metal1') + ['Cont.drawing', 'Via1.drawing']),
            NamedLayerGroup(name='Metal1.Selected', layers=['Metal1.drawing']),
            NamedLayerGroup(name='Metal2.Visible',  layers=met_layers('Metal2') + ['Via1.drawing', 'Via2.drawing']),
            NamedLayerGroup(name='Metal2.Selected', layers=['Metal2.drawing']),
            NamedLayerGroup(name='Metal3.Visible',  layers=met_layers('Metal3') + ['Via2.drawing', 'Via3.drawing']),
            NamedLayerGroup(name='Metal3.Selected', layers=['Metal3.drawing']),
            NamedLayerGroup(name='Metal4.Visible',  layers=met_layers('Metal4') + ['Via3.drawing', 'Via4.drawing']),
            NamedLayerGroup(name='Metal4.Selected', layers=['Metal4.drawing']),
            NamedLayerGroup(name='Metal5.Visible',  layers=met_layers('Metal5') + ['Via4.drawing', 'TopVia1.drawing']),
            NamedLayerGroup(name='Metal5.Selected', layers=['Metal5.drawing']),
            NamedLayerGroup(name='TopMetal1.Visible',  layers=met_layers('TopMetal1') + ['TopVia1.drawing', 'TopVia2.drawing']),
            NamedLayerGroup(name='TopMetal1.Selected', layers=['TopMetal1.drawing']),
            NamedLayerGroup(name='TopMetal2.Visible',  layers=met_layers('TopMetal2') + ['TopVia1.drawing']),
            NamedLayerGroup(name='TopMetal2.Selected', layers=['TopMetal2.drawing']),
            NamedLayerGroup(name='GatPoly.Visible',  layers=['GatPoly.drawing', 'PolyRes.drawing', 'Cont.drawing']),
            NamedLayerGroup(name='GatPoly.Selected', layers=['GatPoly.drawing']),
            NamedLayerGroup(name='Activ.Visible',  layers=['Activ.drawing', 'Cont.drawing', 'NWell.drawing', 'nBuLay.drawing', 
                                                          'pSD.drawing', 'nSD.drawing', 'SalBlock.drawing', 'RES.drawing']),
            NamedLayerGroup(name='Activ.Selected', layers=['Activ.drawing']),
        ],
        shortcuts=shortcuts
    )
    return pi
    
    
#--------------------------------------------------------------------------------

class PDKInfoTests(unittest.TestCase):
    def setUp(self):
        self.pi = build_example_pdk_info()
        
    def check_pdk_info(self, pdk_info: PDKInfo):
        self.assertEqual('sg13g2', self.pi.tech_name)
        self.assertEqual('Metal1.Visible', self.pi.layer_group_definitions[0].name)
        self.assertIn('Metal1.drawing', self.pi.layer_group_definitions[0].layers)
        self.assertEqual('Show default layers', self.pi.shortcuts[0].title)
        self.assertEqual('0', self.pi.shortcuts[0].key)
        self.assertEqual(ActionKind.RESET_AND_SHOW_ALL_LAYERS, self.pi.shortcuts[0].actions[0].kind)

    def dump_pdk_info(self, pdk_info) -> str:
        path = os.path.abspath('ihp-sg13g2.json')
        pdk_info.write_json(path)
        print(f"Dumped example PDK Info file to {path}")
        return path
        
    def test_validate_expectations(self):
        self.check_pdk_info(self.pi)
        
    def test_write_and_read_back_in(self):
        path = self.dump_pdk_info(self.pi)
        
        obtained = PDKInfo.read_json(path)
        self.check_pdk_info(obtained)
        
    def test_parse_packaged_pdk_infos(self):
        script_dir = Path(__file__).resolve().parent
        f = PDKInfoFactory(search_path=[script_dir / '..' / 'pdks'])
        for pi in f._pdk_infos_by_tech_name.values():
            json.dump(asdict(pi), sys.stdout, indent=4)

#--------------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
