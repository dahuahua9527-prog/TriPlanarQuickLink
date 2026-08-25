"""TriPlanar Quick Link - Cinema 4D 2024-2026 command plugin entry point."""

import os
import sys

import c4d


PLUGIN_DIRECTORY = os.path.dirname(__file__)
if PLUGIN_DIRECTORY not in sys.path:
    sys.path.insert(0, PLUGIN_DIRECTORY)

import triplanar_core as core


PLUGIN_ID = 1069296

IDS_PLUGIN_NAME = 10000
IDS_PLUGIN_HELP = 10001
IDS_CONNECT_SCALE = 10002
IDS_CONNECT_OFFSET = 10003
IDS_CONNECT_ROTATION = 10004
IDS_CONNECT_BLEND_AMOUNT = 10005
IDS_DISCONNECT_SCALE = 10006
IDS_DISCONNECT_OFFSET = 10007
IDS_DISCONNECT_ROTATION = 10008
IDS_DISCONNECT_BLEND_AMOUNT = 10009
IDS_ERROR_PREFIX = 10010
IDS_ERROR_SELECT_ONE = 10011
IDS_ERROR_ACTIVE_MATERIAL = 10012
IDS_ERROR_NOT_REDSHIFT = 10013
IDS_ERROR_NO_TARGETS = 10014
IDS_MIX_ROUND_CORNERS = 10015
IDS_ERROR_SELECT_ONE_BUMP = 10016
IDS_ERROR_BUMP_NOT_DIRECTLY_CONNECTED = 10017
IDS_ERROR_BUMP_MIX_PORTS_UNAVAILABLE = 10018
IDS_ERROR_CREATE_BUMP_MIXER = 10019
IDS_ERROR_CYCLIC_CONNECTION = 10023
IDS_DISCONNECT_ALL = 10025

CONNECT_STRING_IDS = (
    IDS_CONNECT_SCALE,
    IDS_CONNECT_OFFSET,
    IDS_CONNECT_ROTATION,
    IDS_CONNECT_BLEND_AMOUNT,
)
DISCONNECT_STRING_IDS = (
    IDS_DISCONNECT_SCALE,
    IDS_DISCONNECT_OFFSET,
    IDS_DISCONNECT_ROTATION,
    IDS_DISCONNECT_BLEND_AMOUNT,
    IDS_DISCONNECT_ALL,
)
ERROR_STRING_IDS = {
    "select_one": IDS_ERROR_SELECT_ONE,
    "active_material": IDS_ERROR_ACTIVE_MATERIAL,
    "not_redshift": IDS_ERROR_NOT_REDSHIFT,
    "no_targets": IDS_ERROR_NO_TARGETS,
    "select_one_bump": IDS_ERROR_SELECT_ONE_BUMP,
    "bump_not_directly_connected": IDS_ERROR_BUMP_NOT_DIRECTLY_CONNECTED,
    "bump_mix_ports_unavailable": IDS_ERROR_BUMP_MIX_PORTS_UNAVAILABLE,
    "create_bump_mixer": IDS_ERROR_CREATE_BUMP_MIXER,
    "cyclic_connection": IDS_ERROR_CYCLIC_CONNECTION,
}


def load_string(symbol_id):
    return c4d.plugins.GeLoadString(symbol_id)


def load_icon():
    bitmap = c4d.bitmaps.BaseBitmap()
    result = bitmap.InitWith(os.path.join(PLUGIN_DIRECTORY, "res", "icon.png"))
    status = result[0] if isinstance(result, tuple) else result
    return bitmap if status == c4d.IMAGERESULT_OK else None


def build_popup_menu(base_id):
    menu = c4d.BaseContainer()
    for index, symbol_id in enumerate(CONNECT_STRING_IDS):
        menu.InsData(base_id + index, load_string(symbol_id))
    menu.InsData(0, "")
    for index, symbol_id in enumerate(DISCONNECT_STRING_IDS):
        menu.InsData(base_id + 10 + index, load_string(symbol_id))
    menu.InsData(0, "")
    menu.InsData(base_id + 20, load_string(IDS_MIX_ROUND_CORNERS))
    return menu


class TriPlanarQuickLinkCommand(c4d.plugins.CommandData):
    def GetScriptName(self):
        return "TriPlanarQuickLink"

    def Execute(self, document):
        try:
            graph = core.get_active_graph()
            selected = core.get_selected_nodes(graph)
            base_id = c4d.FIRST_POPUP_ID
            actions = core.build_menu_actions(base_id)
            command_id = c4d.gui.ShowPopupDialog(
                cd=None,
                bc=build_popup_menu(base_id),
                x=c4d.MOUSEPOS,
                y=c4d.MOUSEPOS,
                flags=c4d.POPUP_RIGHT)
            if command_id == 0:
                return True

            action = actions.get(command_id)
            if action is None:
                return True
            operation, target_key = action
            if operation == "mix_round_corners":
                bump_node = core.validate_bump_selection(selected)
                core.execute_bump_round_corners_mix(graph, bump_node)
            elif operation == "disconnect_all":
                source = core.validate_single_source(selected)
                core.execute_disconnect_all_properties(graph, source)
            else:
                source = core.validate_single_source(selected)
                core.execute_action(graph, source, operation, target_key)
        except core.QuickLinkError as error:
            c4d.gui.MessageDialog(load_string(ERROR_STRING_IDS[error.code]))
        except Exception as error:
            c4d.gui.MessageDialog(f"{load_string(IDS_ERROR_PREFIX)}\n{error}")
        return True


if __name__ == "__main__":
    c4d.plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str=load_string(IDS_PLUGIN_NAME),
        info=0,
        icon=load_icon(),
        help=load_string(IDS_PLUGIN_HELP),
        dat=TriPlanarQuickLinkCommand())
