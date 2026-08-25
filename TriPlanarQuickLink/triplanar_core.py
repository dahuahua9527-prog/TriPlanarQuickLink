"""Language-neutral core logic for the Cinema 4D Redshift plugin."""

try:
    import c4d
    import maxon
except ImportError:  # Allow pure logic tests outside Cinema 4D.
    c4d = None
    maxon = None


REDSHIFT_NODE_SPACE = "com.redshift3d.redshift4c4d.class.nodespace"
TRIPLANAR_ID = "com.redshift3d.redshift4c4d.nodes.core.triplanar"
BUMP_MAP_ID = "com.redshift3d.redshift4c4d.nodes.core.bumpmap"
ROUND_CORNERS_ID = "com.redshift3d.redshift4c4d.nodes.core.roundcorners"
BUMP_BLENDER_ID = "com.redshift3d.redshift4c4d.nodes.core.bumpblender"
STANDARD_MATERIAL_ID = (
    "com.redshift3d.redshift4c4d.nodes.core.standardmaterial")

TARGET_PROPERTIES = (
    ("scale", ("scale",)),
    ("offset", ("offset",)),
    ("rotation", ("rotation",)),
    ("blend_amount", ("blendamount", "blend")),
)


class QuickLinkError(RuntimeError):
    """Expected user-facing error represented by a stable language-free code."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def set_port_value(port, value):
    setter = getattr(port, "SetPortValue", None)
    if callable(setter):
        setter(value)
        return
    setter = getattr(port, "SetDefaultValue", None)
    if callable(setter):
        setter(value)
        return
    raise QuickLinkError("bump_mix_ports_unavailable")


def build_menu_actions(base_id):
    actions = {}
    for index, (target_key, _) in enumerate(TARGET_PROPERTIES):
        actions[base_id + index] = ("connect", target_key)
        actions[base_id + 10 + index] = ("disconnect", target_key)
    actions[base_id + 14] = ("disconnect_all", None)
    actions[base_id + 20] = ("mix_round_corners", None)
    return actions


def validate_single_source(selected):
    if len(selected) != 1:
        raise QuickLinkError("select_one")
    return selected[0]


def validate_bump_selection(selected):
    if len(selected) != 1 or not is_type(selected[0], BUMP_MAP_ID):
        raise QuickLinkError("select_one_bump")
    return selected[0]


def exclude_source_from_targets(source, targets):
    return [target for target in targets if target != source]


def is_type(node, identifier):
    instance_type = str(node.GetId()).split("@", 1)[0]
    if instance_type == identifier.rsplit(".", 1)[-1]:
        return True

    if maxon is not None:
        nodes_namespace = getattr(maxon, "nodes", None)
        asset_attribute = getattr(nodes_namespace, "AssetId", None)
        if asset_attribute is None:
            return False
        asset_value = node.GetValue(asset_attribute)
        try:
            asset_id = str(asset_value[0])
        except (IndexError, TypeError):
            asset_id = str(asset_value)
        return asset_id == identifier
    return False


def walk_ports(port):
    yield port
    for child in port.GetChildren():
        yield from walk_ports(child)


def iter_ports_of_kind(root, kind):
    for port in walk_ports(root):
        if port.GetKind() == kind:
            yield port


def get_graph_root(graph):
    getter = getattr(graph, "GetViewRoot", None)
    if callable(getter):
        return getter()
    return graph.GetRoot()


def find_all_nodes(graph):
    return get_graph_root(graph).GetInnerNodes(
        maxon.NODE_KIND.NODE, False)


def find_all_triplanars(graph):
    return [node for node in find_all_nodes(graph)
            if is_type(node, TRIPLANAR_ID)]


def _normalized_port_id(port):
    identifier = str(port.GetId()).rsplit(".", 1)[-1]
    return identifier.replace("_", "").replace("-", "").lower()


def find_target_input(node, target_key):
    aliases = next(
        item[1] for item in TARGET_PROPERTIES if item[0] == target_key)
    matches = [
        port for port in walk_ports(node.GetInputs())
        if _normalized_port_id(port) in aliases
    ]
    return matches[0] if len(matches) == 1 else None


def ports_are_connectable(graph, source, target):
    checker = getattr(source, "IsConnectable", None)
    if callable(checker):
        return checker(target)
    checker = getattr(graph, "IsConnectable", None)
    if callable(checker):
        return checker(source, target)
    return True


def find_compatible_output(graph, source_node, target):
    for port in iter_ports_of_kind(
            source_node.GetOutputs(), maxon.NODE_KIND.OUTPORT):
        if ports_are_connectable(graph, port, target):
            return port
    return None


def find_connection_from_source(source_node, target):
    source_outputs = list(iter_ports_of_kind(
        source_node.GetOutputs(), maxon.NODE_KIND.OUTPORT))
    connections = target.GetConnections(maxon.PORT_DIR.INPUT)
    for connected_port, _ in connections:
        if any(connected_port == source_port for source_port in source_outputs):
            return connected_port
    return None


def get_active_graph():
    document = c4d.documents.GetActiveDocument()
    material = document.GetActiveMaterial()
    if material is None:
        raise QuickLinkError("active_material")

    node_material = material.GetNodeMaterialReference()
    node_space = maxon.Id(REDSHIFT_NODE_SPACE)
    if node_material is None or not node_material.HasSpace(node_space):
        raise QuickLinkError("not_redshift")
    return node_material.GetGraph(node_space)


def get_selected_source(graph):
    return validate_single_source(get_selected_nodes(graph))


def get_selected_nodes(graph):
    return maxon.GraphModelHelper.GetSelectedNodes(
        graph, maxon.NODE_KIND.NODE)


def _find_unique_port(root, aliases):
    matches = [
        port for port in walk_ports(root)
        if _normalized_port_id(port) in aliases
    ]
    return matches[0] if len(matches) == 1 else None


def _node_for_port(port):
    return port.GetAncestor(maxon.NODE_KIND.NODE)


def _existing_node_edges(graph):
    edges = []
    for target_node in find_all_nodes(graph):
        inputs = target_node.GetInputs()
        if inputs is None:
            continue
        for target_port in iter_ports_of_kind(
                inputs, maxon.NODE_KIND.INPORT):
            for source_port, _ in target_port.GetConnections(
                    maxon.PORT_DIR.INPUT):
                edges.append((_node_for_port(source_port), target_node))
    return edges


def _node_reaches(edges, start, destination):
    pending = [start]
    visited = []
    while pending:
        current = pending.pop()
        if current == destination:
            return True
        if any(current == item for item in visited):
            continue
        visited.append(current)
        pending.extend(
            target for source, target in edges if source == current)
    return False


def _find_direct_material_link(graph, bump_node):
    links = []
    for node in find_all_nodes(graph):
        if not is_type(node, STANDARD_MATERIAL_ID):
            continue
        target_port = _find_unique_port(node.GetInputs(), ("bumpinput",))
        if target_port is None:
            continue
        source_port = find_connection_from_source(bump_node, target_port)
        if source_port is not None:
            links.append((source_port, target_port, node))
    if len(links) != 1:
        raise QuickLinkError("bump_not_directly_connected")
    return links[0]


def _mixer_feeds_standard_material(graph, mixer):
    for node in find_all_nodes(graph):
        if not is_type(node, STANDARD_MATERIAL_ID):
            continue
        target = _find_unique_port(node.GetInputs(), ("bumpinput",))
        if target is not None and find_connection_from_source(mixer, target):
            return True
    return False


def _node_receives_type(node, node_type, input_aliases):
    target = _find_unique_port(node.GetInputs(), input_aliases)
    if target is None:
        return False
    for source_port, _ in target.GetConnections(maxon.PORT_DIR.INPUT):
        if is_type(_node_for_port(source_port), node_type):
            return True
    return False


def _node_receives_from(node, source_node, input_aliases):
    target = _find_unique_port(node.GetInputs(), input_aliases)
    if target is None:
        return False
    return find_connection_from_source(source_node, target) is not None


def has_existing_bump_round_corners_mix(graph, bump_node):
    for mixer in find_all_nodes(graph):
        if not is_type(mixer, BUMP_BLENDER_ID):
            continue
        if not _node_receives_from(
                mixer, bump_node, ("baseinput", "input")):
            continue
        if not _node_receives_type(
                mixer, ROUND_CORNERS_ID, ("bumpinput0", "bumpinput")):
            continue
        if _mixer_feeds_standard_material(graph, mixer):
            return True
    return False


def execute_bump_round_corners_mix(graph, bump_node):
    if has_existing_bump_round_corners_mix(graph, bump_node):
        return False

    bump_output, material_input, _ = _find_direct_material_link(
        graph, bump_node)

    try:
        with graph.BeginTransaction() as transaction:
            round_corners_node = graph.AddChild(
                maxon.Id(), maxon.Id(ROUND_CORNERS_ID),
                maxon.DataDictionary())
            mixer = graph.AddChild(
                maxon.Id(), maxon.Id(BUMP_BLENDER_ID), maxon.DataDictionary())
            radius_input = _find_unique_port(
                round_corners_node.GetInputs(), ("radius",))
            base_input = _find_unique_port(
                mixer.GetInputs(), ("baseinput", "input"))
            round_input = _find_unique_port(
                mixer.GetInputs(), ("bumpinput0", "bumpinput"))
            weight_input = _find_unique_port(
                mixer.GetInputs(), ("bumpweight0", "blendweight"))
            mixer_output = find_compatible_output(graph, mixer, material_input)
            round_output = (
                find_compatible_output(graph, round_corners_node, round_input)
                if round_input is not None else None)

            if any(item is None for item in (
                    radius_input, base_input, round_input, weight_input,
                    mixer_output, round_output)):
                raise QuickLinkError("bump_mix_ports_unavailable")
            if not ports_are_connectable(
                    graph, bump_output, base_input):
                raise QuickLinkError("bump_mix_ports_unavailable")

            set_port_value(radius_input, 0.1)
            set_port_value(weight_input, 0.5)
            bump_output.Connect(base_input)
            round_output.Connect(round_input)
            maxon.GraphModelHelper.RemoveConnection(
                bump_output, material_input)
            mixer_output.Connect(material_input)
            transaction.Commit()
    except QuickLinkError:
        raise
    except Exception as error:
        raise QuickLinkError("create_bump_mixer") from error

    c4d.EventAdd()
    return True


def execute_disconnect_all_properties(graph, source):
    targets = exclude_source_from_targets(source, find_all_triplanars(graph))
    if not targets:
        raise QuickLinkError("no_targets")

    ready = []
    occupied_or_unmatched = 0
    incompatible = 0

    for node in targets:
        for target_key, _ in TARGET_PROPERTIES:
            target = find_target_input(node, target_key)
            if target is None:
                incompatible += 1
                continue

            source_port = find_connection_from_source(source, target)
            if source_port is None:
                occupied_or_unmatched += 1
                continue
            ready.append((source_port, target))

    if ready:
        with graph.BeginTransaction() as transaction:
            for source_port, target in ready:
                maxon.GraphModelHelper.RemoveConnection(source_port, target)
            transaction.Commit()
        c4d.EventAdd()

    return {
        "success": len(ready),
        "skipped": occupied_or_unmatched,
        "incompatible": incompatible,
    }


def execute_action(graph, source, action, target_key):
    targets = exclude_source_from_targets(source, find_all_triplanars(graph))
    if not targets:
        raise QuickLinkError("no_targets")

    ready = []
    occupied_or_unmatched = 0
    incompatible = 0
    cyclic = 0
    edges = _existing_node_edges(graph) if action == "connect" else []

    for node in targets:
        target = find_target_input(node, target_key)
        if target is None:
            incompatible += 1
            continue

        if action == "connect":
            if target.GetConnections(maxon.PORT_DIR.INPUT):
                occupied_or_unmatched += 1
                continue
            if _node_reaches(edges, node, source):
                cyclic += 1
                continue
            source_port = find_compatible_output(graph, source, target)
            if source_port is None:
                incompatible += 1
                continue
        else:
            source_port = find_connection_from_source(source, target)
            if source_port is None:
                occupied_or_unmatched += 1
                continue
        ready.append((source_port, target))

    if not ready and cyclic:
        raise QuickLinkError("cyclic_connection")

    if ready:
        with graph.BeginTransaction() as transaction:
            for source_port, target in ready:
                if action == "connect":
                    source_port.Connect(target)
                else:
                    maxon.GraphModelHelper.RemoveConnection(source_port, target)
            transaction.Commit()
        c4d.EventAdd()

    return {
        "success": len(ready),
        "skipped": occupied_or_unmatched,
        "incompatible": incompatible + cyclic,
    }
