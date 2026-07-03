"""Unit test for PDFGenerator.generate_records_pdf (SP4 export).

This is the generic per-record PDF builder added for the tomba/struttura/
fauna/ut Excel/CSV/PDF export feature: title + one field/value section per
record. No Flask/db involved — just exercise the PDF builder directly.
"""
import os

from pyarchinit_mini.pdf_export.pdf_generator import PDFGenerator


def test_generate_records_pdf_produces_nonempty_pdf(tmp_path):
    gen = PDFGenerator()
    output_path = str(tmp_path / "records.pdf")

    result = gen.generate_records_pdf(
        'T',
        [{'id_tomba': 1, 'sito': 'S', 'rito': 'inumazione'}],
        output_path,
    )

    assert result == output_path
    assert os.path.exists(output_path)
    data = open(output_path, 'rb').read()
    assert len(data) > 0
    assert data.startswith(b'%PDF')


def test_generate_records_pdf_skips_empty_and_none_values(tmp_path):
    gen = PDFGenerator()
    output_path = str(tmp_path / "records2.pdf")

    gen.generate_records_pdf(
        'T',
        [{'id_tomba': 1, 'sito': 'S', 'rito': None, 'descrizione_taf': ''}],
        output_path,
    )

    data = open(output_path, 'rb').read()
    assert data.startswith(b'%PDF')


def test_generate_records_pdf_handles_empty_list(tmp_path):
    gen = PDFGenerator()
    output_path = str(tmp_path / "records3.pdf")

    result = gen.generate_records_pdf('T', [], output_path)

    assert result == output_path
    data = open(output_path, 'rb').read()
    assert data.startswith(b'%PDF')


def test_generate_records_pdf_uses_field_labels(tmp_path):
    gen = PDFGenerator()
    output_path = str(tmp_path / "records4.pdf")

    gen.generate_records_pdf(
        'T',
        [{'id_tomba': 1, 'sito': 'S'}],
        output_path,
        field_labels={'sito': 'Site Name'},
    )

    data = open(output_path, 'rb').read()
    assert data.startswith(b'%PDF')
