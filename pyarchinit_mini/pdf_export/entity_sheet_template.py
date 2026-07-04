#!/usr/bin/env python3
"""Classic-plugin-style PDF sheet ENGINE, parametrized by a per-entity config.

Ports the LOOK of the classic QGIS pyarchinit plugin's styled per-scheda PDFs
(colored section header rows, label:value grid cells, logo header, page
numbers, real sub-tables for list-of-lists/JSON columns) as ONE parametric
engine — see ``pyarchinit_exp_Faunasheet_pdf.py`` and
``pyarchinit_exp_UTsheet_pdf.py`` in the classic plugin for the visual
recipe this mirrors.

Pure reportlab platypus. NO qgis imports. Entity-specific field lists and
section groupings live in :mod:`sheet_configs`, not here.
"""

import ast
import json
import os
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Fonts — same try/except-fallback-to-Helvetica pattern as the classic UT
# exemplar (pyarchinit_exp_UTsheet_pdf.py lines ~34-40). Cambria is almost
# never present outside the original plugin's bundled resources, so this
# routinely (and harmlessly) falls back to Helvetica.
# ---------------------------------------------------------------------------
try:
    pdfmetrics.registerFont(TTFont('Cambria', 'Cambria.ttc'))
    pdfmetrics.registerFont(TTFont('CambriaBold', 'cambriab.ttf'))
    registerFontFamily('Cambria', normal='Cambria', bold='CambriaBold')
    DEFAULT_FONT = 'Cambria'
except Exception:
    DEFAULT_FONT = 'Helvetica'

# ---------------------------------------------------------------------------
# Page geometry + palette — copied from the fauna exemplar's module
# constants (pyarchinit_exp_Faunasheet_pdf.py lines ~50-63).
# ---------------------------------------------------------------------------
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 12 * mm
USABLE_WIDTH = PAGE_WIDTH - 2 * MARGIN

HEADER_BG = colors.HexColor('#2C3E50')      # Dark blue-gray
SECTION_BG = colors.HexColor('#3498DB')     # Blue
SUBSECTION_BG = colors.HexColor('#ECF0F1')  # Light gray
LABEL_BG = colors.HexColor('#F8F9FA')       # Very light gray
BORDER_COLOR = colors.HexColor('#BDC3C7')   # Medium gray


class NumberedCanvasEntity(canvas.Canvas):
    """Canvas with "Pag. X di Y" footer — copy of NumberedCanvasFinds from
    pyarchinit_finds_template.py."""

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """Add page info to each page (page x of y)."""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.setFont(DEFAULT_FONT, 8)
        self.drawRightString(
            PAGE_WIDTH - MARGIN, MARGIN / 2,
            "Pag. %d di %d" % (self._pageNumber, page_count)
        )


def _get_styles() -> Dict[str, ParagraphStyle]:
    """Professional styles for the sheet — mirrors the fauna exemplar's
    ``_get_styles()`` (title/section/label/value/longtext), plus two extra
    styles this engine needs (subtable column headers, header-right cell)."""
    styles: Dict[str, ParagraphStyle] = {}

    styles['title'] = ParagraphStyle(
        'EntityTitle', fontName=DEFAULT_FONT, fontSize=14, leading=18,
        alignment=TA_CENTER, textColor=colors.white,
    )
    styles['section'] = ParagraphStyle(
        'EntitySection', fontName=DEFAULT_FONT, fontSize=10, leading=14,
        alignment=TA_LEFT, textColor=colors.white, leftIndent=3,
    )
    styles['label'] = ParagraphStyle(
        'EntityLabel', fontName=DEFAULT_FONT, fontSize=7, leading=9,
        alignment=TA_LEFT, textColor=HEADER_BG,
    )
    styles['value'] = ParagraphStyle(
        'EntityValue', fontName=DEFAULT_FONT, fontSize=8, leading=10,
        alignment=TA_LEFT, textColor=colors.black,
    )
    styles['longtext'] = ParagraphStyle(
        'EntityLongText', fontName=DEFAULT_FONT, fontSize=8, leading=10,
        alignment=TA_JUSTIFY, textColor=colors.black,
    )
    styles['subheader'] = ParagraphStyle(
        'EntitySubHeader', fontName=DEFAULT_FONT, fontSize=7, leading=9,
        alignment=TA_CENTER, textColor=HEADER_BG,
    )
    styles['header_right'] = ParagraphStyle(
        'EntityHeaderRight', fontName=DEFAULT_FONT, fontSize=8, leading=11,
        alignment=TA_CENTER, textColor=colors.white,
    )
    return styles


def _safe(value: Any) -> str:
    """Escape a value for reportlab Paragraph mini-XML — mirrors
    PDFGenerator._safe_cell_text (pdf_generator.py ~line 1056).

    Real Python booleans render as "Sì"/"No" (Italian, matching the rest of
    this engine's labels) rather than "True"/"False" — but only actual
    ``bool`` values; strings like "Si"/"No"/"true" already stored by the
    services pass through unchanged."""
    if value is None:
        return ''
    if isinstance(value, bool):
        value = 'Sì' if value else 'No'
    try:
        text = str(value)
    except Exception:
        text = repr(value)
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == '':
        return True
    return False


