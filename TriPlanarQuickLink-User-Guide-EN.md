# TriPlanar Quick Link

## Usage

1. Activate the Redshift node material you want to process.

2. Select exactly one source node in the Node Editor.

   1. You do not need to select any TriPlanar nodes. The plugin automatically scans all TriPlanar nodes in the active material.
   2. If the selected source is itself a TriPlanar node, it is excluded from the target list to prevent self-connection.

3. Press the shortcut assigned to “TriPlanar Quick Link.”

4. Choose the required action from the menu displayed at the mouse pointer.

   1. Choose “Connect · Scale / Offset / Rotation / Blend Amount” to connect the corresponding property.
   2. Choose “Disconnect · Scale / Offset / Rotation / Blend Amount” to precisely remove the corresponding connection.
   3. Choose “Disconnect All” to remove all four types of TriPlanar connections created by the selected source.

5. Successful operations do not display a completion dialog. An error message appears only when the requested operation cannot be performed.

## Feature Reference

### `Connect · Scale`

Connects a compatible output from the selected source node to every unoccupied Scale input on the TriPlanar nodes in the active material. Inputs that already have a connection are skipped and never overwritten.

### `Connect · Offset`

Connects the selected source node to every unoccupied Offset input on the TriPlanar nodes. Incompatible ports are skipped automatically.

### `Connect · Rotation`

Connects the selected source node to every unoccupied Rotation input on the TriPlanar nodes. The plugin checks the node relationships before connecting to prevent graph cycles.

### `Connect · Blend Amount`

Connects the selected source node to every unoccupied Blend Amount input on the TriPlanar nodes. Existing connections remain unchanged.

### `Disconnect · Property`

“Disconnect · Scale / Offset / Rotation / Blend Amount” removes only the corresponding connections created by the currently selected source node. Connections from other nodes are left unchanged.

### `Disconnect All`

Checks the Scale, Offset, Rotation, and Blend Amount inputs on all TriPlanar nodes and removes only the connections originating from the selected source node. Connections from all other sources remain unchanged.

### `Mix Round Corners`

Automatically adds a Round Corners node and a Bump Blender to a Bump Map connected directly to the Bump Input of an RS Standard Material. If an identical setup already exists, the operation is skipped without creating a duplicate structure.

## Using Mix Round Corners

1. Confirm that a Redshift Bump Map node is connected directly to the Bump Input of the active RS Standard Material.

2. Select only that Bump Map node.

3. Press the plugin shortcut and choose “Mix Round Corners.”

4. The plugin automatically performs the following operations:

   1. Creates a Round Corners node.
   2. Creates a Bump Blender node.
   3. Connects the original Bump Map to the Base Input of the Bump Blender.
   4. Connects the Round Corners node to `Bump Input 0`.
   5. Connects the Bump Blender output back to the material's Bump Input.

## Parameters

### `Corner Radius`

The Radius of the automatically created Round Corners node is fixed at `0.1`.

### `Blend Weight`

The automatically created Bump Blender sets `Bump Weight 0` to `0.5`, blending the original bump map with the Round Corners effect.
