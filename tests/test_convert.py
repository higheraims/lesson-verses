import pytest

from lesson_verses.app import ConversionError, convert, main
from sample import check_edition, write_sample


def test_sample_converts(tmp_path):
    src, dst = tmp_path / "sample.docx", tmp_path / "edition.docx"
    write_sample(src)
    notes = convert(src, dst)
    assert check_edition(dst) == []
    assert notes == ["Lesson 1, day 3, question a runs over two paragraphs; read as one."]


def test_headless_mode(tmp_path):
    src, dst = tmp_path / "sample.docx", tmp_path / "edition.docx"
    write_sample(src)
    assert main(["--convert", str(src), str(dst)]) == 0
    assert dst.is_file()


def test_bad_reference_stops_the_conversion(tmp_path):
    from docx import Document
    doc = Document()
    for line in ["2031", "JAN-MAR", "Vol. 1, No. 1", "Theme",
                 "Sabbath, January 4, 2031\tLesson 1", "Title",
                 "1. \tDAY \tSun, Dec 29", "a. \tWhat? Jude 30; Genesis 51:1."]:
        doc.add_paragraph(line)
    src = tmp_path / "bad.docx"
    doc.save(str(src))
    with pytest.raises(ConversionError) as err:
        convert(src, tmp_path / "out.docx")
    assert "question a: Jude 30" in str(err.value)
    assert "question a: Genesis 51:1" in str(err.value)
    assert not (tmp_path / "out.docx").exists()


def test_not_a_word_file(tmp_path):
    src = tmp_path / "notes.docx"
    src.write_text("plain text")
    with pytest.raises(ConversionError):
        convert(src, tmp_path / "out.docx")
