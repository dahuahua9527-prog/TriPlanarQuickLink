# RsMat Clean

Version: `1.2.4`  
Plugin ID: `1069687`  
Compatibility: Cinema 4D 2024–2026

## Short Description

RsMat Clean removes material nodes that are not used by the final material output. It supports Cinema 4D node materials, Redshift, and classic Octane material nodes.

The plugin traces connections upstream from each material output. Nodes that can reach an output are preserved. Isolated nodes, detached chains, and other nodes that cannot reach an output are listed for removal. Missing textures, disabled nodes, and zero-valued parameters do not trigger deletion by themselves.

## Installation

1. Extract the release ZIP.
2. Copy the complete `RsMatClean` folder into Cinema 4D's `plugins` directory.
3. Fully quit and restart Cinema 4D.
4. Search for `RsMat Clean` in the Command Manager. Run it directly or add it to a toolbar.

The plugin automatically uses Chinese or English according to the Cinema 4D interface language.

## Usage

1. Back up the current `.c4d` document.
2. Choose the processing scope in the Material Manager:
   - One selected material: processes only that material.
   - Multiple selected materials: processes all selected materials.
   - No selected materials: processes every material in the active document.
3. Run `RsMat Clean`.
4. Review the candidate list in the Cinema 4D console.
5. Confirm the dialog to delete the listed nodes.

## Undo and Notes

- Cinema 4D Undo is supported. Processing multiple material graphs may require several `Ctrl+Z` operations.
- Connected Surface, Displacement, Volume, and other output branches are preserved.
- Graphs that cannot be read safely or are read-only are skipped.
- When first using the plugin with a Redshift or Octane project, review the preview on a project copy before confirming deletion.

