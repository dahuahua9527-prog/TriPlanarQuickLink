"""Cinema 4D 2024-2026 material unused-node cleaner.

Run this file from Cinema 4D's Script Manager. The script scans all selected
materials when there is a selection, or every material when none is selected.
It prints a preview, asks for confirmation, and removes only nodes that cannot
reach the material output.

Supported storage models:
    * Cinema 4D standard node materials (Maxon Nodes API)
    * Redshift node materials (Maxon Nodes API)
    * Octane classic node materials (BaseShader graph)

The graph algorithm is intentionally independent from Cinema 4D so it can be
tested with a normal Python interpreter.
"""

from __future__ import print_function

from collections import defaultdict

try:
    import c4d
    import maxon
except ImportError:  # Enables pure graph tests outside Cinema 4D.
    c4d = None
    maxon = None


SCRIPT_VERSION = "1.2.4"

IDS_PLUGIN_NAME = 10000
IDS_PLUGIN_HELP = 10001
IDS_SCOPE_SELECTED = 10002
IDS_SCOPE_ALL = 10003
IDS_UNNAMED_MATERIAL = 10004
IDS_UNNAMED_NODE = 10005
IDS_ERROR_GRAPH_EMPTY = 10006
IDS_ERROR_GRAPH_READ_ONLY = 10007
IDS_ERROR_OUTPUT_MISSING = 10008
IDS_ERROR_UNDO_START = 10009
IDS_REPORT_TITLE = 10010
IDS_REPORT_SUMMARY = 10011
IDS_REPORT_ITEM = 10012
IDS_REPORT_NONE = 10013
IDS_REPORT_ERRORS = 10014
IDS_ERROR_RUNTIME_ONLY = 10015
IDS_ERROR_NO_DOCUMENT = 10016
IDS_ERROR_NO_MATERIALS = 10017
IDS_NO_CANDIDATES = 10018
IDS_SKIPPED_COUNT = 10019
IDS_CONFIRM = 10020
IDS_CONFIRM_SKIPPED = 10021
IDS_CANCELED = 10022
IDS_DONE = 10023
IDS_DELETE_ERRORS = 10024
IDS_RESULT_FAILED = 10025

_TEXT_FALLBACKS = {
    IDS_PLUGIN_NAME: "RsMat Clean",
    IDS_PLUGIN_HELP: "Remove unused nodes from selected materials, or all materials when none are selected",
    IDS_SCOPE_SELECTED: "Selected materials",
    IDS_SCOPE_ALL: "All materials",
    IDS_UNNAMED_MATERIAL: "<Unnamed material>",
    IDS_UNNAMED_NODE: "<Unnamed node>",
    IDS_ERROR_GRAPH_EMPTY: "The node graph is empty",
    IDS_ERROR_GRAPH_READ_ONLY: "The node graph is read-only",
    IDS_ERROR_OUTPUT_MISSING: "The material output node could not be found",
    IDS_ERROR_UNDO_START: "Could not start the Cinema 4D undo record",
    IDS_REPORT_TITLE: "RsMat Clean v%s - Scan Preview",
    IDS_REPORT_SUMMARY: "Scope: %s; Materials: %d; Node graphs: %d; Candidates: %d",
    IDS_REPORT_ITEM: "%d. [%s] Material=%s | Node=%s | Type=%s",
    IDS_REPORT_NONE: "No nodes disconnected from the material output were found.",
    IDS_REPORT_ERRORS: "Skipped/errors (these items will not be deleted):",
    IDS_ERROR_RUNTIME_ONLY: "Run this file in Cinema 4D 2024-2026.",
    IDS_ERROR_NO_DOCUMENT: "No Cinema 4D document is open.",
    IDS_ERROR_NO_MATERIALS: "The current document contains no materials to process.",
    IDS_NO_CANDIDATES: "Scan complete. No unused nodes were found.",
    IDS_SKIPPED_COUNT: "\n\n%d item(s) were safely skipped. See the console for details.",
    IDS_CONFIRM: "Scope: %s\nFound %d node(s) disconnected from the material output.\n\nThe full list is in the console.\nDelete them? The operation supports Cinema 4D Undo.",
    IDS_CONFIRM_SKIPPED: "\n\n%d additional item(s) could not be safely classified and were skipped.",
    IDS_CANCELED: "Deletion canceled; the document was not modified.",
    IDS_DONE: "Cleanup complete: removed %d unused node(s).",
    IDS_DELETE_ERRORS: "Deletion errors:",
    IDS_RESULT_FAILED: "\n\n%d group(s) failed to delete. See the console for details.",
}