def _chunk(items: List[Any], size: int):
    size = max(int(size or 1), 1)
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _parse_pylist(raw: Any) -> list:
    """Parse a stored ``str(list-of-lists)`` sub-table value using
    ast.literal_eval — NEVER eval(). Returns [] for None/empty/malformed
    input; never raises. Mirrors StrutturaService.parse_pylist /
    the fauna exemplar's ast.literal_eval fallback."""
    if not raw:
        return []
    if isinstance(raw, (list, tuple)):
        return list(raw)
    try:
        parsed = ast.literal_eval(raw)
    except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError):
        return []
    return parsed if isinstance(parsed, list) else []


def _parse_json_list(raw: Any) -> list:
    """Parse a stored JSON sub-table value (e.g. fauna's specie_psi /
    misure_ossa). Returns [] for None/empty/malformed input; never raises."""
    if not raw:
        return []
    if isinstance(raw, (list, tuple)):
        return list(raw)
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


def _get_logo_flowable(logo_path: Optional[str], styles: Dict[str, ParagraphStyle]):
    """Logo Image scaled to ~1.5in, falling back to a bold "PYARCHINIT"
    Paragraph when no logo is available — matches the fauna/tomba exemplars'
    ``_get_logo`` (1.2-2.0 inch) with graceful degradation."""
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path)
            logo.drawHeight = 1.5 * inch * logo.drawHeight / logo.drawWidth
            logo.drawWidth = 1.5 * inch
            logo.hAlign = 'CENTER'
            return logo
        except Exception:
            pass
    return Paragraph('<b>PYARCHINIT</b>', styles['header_right'])


def _header_table(record: Dict[str, Any], config: Dict[str, Any],
                   styles: Dict[str, ParagraphStyle], logo_path: Optional[str]) -> Table:
    """Header: logo + title + a right cell with sito/id — mirrors the fauna
    exemplar's header_table (colored HEADER_BG band, logo on white)."""
    logo_cell = _get_logo_flowable(logo_path, styles)
    title_text = config.get('title', '')

    id_col = config.get('id_col')
    id_val = record.get(id_col) if id_col else None
    sito_val = record.get('sito') or record.get('progetto') or ''

    right_lines = []
    if sito_val:
        right_lines.append(f"Sito: {_safe(sito_val)}")
    if not _is_empty(id_val):
        right_lines.append(f"ID: {_safe(id_val)}")
    right_para = Paragraph('<br/>'.join(right_lines), styles['header_right'])

    logo_width = 2.2 * 28.35  # ~2.2cm in points
    right_width = 4 * 28.35   # ~4cm in points
    title_width = USABLE_WIDTH - logo_width - right_width

    header_data = [[
        logo_cell,
        Paragraph(f"<b>{_safe(title_text)}</b>", styles['title']),
        right_para,
    ]]
    table = Table(header_data, colWidths=[logo_width, title_width, right_width])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HEADER_BG),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (2, 0), (2, 0), 8),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
    ]))
    return table


def _section_header_table(title: str, styles: Dict[str, ParagraphStyle]) -> Table:
    table = Table([[Paragraph(f"<b>{_safe(title)}</b>", styles['section'])]],
                   colWidths=[USABLE_WIDTH])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), SECTION_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    return table


def _field_rows(fields: List[Dict[str, Any]], cols: int,
                 record: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> List[Table]:
    """Lay out consecutive "field" entries in a `cols`-per-row grid.
    Empty/None values are skipped (rendered as a blank cell) but the grid
    alignment is preserved; a row with no non-empty values at all is
    dropped entirely."""
    flowables: List[Table] = []
    col_width = USABLE_WIDTH / max(int(cols or 1), 1)

    for chunk in _chunk(fields, cols):
        cells: List[Any] = []
        any_value = False
        for f in chunk:
            value = record.get(f['name'])
            if _is_empty(value):
                cells.append('')
            else:
                any_value = True
                label = f.get('label', f['name'])
                cells.append(Paragraph(f"<b>{_safe(label)}:</b> {_safe(value)}", styles['label']))
        if not any_value:
            continue
        while len(cells) < cols:
            cells.append('')
        table = Table([cells], colWidths=[col_width] * cols)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), LABEL_BG),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]))
        flowables.append(table)
    return flowables


def _long_field_flowable(field_cfg: Dict[str, Any], record: Dict[str, Any],
                          styles: Dict[str, ParagraphStyle]) -> Optional[Table]:
    """A full-width justified "label: value" paragraph in its own row.
    Returns None (skip) if the value is empty/None."""
    value = record.get(field_cfg['name'])
    if _is_empty(value):
        return None
    label = field_cfg.get('label', field_cfg['name'])
    para = Paragraph(f"<b>{_safe(label)}:</b> {_safe(value)}", styles['longtext'])
    table = Table([[para]], colWidths=[USABLE_WIDTH])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LABEL_BG),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    return table


