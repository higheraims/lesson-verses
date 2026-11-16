import pytest

from lesson_verses.manuscript import ManuscriptError, parse_lines

MASTHEAD = ["2031", "JAN-MAR", "Vol. 12, No. 1", "Example Lessons", "Example Division",
            "A Theme", "A Subtitle"]
LESSON = ["Contents", "1. A Lesson \t5",
          "Sabbath, January 4, 2031\tLesson 1", "A Lesson",
          "1. \tA DAY \tSun, Dec 29", "a. \tWhat? Genesis 1:1."]


def test_masthead():
    ms = parse_lines(MASTHEAD + LESSON)
    assert (ms.year, ms.months, ms.volume) == ("2031", "January–March", "Vol. 12, No. 1")
    assert (ms.theme, ms.subtitle) == ("A Theme", "A Subtitle")
    assert ms.notes == []


@pytest.mark.parametrize("months, expected", [
    ("Oct - DEC", "October–December"), ("jul-Sep", "July–September"),
    ("Apr -Jun", "April–June"), ("jan-MAR 2031", "January–March"),
])
def test_month_range_forms(months, expected):
    ms = parse_lines(["2031", months, "Vol. 1, No. 1", "X Division", "T"] + LESSON)
    assert ms.months == expected


def test_volume_without_periods_and_with_a_stray_letter():
    assert parse_lines(["2031", "JAN-MAR", "Vol 12, No 1x", "T"] + LESSON).volume == \
        "Vol. 12, No. 1"


def test_theme_and_subtitle_over_two_paragraphs_each():
    ms = parse_lines(["2031 ", "jul - SEP", "Vol. 1, No. 3", "Pub", "Example Division",
                      "Rivers and ", "Mountains", "A short study of ", "water"] + LESSON)
    assert (ms.theme, ms.subtitle) == ("Rivers and Mountains", "A short study of water")


def test_publication_and_division_on_one_line_and_an_extra_line():
    ms = parse_lines(["2031", "JAN-MAR", "Vol. 1, No. 1", "Example Lessons Example Division",
                      "Theme", "Subtitle", "Left over from last time"] + LESSON)
    assert (ms.theme, ms.subtitle) == ("Theme", "Subtitle")
    assert ms.notes == ['Ignored an extra line under the subtitle: "Left over from last time".']


def test_both_friday_forms_are_skipped():
    ms = parse_lines(MASTHEAD + LESSON + [
        "6. \tPersonal Reflection \tFri, Jan 3", "a. \tReflect.",
        "Sabbath, January 11, 2031\tLesson 2", "Another",
        "1. \tDAY \tSun, Jan 5", "a. \tWhat? John 1:1.",
        "PERSONAL REVIEW QUESTIONS \tFri, Jan 10", "a. \tReview."])
    assert [[d.number for d in lesson.days] for lesson in ms.lessons] == [[1], [1]]
    assert [q.prompt for lesson in ms.lessons for d in lesson.days for q in d.questions] == [
        "What?", "What?"]


def test_lesson_and_day_headers():
    ms = parse_lines(MASTHEAD + ["Sabbath, April 5, 2031\t Lesson 1", "Title",
                                 "1. \tLAMPS AND OIL \t  Sun, Mar 30", "a. \tQ? Genesis 1:1."])
    lesson = ms.lessons[0]
    assert (lesson.number, lesson.sabbath, lesson.title) == (1, "Sabbath, April 5, 2031", "Title")
    day = lesson.days[0]
    assert (day.number, day.title, day.date) == (1, "LAMPS AND OIL", "Sun, Mar 30")


def test_question_split_over_two_paragraphs():
    ms = parse_lines(MASTHEAD + LESSON[:-1] + ["a. \tAlthough split,", "\tis this one question? John 1:1."])
    [q] = ms.lessons[0].days[0].questions
    assert q.prompt == "Although split, is this one question?"
    assert [p.label for p in q.passages] == ["John 1:1"]
    assert ms.notes == ["Lesson 1, day 1, question a runs over two paragraphs; read as one."]


def test_letters_out_of_order_are_kept_and_noted():
    ms = parse_lines(MASTHEAD + LESSON[:-1] + ["b. \tOne? John 1:1.", "a. \tTwo? John 1:2."])
    assert [q.letter for q in ms.lessons[0].days[0].questions] == ["b", "a"]
    assert ms.notes == ["Lesson 1, day 1: questions are lettered b, a."]


def test_contents_title_mismatch_is_noted():
    lines = MASTHEAD + ["Contents", "1. Seeds in Spring \t41",
                        "Sabbath, January 4, 2031\tLesson 1", "Seeds In Spring"]
    assert parse_lines(lines).notes == [
        'Lesson 1 is "Seeds In Spring" but the Contents has "Seeds in Spring".']


def test_tabs_inside_a_title_are_collapsed():
    ms = parse_lines(MASTHEAD + ["Sabbath, January 4, 2031\tLesson 1", "Fields and \t\t\tFences"])
    assert ms.lessons[0].title == "Fields and Fences"


def test_not_a_manuscript():
    with pytest.raises(ManuscriptError):
        parse_lines(["Dear friend,", "This is a letter."])