_TEXT_ZH_FALLBACKS = {
    IDS_PLUGIN_NAME: "RsMat Clean",
    IDS_PLUGIN_HELP: "清理已选材质中的未使用节点；没有选择材质时处理工程全部材质",
    IDS_SCOPE_SELECTED: "已选材质",
    IDS_SCOPE_ALL: "全部材质",
    IDS_UNNAMED_MATERIAL: "<未命名材质>",
    IDS_UNNAMED_NODE: "<未命名节点>",
    IDS_ERROR_GRAPH_EMPTY: "节点图为空",
    IDS_ERROR_GRAPH_READ_ONLY: "节点图为只读状态",
    IDS_ERROR_OUTPUT_MISSING: "找不到材质最终输出节点",
    IDS_ERROR_UNDO_START: "无法开启 Cinema 4D 撤销记录",
    IDS_REPORT_TITLE: "RsMat Clean v%s - 扫描预览",
    IDS_REPORT_SUMMARY: "扫描范围：%s；材质数量：%d；节点图数量：%d；待删除节点：%d",
    IDS_REPORT_ITEM: "%d. [%s] 材质=%s | 节点=%s | 类型=%s",
    IDS_REPORT_NONE: "没有发现未接入最终材质输出的节点。",
    IDS_REPORT_ERRORS: "跳过/错误（不会删除这些项目）：",
    IDS_ERROR_RUNTIME_ONLY: "请在 Cinema 4D 2024-2026 中运行此插件。",
    IDS_ERROR_NO_DOCUMENT: "当前没有打开的 Cinema 4D 工程。",
    IDS_ERROR_NO_MATERIALS: "当前工程中没有可处理的材质球。",
    IDS_NO_CANDIDATES: "扫描完成，没有发现可清理的未使用节点。",
    IDS_SKIPPED_COUNT: "\n\n有 %d 项被安全跳过，详情见控制台。",
    IDS_CONFIRM: "扫描范围：%s\n发现 %d 个未接入材质最终输出的节点。\n\n完整清单已输出到控制台。\n是否确认删除？删除后可使用 Cinema 4D 撤销。",
    IDS_CONFIRM_SKIPPED: "\n\n另有 %d 项因无法安全判断而跳过。",
    IDS_CANCELED: "用户取消删除；工程未发生修改。",
    IDS_DONE: "清理完成：已删除 %d 个未使用节点。",
    IDS_DELETE_ERRORS: "删除阶段错误：",
    IDS_RESULT_FAILED: "\n\n有 %d 组删除失败，详情见控制台。",
}


def _get_ui_language_extension(api=None):
    """Return the active Cinema 4D language extension, for example zh-CN."""
    api = c4d if api is None else api
    if api is None:
        return ""

    index = 0
    try:
        while True:
            language = api.GeGetLanguage(index)
            if language is None:
                return ""
            if language.get("default_language"):
                return str(language.get("extensions", ""))
            index += 1
    except Exception:
        return ""


def resolve_text(symbol_id, language_extension, resource_value="", *values):
    """Resolve one message, forcing Chinese fallback for a Chinese UI."""
    is_chinese = str(language_extension).lower().startswith("zh")
    if is_chinese:
        value = _TEXT_ZH_FALLBACKS[symbol_id]
    else:
        value = resource_value or _TEXT_FALLBACKS[symbol_id]
    return value % values if values else value


def get_text(symbol_id, *values):
    """Load a localized string with language-aware built-in fallbacks."""
    resource_value = ""
    if c4d is not None:
        try:
            resource_value = c4d.plugins.GeLoadString(symbol_id)
        except Exception:
            resource_value = ""
    return resolve_text(
        symbol_id,
        _get_ui_language_extension(),
        resource_value,
        *values
    )

