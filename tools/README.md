# 公开构建工具

本目录只公开复现书稿和无障碍声明所必需的脚本。内部 QA 脚本不进入公开仓库。

## 公开（11 个）

- `build_book.py`：Markdown → DOCX
- `render_pdf.sh`：DOCX → PDF
- `check_pdf.py`：PDF 页数/字体/标记检查
- `make_cover.py`：封面生成
- `make_figures.py`：正式图生成
- `fetch_fonts.sh`：下载 Noto OFL 字体
- `fonts.conf`：字体配置
- `book-meta.json`：构建元数据
- `toc-pages.json`：目录页码，`check_pdf.py` 的输入
- `extract_toc_pages.py`：从 PDF 生成 `toc-pages.json`
- `audit_docx.py`：DOCX 无障碍审计；读者可据此复核 high/medium/low 全 0 的声明

## 内部（不公开）

- `add_table_captions.py`
- `style_audit.py`
- `review_audit.py`
- `font_probe.py`
- `make_contact_sheets.py`
- `check_manuscript.py`
- `toc-v*.json`

## 第三方依赖

- python-docx：MIT，见 `licenses/python-docx-MIT.txt`
- Pillow：HPND/MIT-CMU，见 `licenses/Pillow-HPND.txt`
- LibreOffice / poppler：外部可执行程序，不由本仓库分发
