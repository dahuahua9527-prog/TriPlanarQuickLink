三平面快速链接 - Cinema 4D 2024–2026 / Redshift
================================================

Plugin ID：1069296
命令名称：三平面快速链接

安装
----
1. 将整个 TriPlanarQuickLink 文件夹复制到 Cinema 4D 的 plugins 文件夹。
2. 完全退出并重新启动 Cinema 4D 2024、2025 或 2026。
3. 打开“窗口 > 自定义 > 命令管理器”。
4. 搜索“三平面快速链接”。
5. 为该命令设置所需快捷键并保存快捷键布局。

使用
----
1. 激活需要处理的 Redshift 节点材质。
2. 只选择一个任意源节点。
3. 按已配置的快捷键。
4. 在鼠标位置弹出的菜单中选择：
   - 连接 · 缩放 / 偏移 / 旋转 / 混合量
   - 取消 · 缩放 / 偏移 / 旋转 / 混合量
   - 取消所有

混合圆角
--------
1. 只选择一个直接连接到当前 RS 标准材质“凹凸贴图”端口的凹凸贴图节点。
2. 按相同快捷键并选择“混合圆角”。
3. 插件自动创建半径为 0.1 的圆角节点和凹凸混合器，将原凹凸接入基础输入、圆角接入凹凸输入，并将混合权重设为 0.5。
4. 相同混合结构已存在时静默跳过，不重复创建。

规则
----
- 自动处理当前材质中的全部三平面节点。
- “取消所有”一次检查缩放、偏移、旋转、混合量四个属性。
- 连接时，目标已有入线便跳过，不覆盖。
- 取消时，只移除当前源节点建立的对应连接。
- 源节点也为三平面时，会从目标列表排除，避免自连接。
- 所选源节点位于目标三平面下游时拒绝连接，避免形成节点循环；请选择三平面上游的源节点。
- 端口不兼容时直接跳过。
- 连接或取消成功后不弹出完成提示；只有操作无法执行时才显示错误提示。
- 同一插件文件夹兼容 C4D 2024.0–2026；旧版端口赋值 API 会自动回退。
- 不需要安装任何第三方 Python 依赖。

语言
----
- Cinema 4D 使用简体中文时，命令、菜单和错误提示自动显示中文。
- Cinema 4D 使用英文或其他语言时，自动使用英文资源。


TriPlanar Quick Link - Cinema 4D 2024–2026 / Redshift
======================================================

Plugin ID: 1069296
Command: TriPlanar Quick Link

Installation
------------
1. Copy the complete TriPlanarQuickLink folder into Cinema 4D's plugins folder.
2. Fully quit and restart Cinema 4D 2024, 2025, or 2026.
3. Open Window > Customization > Command Manager.
4. Search for "TriPlanar Quick Link".
5. Assign a shortcut to the command and save the shortcut layout.

Usage
-----
1. Activate the Redshift node material to process.
2. Select exactly one source node.
3. Press the assigned shortcut.
4. Choose Connect or Disconnect for Scale, Offset, Rotation, or Blend Amount
   from the menu shown at the mouse pointer, or choose "Disconnect All" to
   remove the selected source's connections from all four properties.

Mix Round Corners
-----------------
1. Select one Bump Map connected directly to the active RS Standard Material's
   Bump Input.
2. Press the same shortcut and choose "Mix Round Corners".
3. The plugin creates a Round Corners node with Radius 0.1 and a Bump Blender,
   connects the original bump as its base, connects Round Corners to Bump
   Input 0, and sets Bump Weight 0 to 0.5.
4. An identical existing mix is skipped silently and is not nested again.

Rules
-----
- All TriPlanar nodes in the active material are processed automatically.
- Disconnect All checks Scale, Offset, Rotation, and Blend Amount in one
  operation.
- Connect skips occupied inputs and never overwrites them.
- Disconnect removes only the matching connection from the selected source.
- A TriPlanar source is excluded from the targets to prevent self-connection.
- A source downstream of a target TriPlanar is rejected to prevent a graph
  cycle; select an upstream source node instead.
- Incompatible ports are skipped.
- Successful operations stay silent; only errors display a dialog.
- The same plugin folder supports C4D 2024.0–2026 and automatically falls
  back to the legacy port-value API when required.
- No third-party Python dependencies are required.
- Chinese UI uses Chinese resources. English and other UI languages use English.
