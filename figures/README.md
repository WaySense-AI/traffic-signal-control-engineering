# 图表源文件

书中的图都来自可版本控制的源文件，便于复核与重绘：

- Mermaid：流程图、状态图、时序图；
- Python + matplotlib：时间轴、时空图、数值实验图、叙事图；
- SVG：需要精细排版的系统结构图；
- anidoodle：需要手绘质感与墨色层次的题图和扉页。

每张图在正文中只承担一个解释任务，并保留生成脚本或生成源文件的校验值。仓库不包含字体文件，脚本按 `tools/fetch_fonts.sh` 下载 Noto OFL 字体后即可重绘。

## 生成方式

| 类别 | 工具 | 生成源 | 复现 |
|---|---|---|---|
| 数值图与时空图 | matplotlib | `tools/make_figures.py` | 运行脚本 |
| 叙事图（战役地图等 4 张） | matplotlib | `tools/make_narrative_figures.py` | 运行脚本 |
| 部分题图、图 4-1／6-1／23-1、扉页 | anidoodle 0.10.1 | 作者本地工程 | 见下表校验值 |

anidoodle 引擎采用 Apache License 2.0，不随本仓库分发，仓库只包含生成后的 PNG。下表用源文件 SHA-256 与输出 MD5 记录对应关系，可据此确认某张图由哪一份源文件产出。引擎版本 `0.10.1`，其 `package.json` 的 SHA-256 为 `db894b4cb411ec080992ed689838c5f65cd502920c825965138c84d57913ffdc`。

## anidoodle 生成的图

| 输出文件 | 图号与画面 | 源文件 SHA-256 | 输出 MD5 |
|---|---|---|---|
| `part-01-opener.png` | 题图 1「一个路口，一条闭环」 | `da4a574d2570b37cc1a52628a8db8af99d48a25c5878d3da09549777f8ae50d0` | `3f1c45c30b5f0647466ec0cb7ca5af9a` |
| `part-02-opener.png` | 题图 2「从事件到输入」 | `8d777fda8ab663c1739dfc1968a1725231bf1554329e1f2feddf0b5fe294f879` | `82c70e82a86d0d6dbe2ed228e1f474be` |
| `part-03-opener.png` | 题图 3「一个周期的节拍」 | `1aca529234c1c4ffbeb8f43741059e210f939bce749fe3c934bdc99065ed3382` | `4efbc4dc4b84c2a515837690b3e70a04` |
| `part-04-opener.png` | 题图 4「一条绿波串起四个路口」 | `da908ce7f2fa25950a30b18e168bbee519baec67e22cbb53218d9b917576e3e0` | `848d72dc37d49f4f75850a27a60d4e81` |
| `part-05-opener.png` | 题图 5「从算法到信号机的桥」 | `0967d951961d178ab31211849982eeae2ad053411f4ec44ea189bb57d97c0573` | `e8d05b5126fb192c4b15b7a8d1b7701c` |
| `part-06-opener.png` | 题图 6「执行与改善之间」 | `11d01a61bab07adce630608b5d6d4413b6ee0fc91684d134410fbad21d500c08` | `c77041720b75da35a55effe1573ff35c` |
| `part-07-opener.png` | 题图 7「生产源码的地层」 | `0806b9ac4f79bf56ce45f0955cc537a3a45583f658eda66d6d3c3c4561d75cee` | `1835cf1a7462bd5edcd47b4a813f81bf` |
| `fig-04-gates.png` | 图 4-1 四道正确性闸门 | `5ca1fba8ae9d45ce3bc4632ed5b81eb23aeb0d320eb98128dbf2559b04641864` | `22c52141af66055113d23b74ae9c141b` |
| `fig-06-quality.png` | 图 6-1 数据质量的三种坏法 | `0ce604417499f4d8271751237df3babb2056db62c70472c89ab36ad77a921c4f` | `078fc7c30bf4929f83833848dd972a66` |
| `fig-23-evaluation.png` | 图 23-1 执行了，不等于改善了 | `3338786caad87d4117949c57f69070240e9f8efb7f86b2b3e25afa6714865a2b` | `f5d841f9762987e838860c0d51195c46` |
| `frontispiece.png` | 扉页水墨路口与格言 | `c8d06b8a87da02850fdc6af0d903d0d2f9a2f0a2919b490d2de77fc832aa0615` | `fab597293d8eec3657bc1a638b93f4b6` |

七张题图与扉页不编图号、不写图题、不进图录、正文不引用，DOCX 中作为装饰图处理。

## 脚本生成的图

| 输出文件 | 图号与画面 | 生成脚本 | 输出 MD5 |
|---|---|---|---|
| `green-wave.png` | 图 18-1 标准时空图与绿波带 | `tools/make_figures.py` | `c2453a7f12c81fdf7fc909c235c1668f` |
| `battle-map.png` | 图 前-1 六场战役地图（3200×1600） | `tools/make_narrative_figures.py` | `d4132a9dceda579ef2cce51fc27812a1` |
| `six-layers.png` | 图 2-1 六个层面的状态账（2600×1500） | `tools/make_narrative_figures.py` | `98a780c96e0b82febdc196a192d182f2` |
| `offset-propagation.png` | 图 16-1 S1—S4 的偏移传播（2600×1200） | `tools/make_narrative_figures.py` | `3751ca716e5781730e5c70220bcbac09` |
| `coordination-tables.png` | 图 27-1 生产协调的四张表（3000×1300） | `tools/make_narrative_figures.py` | `74a709b8ca70f0b219acd725806ec4a7` |

叙事图为脚本绘制，文字、编号和比例都在代码里，便于按同一版式重绘。绘制时用脚本而非图形工具排版中文标签，避免字形错位。

`tools/make_narrative_figures.py` 的 SHA-256：`787917c907ef2e145816ae82fcdfd3566d67c41507e6ed0790670653a12ca672`

## 印刷分辨率

书中的插图按印刷要求输出，下列两张按用途采用较低分辨率：

| 文件 | 尺寸 | 正文宽度 | 实际 dpi | 说明 |
|---|---|---|---|---|
| `frontispiece.png` | 1721×2434 | 约 20.1 cm | 约 217 | 艺术扉页，线条与墨色不依赖精细网点 |
| `system-closed-loop.png` | 1600×1220 | 约 15.4 cm | 约 264 | 机制示意图，打印未见文字或线条断裂 |

## 扉页二维码

- `wechat-qr.jpg`：作者公众号二维码，430×430 px，MD5 `ce787cd7e9e589011f8acaa2926d4304`。
- `frontispiece-qr.png`：在原扉页右下角合成二维码与「扫码关注」标签，1721×2434 px，MD5 `b5749682994bf9961e8e3552463d711c`。
- 原 `frontispiece.png` 保留不动，PDF 使用 `frontispiece-qr.png`。
- 二维码在 PDF 第 2 页渲染后仍可解码，指向 `http://weixin.qq.com/r/mp/ehyfh1DE3w2grRTk90lo`。