STANDARD_NODE_SPACE = "net.maxon.nodespace.standard"
REDSHIFT_NODE_SPACE = "com.redshift3d.redshift4c4d.class.nodespace"
NODE_SPACES = (
    ("C4D Nodes", STANDARD_NODE_SPACE),
    ("Redshift", REDSHIFT_NODE_SPACE),
)

# Stable Octane material plugin IDs used by the C4D Octane node editor.
OCTANE_MATERIAL_IDS = frozenset((
    1029501,  # Octane material / universal material
    1058763,  # Standard Surface
    1040075,  # Composite Material
    1029622,  # Mix Material
    1029623,  # Portal Material
    1056989,  # Clipping Material
    1057003,  # Shadow Catcher Material
    1054119,  # Hair Material
))


class CleanupItem(object):
    """One preview row for a node that is safe to remove."""

    def __init__(self, material_name, renderer, node_name, node_type):
        self.material_name = material_name
        self.renderer = renderer
        self.node_name = node_name
        self.node_type = node_type


class ScanGroup(object):
    """Deletion candidates that share one graph transaction."""

    def __init__(self, adapter, material, renderer, graph, nodes):
        self.adapter = adapter
        self.material = material
        self.renderer = renderer
        self.graph = graph
        self.nodes = list(nodes)


class ScanReport(object):
    """Scan result for the active material."""

    def __init__(self):
        self.groups = []
        self.items = []
        self.errors = []
        self.material_count = 0
        self.graph_count = 0
        self.scope = ""


def compute_reachable_keys(all_keys, edges, output_keys):
    """Return nodes which can reach at least one output.

    Args:
        all_keys: Iterable containing every node key.
        edges: Iterable of ``(source, destination)`` node connections.
        output_keys: Iterable containing all material-output node keys.

    Connections are stored in render direction (source -> destination), while
    traversal starts at each output and walks upstream.
    """
    known = set(all_keys)
    incoming = defaultdict(set)
    for source, destination in edges:
        if source in known and destination in known:
            incoming[destination].add(source)

    reachable = set()
    pending = [key for key in output_keys if key in known]
    while pending:
        key = pending.pop()
        if key in reachable:
            continue
        reachable.add(key)
        pending.extend(incoming.get(key, ()))
    return reachable


def compute_unused_keys(all_keys, edges, output_keys):
    """Return all nodes that have no connection path to a material output."""
    all_keys = set(all_keys)
    return all_keys - compute_reachable_keys(all_keys, edges, output_keys)


def _is_valid_graph_node(node):
    if node is None:
        return False
    checker = getattr(node, "IsValid", None)
    if callable(checker):
        try:
            return bool(checker())
        except Exception:
            return False
    return True


def _graph_node_key(node):
    return str(node.GetPath())


def _get_graph_root(graph):
    getter = getattr(graph, "GetViewRoot", None)
    if callable(getter):
        return getter()
    return graph.GetRoot()


def _find_all_graph_nodes(graph):
    root = _get_graph_root(graph)
    nodes = root.GetInnerNodes(maxon.NODE_KIND.NODE, False)
    return [node for node in nodes if _is_valid_graph_node(node)]


def _walk_graph_ports(root):
    if not _is_valid_graph_node(root):
        return
    yield root
    for child in root.GetChildren():
        for port in _walk_graph_ports(child):
            yield port


def _input_connections(port):
    """Get incoming connections with a 2024-2026 compatible fallback."""
    try:
        return port.GetConnections(
            maxon.PORT_DIR.INPUT,
            None,
            maxon.Wires.All(),
            maxon.WIRE_MODE.ALL,
        )
    except (AttributeError, TypeError):
        return port.GetConnections(maxon.PORT_DIR.INPUT)


