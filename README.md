# MHGU Xbox 手柄按键提示

适用于 Astris 上的 Switch 国际版《Monster Hunter Generations Ultimate》1.4.0 简体中文界面（Title ID `0100770008DD8000`）。按实体位置显示 Xbox 键帽，适合右侧 B 确认、下方 A 返回的布局。

## 生成与安装

1. 从 [Releases](https://github.com/DogWY/mhxx-xbox-button-prompts/releases) 下载 `MHGU-Xbox-Builder.zip`，解压并进入含有 `build_release.py` 的目录。准备自己导出的游戏 1.4.0 RomFS，所选文件夹下应有 `nativeNX`。
2. 使用 Python 3.9 或更新版本，安装带 DXT5 编码支持的 Pillow。在 macOS 终端执行以下命令，将最后一行的 RomFS 路径替换为自己的路径。

   ```sh
   python3 -m venv .venv
   .venv/bin/python -m pip install 'Pillow>=11.3'
   .venv/bin/python build_release.py "/path/to/romfs"
   ```

3. 构建成功后会生成 `0.MHGU-Xbox-Button-Prompts` 文件夹。可以用第二个位置参数指定新的输出目录。默认字体为 macOS 的 Arial Bold，可用 `--font "/path/to/font.ttf"` 指定本机字体。
4. 在 Astris 游戏库右键游戏，打开 **Open Mods Folder → LayeredFS Mods**，将生成的整个文件夹放入其中。在 **Manage Mods** 启用，停用开发探针或旧版，重启游戏。升级时先将旧版移出 Mods 目录，再放入新版。

| 游戏原键位 | Xbox 提示 |
| --- | --- |
| A、B、X、Y | B、A、Y、X |
| L、R、ZL、ZR | LB、RB、LT、RT |
| 左、右摇杆按下 | LS、RS |
| ＋、－ | Menu、View 图标 |

## 覆盖与验证

包含通用和任务按键图集、操作面板、帮助翻页图标、标题 PRESS B，以及简中教程、猎人笔记、菜单、任务窗口和部分 NPC 对话里的键名。v0.1.1 的生成器默认使用玩家导出的原版标题。公开附件只包含生成器源码和说明。

v0.1.0 在 Astris 1.0.32 中已验证标题 PRESS B、村内 Y 世界地图、X 猎人搜索和帮助目录 LB/RB。任务内 HUD 与实体手柄逐键对应仍待实测。

## 与其他 Mod 合用

两个 Mod 修改同一路径的 ARC 时，Astris 只加载其中一份。若使用 3.HD、视距或其他修改界面的 Mod，请在生成时传入实际启用的 Mod 文件夹，每个文件夹下面应有 `romfs/`。例如：

```sh
.venv/bin/python build_release.py "/path/to/romfs" "0.MHGU-Xbox-Button-Prompts" \
  --merge-mod "/path/to/3.HD" --merge-mod "/path/to/视距增加60%"
```

生成器会比较原版、Xbox 提示和额外 Mod 的改动，在同一个 ARC 里合并不同成员的修改。多个来源对同一成员作出不同修改，或对同一散装资源作出不同修改时，构建会报出冲突并停止。请保留其他 Mod 启用，生成的模块只覆盖 Xbox 提示用到的文件；应让它在同路径资源中优先加载。

重点检查这些相对于 `romfs/nativeNX/` 的归档：

- `loc/arc/resident.arc`
- `chS/arc/` 下的 `title_chS.arc`、`quest_chS.arc`、`resident_chS.arc`、`result_chS.arc`
- `chS/arc/village/common_chS.arc`、`chS/arc/village/hunter_note_chS.arc`
- `chS/arc/tutorial/common_chS.arc`、`chS/arc/npc/npcFakeArc_chS.arc`

使用干净的 1.4.0 RomFS 作基线，选择新输出目录。所有步骤成功后才会生成最终目录。原版、其他 Mod 和已有安装可以留作回退。