def _subtable_flowables(field_cfg: Dict[str, Any], record: Dict[str, Any],
                         styles: Dict[str, ParagraphStyle]) -> List[Any]:
    """Parse the raw stored value (pylist via ast.literal_eval, or json) and
    render a real sub-table with the config's column headers. Returns []
    (skip) when the value is empty or unparseable."""
    raw = record.get(field_cfg['name'])
    parse_kind = field_cfg.get('parse', 'pylist')
    rows = _parse_json_list(raw) if parse_kind == 'json' else _parse_pylist(raw)
    columns = field_cfg.get('columns') or []
    if not rows or not columns:
        return []

    flowables: List[Any] = []
    label = field_cfg.get('label', field_cfg['name'])
    caption = Table([[Paragraph(f"<b>{_safe(label)}</b>", styles['label'])]],
                     colWidths=[USABLE_WIDTH])
    caption.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), SUBSECTION_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    flowables.append(caption)

    ncols = len(columns)
    table_data = [[Paragraph(f"<b>{_safe(c)}</b>", styles['subheader']) for c in columns]]
    for row in rows:
        if isinstance(row, (list, tuple)):
            cells = list(row)
        else:
            cells = [row]
        cells = (cells + [''] * ncols)[:ncols]
        table_data.append([
            Paragraph(_safe(c) if not _is_empty(c) else '-', styles['value'])
            for c in cells
        ])

    col_width = USABLE_WIDTH / max(ncols, 1)
    data_table = Table(table_data, colWidths=[col_width] * ncols)
    data_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), SUBSECTION_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), HEADER_BG),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LABEL_BG]),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    flowables.append(data_table)
    return flowables


def _section_flowables(section: Dict[str, Any], record: Dict[str, Any],
                        styles: Dict[str, ParagraphStyle]) -> List[Any]:
    """A colored section-header row + the section's fields laid out
    `section.get('cols', 3)` per row. Sections that end up with no
    renderable content (every field empty) are skipped entirely — no
    orphan header for an empty section."""
    cols = section.get('cols', 3)
    content: List[Any] = []
    run: List[Dict[str, Any]] = []

    def flush_run():
        if run:
            content.extend(_field_rows(run, cols, record, styles))
            run.clear()

    for f in section.get('fields', []):
        ftype = f.get('type', 'field')
        if ftype == 'field' and not f.get('long'):
            run.append(f)
            continue
        flush_run()
        if ftype == 'subtable':
            content.extend(_subtable_flowables(f, record, styles))
        elif f.get('long'):
            flowable = _long_field_flowable(f, record, styles)
            if flowable is not None:
                content.append(flowable)
    flush_run()

    if not content:
        return []

    flowables = [_section_header_table(section.get('title', ''), styles)]
    flowables.extend(content)
    flowables.append(Spacer(1, 3 * mm))
    return flowables


class EntitySheet:
    """Builds one classic-style PDF sheet (a single reportlab Table
    flowable, wrapped like the fauna exemplar's ``_create_professional_sheet``
    main_table) for one record, driven entirely by `config`."""

    def __init__(self, record: Dict[str, Any], config: Dict[str, Any],
                 logo_path: Optional[str] = None):
        self.record = record or {}
        self.config = config or {}
        self.logo_path = logo_path
        self.styles = _get_styles()

    def create_sheet(self) -> List[Any]:
        elements: List[Any] = [
            _header_table(self.record, self.config, self.styles, self.logo_path),
            Spacer(1, 3 * mm),
        ]
        for section in self.config.get('sections', []):
            elements.extend(_section_flowables(section, self.record, self.styles))

        main_data = [[e] for e in elements]
        main_table = Table(main_data, colWidths=[USABLE_WIDTH])
        main_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        return [main_table]


def generate_entity_sheets(rows: List[Dict[str, Any]], config: Dict[str, Any],
                            output_path: str, logo_path: Optional[str] = None) -> str:
    """Build one classic-style sheet per record + PageBreak, à la
    ``generate_finds_sheets`` (pyarchinit_finds_template.py ~line 357).
    Empty `rows` produces a single "No records" page."""
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN * 1.3,
    )

    story: List[Any] = []
    if not rows:
        styles = _get_styles()
        story.append(Paragraph(
            f"<b>{_safe(config.get('title', ''))}</b>", styles['label']
        ))
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph('Nessun record da visualizzare.', styles['value']))
    else:
        for i, record in enumerate(rows):
            sheet = EntitySheet(record, config, logo_path)
            story.extend(sheet.create_sheet())
            if i < len(rows) - 1:
                story.append(PageBreak())

    doc.build(story, canvasmaker=NumberedCanvasEntity)
    return output_path
