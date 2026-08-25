"""RsMat Clean - Cinema 4D 2024-2026 command plugin entry point."""

import os
import sys

import c4d


PLUGIN_ID = 1069687
PLUGIN_DIRECTORY = os.path.dirname(__file__)
CORE_DIRECTORY = PLUGIN_DIRECTORY
if not os.path.isfile(os.path.join(CORE_DIRECTORY, "unused_node_cleanup.py")):
    CORE_DIRECTORY = os.path.dirname(PLUGIN_DIRECTORY)
if CORE_DIRECTORY not in sys.path:
    sys.path.insert(0, CORE_DIRECTORY)

import unused_node_cleanup as core


def load_icon():
    bitmap = c4d.bitmaps.BaseBitmap()
    result = bitmap.InitWith(os.path.join(PLUGIN_DIRECTORY, "res", "icon.png"))
    status = result[0] if isinstance(result, tuple) else result
    return bitmap if status == c4d.IMAGERESULT_OK else None


class RsMatCleanCommand(c4d.plugins.CommandData):
    def GetScriptName(self):
        return "RsMatClean"

    def Execute(self, document):
        try:
            core.main(document)
        except Exception as error:
            c4d.gui.MessageDialog(
                "%s:\n%s" % (core.get_text(core.IDS_PLUGIN_NAME), error))
        return True


if __name__ == "__main__":
    c4d.plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str=core.get_text(core.IDS_PLUGIN_NAME),
        info=0,
        icon=load_icon(),
        help=core.get_text(core.IDS_PLUGIN_HELP),
        dat=RsMatCleanCommand(),
    )