def _collect_graph_edges(nodes):
    keys = set(_graph_node_key(node) for node in nodes)
    edges = set()
    for target_node in nodes:
        target_key = _graph_node_key(target_node)
        inputs = target_node.GetInputs()
        if not _is_valid_graph_node(inputs):
            continue
        for input_port in _walk_graph_ports(inputs):
            if input_port.GetKind() != maxon.NODE_KIND.INPORT:
                continue
            for source_port, _ in _input_connections(input_port):
                source_node = source_port.GetAncestor(maxon.NODE_KIND.NODE)
                if not _is_valid_graph_node(source_node):
                    continue
                source_key = _graph_node_key(source_node)
                if source_key in keys:
                    edges.add((source_key, target_key))
    return edges


def _graph_node_asset_id(node):
    nodes_namespace = getattr(maxon, "nodes", None)
    attribute = getattr(nodes_namespace, "AssetId", None)
    if attribute is not None:
        try:
            value = node.GetValue(attribute)
            if isinstance(value, (tuple, list)) and value:
                return str(value[0])
            if value is not None:
                text = str(value)
                if text:
                    return text
        except Exception:
            pass
    return str(node.GetId())


def _graph_node_name(node):
    node_namespace = getattr(maxon, "NODE", None)
    base_namespace = getattr(node_namespace, "BASE", None)
    name_attribute = getattr(base_namespace, "NAME", None)
    if name_attribute is not None:
        try:
            value = node.GetValue(name_attribute)
            text = str(value).strip()
            if text and text.lower() != "none":
                return text
        except Exception:
            pass
    return str(node.GetId())


def _graph_path_depth(node):
    path = node.GetPath()
    for method_name in ("GetNodeDepth", "GetCount"):
        method = getattr(path, method_name, None)
        if callable(method):
            try:
                return int(method())
            except Exception:
                pass
    return str(path).count(">")


def _scan_maxon_graph(material, node_material, renderer, space_id):
    space = maxon.Id(space_id)
    if not node_material.HasSpace(space):
        return None

    graph = node_material.GetGraph(space)
    if graph is None or graph.IsNullValue():
        raise RuntimeError(get_text(IDS_ERROR_GRAPH_EMPTY))
    if graph.IsReadOnly():
        raise RuntimeError(get_text(IDS_ERROR_GRAPH_READ_ONLY))

    nodes = _find_all_graph_nodes(graph)
    if not nodes:
        return ScanGroup("maxon", material, renderer, graph, [])

    output_path = node_material.GetMaterialNodePath(space)
    output_node = graph.GetNode(output_path)
    if not _is_valid_graph_node(output_node):
        raise RuntimeError(get_text(IDS_ERROR_OUTPUT_MISSING))

    output_key = _graph_node_key(output_node)
    node_by_key = {_graph_node_key(node): node for node in nodes}
    if output_key not in node_by_key:
        nodes.append(output_node)
        node_by_key[output_key] = output_node

    edges = _collect_graph_edges(nodes)
    unused_keys = compute_unused_keys(node_by_key, edges, (output_key,))
    candidates = [node_by_key[key] for key in unused_keys]
    candidates.sort(key=_graph_path_depth, reverse=True)
    return ScanGroup("maxon", material, renderer, graph, candidates)


def _iter_shader_tree(first_shader):
    """Yield every BaseShader in sibling/child hierarchy order."""
    shader = first_shader
    while shader is not None:
        yield shader
        child = shader.GetDown()
        if child is not None:
            for nested in _iter_shader_tree(child):
                yield nested
        shader = shader.GetNext()


def _classic_node_key(node):
    finder = getattr(node, "FindUniqueID", None)
    creator_id = getattr(c4d, "MAXON_CREATOR_ID", None)
    if callable(finder) and creator_id is not None:
        try:
            value = finder(creator_id)
            if value:
                return bytes(value).hex()
        except Exception:
            pass
    # BaseList2D wrappers compare by their underlying C4D atom. repr/str also
    # contains that identity and is stable for the duration of one scan.
    return str(node)


def _container_linked_shaders(owner, known_keys):
    result = []
    container = owner.GetDataInstance()
    if container is None:
        return result
    for index in range(len(container)):
        key = container.GetIndexId(index)
        try:
            value = container[key]
        except Exception:
            continue
        if isinstance(value, c4d.BaseShader):
            value_key = _classic_node_key(value)
            if value_key in known_keys:
                result.append(value_key)
    return result


