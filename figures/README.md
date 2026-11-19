# 图表源文件

图表优先使用文本源文件生成，便于版本控制和后续重绘。

- Mermaid 用于流程图、状态图和时序图。
- Python + matplotlib 用于时间轴、时空图和数值实验图。
- SVG 用于需要精细排版的系统结构图。

每张图在正文中只承担一个主要解释任务，并保留生成脚本。


## 2026-11-17 新增插图

本组图由 **anidoodle 0.10.1** 生成，经作者郭海锋筛选、调整和定稿。  
anidoodle 工程没有可用的 Git 提交；以 `package.json` 的 SHA-256、源 film 的 SHA-256 和输出 PNG 的 MD5 作为可复现记录。anidoodle 工程位于作者本地，不随本书仓库分发。

- 引擎版本：`0.10.1`
- `package.json` SHA-256：`db894b4cb411ec080992ed689838c5f65cd502920c825965138c84d57913ffdc`
- 源 film 目录：`src/canvas-core/`（作者本地保留）

### 部分题图（装饰，不编号）

| 输出文件 | 画面 | 源 film | 源 film SHA-256 | 输出 MD5 |
|---|---|---|---|---|
| `part-01-opener.png` | 一个路口，一条闭环 | `dshPart01.ts` | `da4a574d2570b37cc1a52628a8db8af99d48a25c5878d3da09549777f8ae50d0` | `3f1c45c30b5f0647466ec0cb7ca5af9a` |
| `part-02-opener.png` | 从事件到输入 | `dshPart02.ts` | `8d777fda8ab663c1739dfc1968a1725231bf1554329e1f2feddf0b5fe294f879` | `82c70e82a86d0d6dbe2ed228e1f474be` |
| `part-03-opener.png` | 一个周期的节拍 | `dshPart03.ts` | `1aca529234c1c4ffbeb8f43741059e210f939bce749fe3c934bdc99065ed3382` | `4efbc4dc4b84c2a515837690b3e70a04` |
| `part-04-opener.png` | 一条绿波串起四个路口 | `dshPart04.ts` | `da908ce7f2fa25950a30b18e168bbee519baec67e22cbb53218d9b917576e3e0` | `848d72dc37d49f4f75850a27a60d4e81` |
| `part-05-opener.png` | 从算法到信号机的桥 | `dshPart05.ts` | `0967d951961d178ab31211849982eeae2ad053411f4ec44ea189bb57d97c0573` | `e8d05b5126fb192c4b15b7a8d1b7701c` |
| `part-06-opener.png` | 执行与改善之间 | `dshPart06.ts` | `11d01a61bab07adce630608b5d6d4413b6ee0fc91684d134410fbad21d500c08` | `c77041720b75da35a55effe1573ff35c` |
| `part-07-opener.png` | 生产源码的地层 | `dshPart07.ts` | `0806b9ac4f79bf56ce45f0955cc537a3a45583f658eda66d6d3c3c4561d75cee` | `1835cf1a7462bd5edcd47b4a813f81bf` |

这些图不编图号、不写图题、不进图录、正文不引用；DOCX 中作为装饰图处理。

### 正式插图

| 输出文件 | 图号与画面 | 源 film | 源 film SHA-256 | 输出 MD5 |
|---|---|---|---|---|
| `fig-04-gates.png` | 图 4-1 四道正确性闸门 | `dshInvariantGates.ts` | `5ca1fba8ae9d45ce3bc4632ed5b81eb23aeb0d320eb98128dbf2559b04641864` | `22c52141af66055113d23b74ae9c141b` |
| `fig-06-quality.png` | 图 6-1 数据质量的三种坏法 | `dshFig06.ts` | `0ce604417499f4d8271751237df3babb2056db62c70472c89ab36ad77a921c4f` | `078fc7c30bf4929f83833848dd972a66` |
| `fig-23-evaluation.png` | 图 23-1 执行了，不等于改善了 | `dshFig23.ts` | `3338786caad87d4117949c57f69070240e9f8efb7f86b2b3e25afa6714865a2b` | `f5d841f9762987e838860c0d51195c46` |

### 扉页

| 输出文件 | 画面 | 源 film | 源 film SHA-256 | 输出 MD5 |
|---|---|---|---|---|
| `frontispiece.png` | 扉页水墨路口与格言 | `feiye.ts` | `c8d06b8a87da02850fdc6af0d903d0d2f9a2f0a2919b490d2de77fc832aa0615` | `fab597293d8eec3657bc1a638b93f4b6` |

扉页由作者郭海锋使用 anidoodle 0.10.1 生成，经作者定稿；扉页不编图号，不进入图录。

## 2026-11-19 重绘

- `green-wave.png` — 图 18-1 标准时空图与绿波带；由 `tools/make_figures.py` 生成。
- MD5：`c2453a7f12c81fdf7fc909c235c1668f`

## 分辨率已知例外

以下两张图低于 300 dpi，作者确认按当前版本使用，不再重绘：

- `frontispiece.png`：1721×2434，扉页整幅约 20.1 cm 宽，约 217 dpi。作为艺术扉页使用，线条和墨色不依赖精细网点。
- `system-closed-loop.png`：1600×1220，正文约 15.4 cm 宽，约 264 dpi。作为机制示意图使用，打印检查未发现文字或线条断裂。

这两项作为已接受的印刷例外记录，不再声称全书画质均达到 300 dpi。
