from pathlib import Path

import pytest

from lesson_verses.scripture import Bible, find_passages, printed_label, split_passages, verse_keys

KJV = Path(__file__).resolve().parent.parent / "lesson_verses" / "kjv.tsv"


@pytest.fixture(scope="module")
def bible():
    return Bible(KJV)


def labels(question):
    return [p.label for p in find_passages(question)[1]]


def test_trailing_list_is_removed_from_the_prompt():
    prompt, passages = find_passages("What does the psalmist say? Psalm 23:1, 2; Romans 8:28.")
    assert prompt == "What does the psalmist say?"
    assert [p.label for p in passages] == ["Psalm 23:1, 2", "Romans 8:28"]


def test_imperative_prompt_keeps_its_period():
    assert find_passages("Describe the scene. Genesis 2:8.")[0] == "Describe the scene."


def test_book_carries_forward():
    assert labels("Why? Exodus 20:8; 31:13, 16.") == ["Exodus 20:8", "Exodus 31:13, 16"]


def test_comma_between_books_splits():
    assert labels("Who? Isaiah 40:8, Matthew 24:35–37.") == ["Isaiah 40:8", "Matthew 24:35–37"]


def test_reference_inside_the_sentence_stays_and_is_expanded():
    prompt, passages = find_passages("As Micah 6:8 says, what is required?")
    assert prompt == "As Micah 6:8 says, what is required?"
    assert [p.label for p in passages] == ["Micah 6:8"]


def test_inside_reference_ignored_when_a_list_ends_the_question():
    assert labels("As Hebrews 4:12 shows, what else? John 1:1.") == ["John 1:1"]


def test_note_with_a_comma_stays_in_the_label():
    passages = find_passages("What is sown? Mark 4:3 (compare verse 14, and see the margin).")[1]
    assert [(p.label, p.locations) for p in passages] == [
        ("Mark 4:3 (compare verse 14, and see the margin)", "4:3")]


def test_list_continues_after_a_note():
    assert labels("Why? Ruth 1:16 (last part); Micah 6:8.") == [
        "Ruth 1:16 (last part)", "Micah 6:8"]


def test_nbsp_in_numbered_book():
    [p] = find_passages("Who? 1\xa0John 1:1.")[1]
    assert p.book == "1 John"
    assert printed_label(p) == "1\xa0John 1:1"


def test_printed_label_uses_en_dash():
    [p] = split_passages("John 14:1-3")
    assert printed_label(p) == "John 14:1–3"


def test_no_references():
    assert find_passages("What did you learn this week?") == ("What did you learn this week?", [])


def test_prose_reference_is_not_a_passage():
    assert labels("Read the story in Ruth chapters 1 and 2.") == []


@pytest.mark.parametrize("ref, keys", [
    ("Jude 14, 15", [(1, 14), (1, 15)]),                       # one-chapter book
    ("Acts 4:36-5:2", [(4, 36), (4, 37)] + [(4, v) for v in range(38, 177)] + [(5, 1), (5, 2)]),
    ("Colossians 3:25-4:1, 5", None),                          # checked below
])
def test_verse_keys(ref, keys):
    [p] = split_passages(ref)
    if keys is not None:
        assert verse_keys(p) == keys


def test_bare_verse_after_a_cross_chapter_range_is_in_the_new_chapter(bible):
    [p] = split_passages("Colossians 3:25-4:1, 5")
    assert [v for v, _ in bible.verses(p)] == [25, 1, 5]
    assert bible.verses(p)[-1][1].startswith("Walk in wisdom")


def test_whole_chapter_returns_only_real_verses(bible):
    [p] = split_passages("Psalm 117")
    assert [v for v, _ in bible.verses(p)] == [1, 2]


def test_verse_text(bible):
    [p] = split_passages("Genesis 1:1")
    assert bible.verses(p) == [(1, "In the beginning God created the heaven and the earth.")]


def test_unknown_verse_returns_nothing(bible):
    [p] = split_passages("Jude 30")
    assert bible.verses(p) == []


def test_kjv_has_every_book(bible):
    from lesson_verses.scripture import BOOKS
    for book in BOOKS:
        [p] = split_passages(f"{book} 1:1")
        assert bible.verses(p), book