def _description_linked_shaders(owner, known_keys):
    """Fallback for dynamic links not exposed in the raw BaseContainer."""
    result = []
    try:
        description = owner.GetDescription(c4d.DESCFLAGS_DESC_NONE)
    except Exception:
        return result

    for _, desc_id, _ in description:
        is_link = False
        try:
            for level_index in range(desc_id.GetDepth()):
                if desc_id[level_index].dtype == c4d.DTYPE_BASELISTLINK:
                    is_link = True
                    break
        except Exception:
            continue
        if not is_link:
            continue
        try:
            value = owner[desc_id]
        except Exception:
            continue
        if isinstance(value, c4d.BaseShader):
            value_key = _classic_node_key(value)
            if value_key in known_keys:
                result.append(value_key)
    return result


def _shader_depth(shader):
    depth = 0
    parent = shader.GetUp()
    while isinstance(parent, c4d.BaseShader):
        depth += 1
        parent = parent.GetUp()
    return depth


def _scan_octane_graph(material):
    if int(material.GetType()) not in OCTANE_MATERIAL_IDS:
        return None
    first_shader = material.GetFirstShader()
    if first_shader is None:
        return ScanGroup("octane", material, "Octane", None, [])

    shaders = list(_iter_shader_tree(first_shader))
    node_by_key = {_classic_node_key(shader): shader for shader in shaders}
    known_keys = set(node_by_key)
    edges = set()

    owners = [material] + shaders
    for owner in owners:
        owner_key = "__material_output__" if owner is material else _classic_node_key(owner)
        linked = set(_container_linked_shaders(owner, known_keys))
        linked.update(_description_linked_shaders(owner, known_keys))
        for source_key in linked:
            edges.add((source_key, owner_key))

        # A connected compound/layer shader owns its child shaders. Preserve
        # those children even when the renderer hides their dynamic links.
        if owner is not material:
            child = owner.GetDown()
            while isinstance(child, c4d.BaseShader):
                child_key = _classic_node_key(child)
                if child_key in known_keys:
                    edges.add((child_key, owner_key))
                child = child.GetNext()

    all_keys = set(known_keys)
    all_keys.add("__material_output__")
    unused_keys = compute_unused_keys(
        all_keys, edges, ("__material_output__",))
    unused_keys.discard("__material_output__")
    candidates = [node_by_key[key] for key in unused_keys]
    candidates.sort(key=_shader_depth, reverse=True)
    return ScanGroup("octane", material, "Octane", None, candidates)


def _append_group(report, group):
    if group is None:
        return
    report.graph_count += 1
    if not group.nodes:
        return
    report.groups.append(group)
    material_name = group.material.GetName() or get_text(IDS_UNNAMED_MATERIAL)
    for node in group.nodes:
        if group.adapter == "maxon":
            node_name = _graph_node_name(node)
            node_type = _graph_node_asset_id(node)
        else:
            node_name = node.GetName() or get_text(IDS_UNNAMED_NODE)
            node_type = str(node.GetType())
        report.items.append(CleanupItem(
            material_name, group.renderer, node_name, node_type))


def _scan_material(report, material):
    material_name = material.GetName() or get_text(IDS_UNNAMED_MATERIAL)

    try:
        node_material = material.GetNodeMaterialReference()
        if node_material is not None:
            for renderer, space_id in NODE_SPACES:
                try:
                    group = _scan_maxon_graph(
                        material, node_material, renderer, space_id)
                    _append_group(report, group)
                except Exception as error:
                    report.errors.append(
                        "%s / %s：%s" % (
                            material_name, renderer, error))
    except Exception as error:
        report.errors.append(
            "%s / Nodes API：%s" % (material_name, error))

    try:
        _append_group(report, _scan_octane_graph(material))
    except Exception as error:
        report.errors.append(
            "%s / Octane：%s" % (material_name, error))


