"""A small .xlsx writer: sheets of rows with bold titles and headers, no third-party package.

Rows are lists of cells; a cell is a str, int, float, None or a (value, style) pair where style is
"title", "head" or "note". Numbers stay numbers so Excel can sum and chart them.
"""
from __future__ import annotations

import io
import re
import zipfile
from xml.sax.saxutils import escape

_STYLES = {None: 0, "head": 1, "title": 2, "note": 3}
_BAD_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")
_BAD_NAME = re.compile(r"[\[\]:*?/\\]")


def _col(n: int) -> str:
    out = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        out = chr(65 + r) + out
    return out


def _text(value) -> str:
    return escape(_BAD_XML.sub("", str(value)))[:32000]


def _cell(ref: str, value, style) -> str:
    s = _STYLES.get(style, 0)
    sa = f' s="{s}"' if s else ""
    if value is None or value == "":
        return f'<c r="{ref}"{sa}/>' if s else ""
    if isinstance(value, bool):
        value = "да" if value else "нет"
    if isinstance(value, (int, float)):
        if value != value or value in (float("inf"), float("-inf")):
            return ""
        return f'<c r="{ref}"{sa}><v>{value}</v></c>'
    return f'<c r="{ref}" t="inlineStr"{sa}><is><t xml:space="preserve">{_text(value)}</t></is></c>'


def _sheet_xml(rows: list[list]) -> str:
    widths: dict[int, int] = {}
    body = []
    for r, row in enumerate(rows, start=1):
        cells = []
        for c, item in enumerate(row):
            value, style = item if isinstance(item, tuple) else (item, None)
            cells.append(_cell(f"{_col(c)}{r}", value, style))
            if style != "title" and style != "note":
                widths[c] = max(widths.get(c, 8), min(60, len(str(value if value is not None else "")) + 2))
        body.append(f'<row r="{r}">{"".join(cells)}</row>')
    cols = "".join(f'<col min="{c + 1}" max="{c + 1}" width="{w}" customWidth="1"/>' for c, w in sorted(widths.items()))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            + (f"<cols>{cols}</cols>" if cols else "")
            + f'<sheetData>{"".join(body)}</sheetData></worksheet>')


def _name(raw: str, used: set[str]) -> str:
    base = _BAD_NAME.sub(" ", raw).strip()[:31] or "Лист"
    name, n = base, 2
    while name.lower() in used:
        suffix = f" {n}"
        name, n = base[:31 - len(suffix)] + suffix, n + 1
    used.add(name.lower())
    return name


def build(sheets: list[tuple[str, list[list]]]) -> bytes:
    used: set[str] = set()
    named = [(_name(title, used), rows) for title, rows in sheets] or [("Лист", [])]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            + "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
                      'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                      for i in range(1, len(named) + 1))
            + "</Types>")
        z.writestr("_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>")
        z.writestr("xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
            + "".join(f'<sheet name="{escape(n, {chr(34): "&quot;"})}" sheetId="{i}" r:id="rId{i}"/>'
                      for i, (n, _) in enumerate(named, start=1))
            + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                      f'Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(named) + 1))
            + f'<Relationship Id="rId{len(named) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            "</Relationships>")
        z.writestr("xl/styles.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="4"><font><sz val="11"/><name val="Calibri"/></font>'
            '<font><b/><sz val="11"/><name val="Calibri"/></font>'
            '<font><b/><sz val="14"/><name val="Calibri"/></font>'
            '<font><i/><sz val="10"/><color rgb="FF666666"/><name val="Calibri"/></font></fonts>'
            '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
            '<fill><patternFill patternType="solid"><fgColor rgb="FFEEF2F7"/></patternFill></fill></fills>'
            '<borders count="1"><border/></borders>'
            '<cellStyleXfs count="1"><xf/></cellStyleXfs>'
            '<cellXfs count="4"><xf/><xf fontId="1" fillId="2" applyFont="1" applyFill="1"/>'
            '<xf fontId="2" applyFont="1"/><xf fontId="3" applyFont="1"/></cellXfs>'
            "</styleSheet>")
        for i, (_, rows) in enumerate(named, start=1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", _sheet_xml(rows))
    return buf.getvalue()
