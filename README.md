# MHGU Xbox 手柄按键提示

适用于 Astris 上的 Switch 国际版《Monster Hunter Generations Ultimate》1.4.0 简体中文界面（Title ID `0100770008DD8000`）。这个 LayeredFS Mod 按实体位置显示 Xbox 键帽，适合使用右侧 B 确认、下方 A 返回的手柄布局。

## 安装

1. 从 [Releases](https://github.com/DogWY/mhxx-xbox-button-prompts/releases/latest) 下载 `MHGU-Xbox-Button-Prompts.zip` 并解压。
2. 在 Astris 游戏库右键游戏，打开 **Open Mods Folder → LayeredFS Mods**，复制整个 `0.MHGU-Xbox-Button-Prompts` 文件夹。
3. 在 **Manage Mods** 启用它。如果装过开发用的 `MHGU-Xbox-Probe`，请停用探针，然后重启游戏。要恢复原提示，停用正式 Mod 并重启。

| 游戏原键位 | Xbox 提示 |
| --- | --- |
| A、B、X、Y | B、A、Y、X |
| L、R、ZL、ZR | LB、RB、LT、RT |
| 左、右摇杆按下 | LS、RS |
| ＋、－ | Menu、View 图标 |

## 覆盖与验证

替换了通用和任务按键图集、操作面板、帮助翻页图标和标题的 PRESS B，并更新了简中教程、猎人笔记、菜单、任务窗口及部分 NPC 对话里的键名。发布包沿用已测试的 3.HD 与视距增加 60% 共用的标题归档。其他 Mod 若也修改同一个 ARC，可以使用下方的构建工具合并标题修改。

在 Astris 1.0.32 中已看到标题 PRESS B、村内 Y 世界地图、X 猎人搜索，以及帮助目录的 LB/RB。任务内 HUD 和实体手柄逐键对应仍待实测。图集预览见 [evidence](evidence/)。

## 从本地游戏资源构建

使用 Python 3、支持 DXT5 编码的 Pillow，以及自行导出的 MHGU 1.4.0 RomFS。以下命令中的 `originals` 存放从 `romfs/nativeNX/loc/arc/` 复制的 `resident.arc` 和从 `romfs/nativeNX/chS/arc/` 复制的 `quest_chS.arc`。三个脚本按以下顺序写入同一输出目录。

```sh
python3 build_mod.py originals 0.MHGU-Xbox-Button-Prompts
python3 build_help.py romfs 0.MHGU-Xbox-Button-Prompts
python3 build_title.py romfs/nativeNX 0.MHGU-Xbox-Button-Prompts
```

如需沿用某个标题 Mod，把 `--title-archive 路径/title_chS.arc` 加到最后一条命令。三个脚本都支持用 `--font` 指定字体，默认使用 macOS 的 Arial Bold。