def scan_document(document):
    report = ScanReport()
    selected_materials = document.GetActiveMaterials()
    if selected_materials:
        materials = selected_materials
        report.scope = "selected"
    else:
        materials = document.GetMaterials()
        report.scope = "all"

    report.material_count = len(materials)
    for material in materials:
        _scan_material(report, material)

    return report


def print_report(report):
    scope = get_text(
        IDS_SCOPE_SELECTED if report.scope == "selected" else IDS_SCOPE_ALL)
    print("\n" + "=" * 72)
    print(get_text(IDS_REPORT_TITLE, SCRIPT_VERSION))
    print(get_text(
        IDS_REPORT_SUMMARY,
        scope,
        report.material_count,
        report.graph_count,
        len(report.items),
    ))
    print("-" * 72)

    if report.items:
        for index, item in enumerate(report.items, 1):
            print(get_text(IDS_REPORT_ITEM,
                index,
                item.renderer,
                item.material_name,
                item.node_name,
                item.node_type,
            ))
    else:
        print(get_text(IDS_REPORT_NONE))

    if report.errors:
        print("-" * 72)
        print(get_text(IDS_REPORT_ERRORS))
        for error in report.errors:
            print("- " + error)
    print("=" * 72 + "\n")


def _remove_maxon_group(group):
    removed = 0
    with group.graph.BeginTransaction() as transaction:
        for node in group.nodes:
            if not _is_valid_graph_node(node):
                continue
            node.Remove()
            removed += 1
        transaction.Commit()
    return removed


def _remove_octane_groups(document, groups):
    removed = 0
    if not groups:
        return removed

    if not document.StartUndo():
        raise RuntimeError(get_text(IDS_ERROR_UNDO_START))
    try:
        for group in groups:
            for shader in group.nodes:
                document.AddUndo(c4d.UNDOTYPE_DELETEOBJ, shader)
                shader.Remove()
                removed += 1
            try:
                group.material.Message(c4d.MSG_UPDATE)
                group.material.Update(True, True)
            except Exception:
                pass
    finally:
        document.EndUndo()
    return removed


def remove_report(document, report):
    removed = 0
    errors = []
    octane_groups = []

    for group in report.groups:
        if group.adapter == "octane":
            octane_groups.append(group)
            continue
        try:
            removed += _remove_maxon_group(group)
        except Exception as error:
            errors.append("%s / %s：%s" % (
                group.material.GetName(), group.renderer, error))

    try:
        removed += _remove_octane_groups(document, octane_groups)
    except Exception as error:
        errors.append("Octane：%s" % error)

    c4d.EventAdd()
    return removed, errors


def main(document=None):
    if c4d is None or maxon is None:
        raise RuntimeError(get_text(IDS_ERROR_RUNTIME_ONLY))

    if document is None:
        document = c4d.documents.GetActiveDocument()
    if document is None:
        c4d.gui.MessageDialog(get_text(IDS_ERROR_NO_DOCUMENT))
        return

    report = scan_document(document)
    if report.material_count == 0:
        c4d.gui.MessageDialog(get_text(IDS_ERROR_NO_MATERIALS))
        return

    print_report(report)

    if not report.items:
        message = get_text(IDS_NO_CANDIDATES)
        if report.errors:
            message += get_text(IDS_SKIPPED_COUNT, len(report.errors))
        c4d.gui.MessageDialog(message)
        return

    scope = get_text(
        IDS_SCOPE_SELECTED if report.scope == "selected" else IDS_SCOPE_ALL)
    message = get_text(IDS_CONFIRM, scope, len(report.items))
    if report.errors:
        message += get_text(IDS_CONFIRM_SKIPPED, len(report.errors))

    if not c4d.gui.QuestionDialog(message):
        print(get_text(IDS_CANCELED))
        return

    removed, errors = remove_report(document, report)
    print(get_text(IDS_DONE, removed))
    if errors:
        print(get_text(IDS_DELETE_ERRORS))
        for error in errors:
            print("- " + error)

    result_message = get_text(IDS_DONE, removed)
    if errors:
        result_message += get_text(IDS_RESULT_FAILED, len(errors))
    c4d.gui.MessageDialog(result_message)


if __name__ == "__main__":
    main()

