from pathlib import Path

from apt_helper.catalog import (
    CATALOG,
    PracticeGroup,
    find_apt_name,
)


def test_catalog_has_all_known_apt_entries() -> None:
    assert len(CATALOG) == 74


def test_catalog_ids_and_source_paths_are_unique() -> None:
    catalog_ids = [problem.catalog_id.casefold() for problem in CATALOG]
    source_paths = [problem.relative_source_path for problem in CATALOG]

    assert len(catalog_ids) == len(set(catalog_ids))
    assert len(source_paths) == len(set(source_paths))


def test_form_slug_can_differ_from_java_class() -> None:
    problem = find_apt_name("dnamax")

    assert problem is not None
    assert problem.class_name == "DNAMaxNucleotide"


def test_visible_apt_name_resolves_case_insensitively() -> None:
    problem = find_apt_name("dnamaxnucleotide")

    assert problem is not None
    assert problem.slug == "dnamax"


def test_assigned_sets_are_not_shifted_by_practice_groups() -> None:
    pair_down = find_apt_name("pairdown")
    unique_tree = find_apt_name("uniquetree")

    assert pair_down is not None and pair_down.set_number == 5
    assert unique_tree is not None and unique_tree.set_number == 10


def test_catalog_has_eleven_assigned_sets_and_three_practice_groups() -> None:
    assigned_sets = {
        problem.set_number for problem in CATALOG if problem.set_number is not None
    }
    practice_counts = {
        group: sum(problem.practice_group is group for problem in CATALOG)
        for group in PracticeGroup
    }

    assert assigned_sets == set(range(1, 12))
    assert practice_counts == {
        PracticeGroup.QUIZ_1: 6,
        PracticeGroup.QUIZ_2: 5,
        PracticeGroup.QUIZ_2_DISCUSSION: 3,
    }


def test_quiz_practice_has_a_separate_source_tree(tmp_path: Path) -> None:
    problem = find_apt_name("endofwords")

    assert problem is not None
    assert problem.practice_group is PracticeGroup.QUIZ_1
    assert problem.details == "level 1"
    assert problem.source_path(tmp_path) == (
        tmp_path / "apts" / "quiz1" / "EndOfWords.java"
    )


def test_unqualified_duplicate_prefers_the_assigned_apt(tmp_path: Path) -> None:
    assigned = find_apt_name("sortedleaves")
    discussion = find_apt_name("quiz2-discussion/sortedleaves")

    assert assigned is not None and assigned.set_number == 9
    assert discussion is not None
    assert discussion.practice_group is PracticeGroup.QUIZ_2_DISCUSSION
    assert discussion.source_path(tmp_path) == (
        tmp_path / "apts" / "quiz2-discussion" / "SortedLeaves.java"
    )
    assert assigned.catalog_id != discussion.catalog_id
