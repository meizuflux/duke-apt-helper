"""The CompSci 201 Fall 2026 assigned and practice APT catalog."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final


class PracticeGroup(StrEnum):
    QUIZ_1 = "quiz1"
    QUIZ_2 = "quiz2"
    QUIZ_2_DISCUSSION = "quiz2-discussion"


@dataclass(frozen=True)
class AptProblem:
    slug: str
    class_name: str
    details: str = ""
    set_number: int | None = None
    practice_group: PracticeGroup | None = None

    def __post_init__(self) -> None:
        if (self.set_number is None) == (self.practice_group is None):
            raise ValueError(
                "an APT must belong to exactly one assigned set or practice group"
            )

    @property
    def group_id(self) -> str:
        if self.set_number is not None:
            return f"set{self.set_number}"
        assert self.practice_group is not None
        return self.practice_group.value

    @property
    def catalog_id(self) -> str:
        """A stable local identity; unlike the remote slug, this is unique."""
        return f"{self.group_id}/{self.slug}"

    @property
    def relative_source_path(self) -> Path:
        return Path("apts") / self.group_id / f"{self.class_name}.java"

    def source_path(self, root: Path) -> Path:
        return root / self.relative_source_path


def assigned(
    set_number: int, slug: str, class_name: str, *, details: str = ""
) -> AptProblem:
    return AptProblem(slug, class_name, details, set_number=set_number)


def practice(
    group: PracticeGroup,
    slug: str,
    class_name: str,
    *,
    details: str = "",
) -> AptProblem:
    return AptProblem(slug, class_name, details, practice_group=group)


CATALOG: Final[tuple[AptProblem, ...]] = (
    assigned(1, "totality", "Totality"),
    assigned(1, "accesslevel", "AccessLevel", details="WOTO"),
    assigned(1, "gravity", "Gravity", details="WOTO"),
    assigned(1, "starter", "Starter"),
    assigned(1, "circlescountry", "CirclesCountry", details="challenge/discuss"),
    assigned(2, "dnamax", "DNAMaxNucleotide"),
    assigned(2, "sandwichbar", "SandwichBar"),
    assigned(2, "simplewordsearch", "SimpleWordGame", details="woto"),
    assigned(2, "txtmsg", "TxMsg", details="woto"),
    assigned(2, "common", "Common", details="challenge"),
    assigned(3, "stringcuts", "StringCuts"),
    assigned(3, "truespace", "TrueSpace"),
    assigned(3, "counterattack", "CounterAttack", details="woto"),
    assigned(3, "bigword", "BigWord", details="woto"),
    assigned(3, "prefixcode", "PrefixCode", details="challenge"),
    assigned(4, "anonymous", "Anonymous", details="woto"),
    assigned(4, "membercheck", "MemberCheck"),
    assigned(4, "encryption", "Encryption", details="some class woto"),
    assigned(4, "soccerleagues", "SoccerLeagues"),
    assigned(4, "isomorphicwords", "IsomorphicWords", details="challenge"),
    practice(PracticeGroup.QUIZ_1, "endofwords", "EndOfWords", details="level 1"),
    practice(PracticeGroup.QUIZ_1, "measuring", "Measuring", details="level 1"),
    practice(PracticeGroup.QUIZ_1, "compound", "Compound", details="level 2"),
    practice(PracticeGroup.QUIZ_1, "heavychar", "HeavyChar", details="level 2"),
    practice(PracticeGroup.QUIZ_1, "simplehash", "SimpleHash", details="level 3"),
    practice(PracticeGroup.QUIZ_1, "splitcount", "SplitCount", details="level 3"),
    assigned(5, "pairdown", "PairDown", details="woto"),
    assigned(5, "setaside", "SetAside", details="woto"),
    assigned(5, "closet", "Closet"),
    assigned(5, "anagram", "Aaagmnrs"),
    assigned(5, "thesaurus", "Thesaurus", details="big challenge"),
    assigned(6, "listcount", "ListCount", details="woto"),
    assigned(6, "listsum", "ListSum", details="woto"),
    assigned(6, "listsequal", "ListsEqual"),
    assigned(6, "alphalength", "AlphaLength", details="woto"),
    assigned(6, "mergelists", "MergeLists", details="challenge"),
    assigned(7, "liststretch", "ListStretch"),
    assigned(7, "doublelist", "DoubleList"),
    assigned(7, "listlastfirst", "ListLastFirst"),
    assigned(7, "removemin", "RemoveMin"),
    assigned(7, "list2long", "List2Long"),
    assigned(7, "listparity", "ListParity"),
    assigned(7, "sortedlistremoval", "SortedListRemoval", details="challenge"),
    assigned(8, "lengthsort", "LengthSort"),
    assigned(8, "sortbyfreqs", "SortByFreqs"),
    assigned(8, "sortedfreqs", "SortedFreqs"),
    assigned(8, "medaltable", "MedalTable"),
    assigned(8, "syllabsort", "SyllableSort", details="challenge"),
    assigned(8, "tournamentrank", "TournamentRanker", details="challenge"),
    assigned(9, "treecount", "TreeCount"),
    assigned(9, "pathsum", "PathSum"),
    assigned(9, "levelcount", "LevelCount"),
    assigned(9, "heightlabel", "HeightLabel"),
    assigned(9, "sortedleaves", "SortedLeaves", details="challenge"),
    practice(PracticeGroup.QUIZ_2, "ezsort", "EZSort", details="level 1"),
    practice(PracticeGroup.QUIZ_2, "nonleafsum", "InternalSum", details="level 1"),
    practice(PracticeGroup.QUIZ_2, "simplelist", "SimpleList", details="level 1"),
    practice(PracticeGroup.QUIZ_2, "combolist", "ComboList", details="level 2"),
    practice(PracticeGroup.QUIZ_2, "longestpath", "LongestPath", details="level 3"),
    practice(
        PracticeGroup.QUIZ_2_DISCUSSION,
        "lettercountsort",
        "LetterCountSort",
    ),
    practice(PracticeGroup.QUIZ_2_DISCUSSION, "addat", "AddAt"),
    practice(PracticeGroup.QUIZ_2_DISCUSSION, "sortedleaves", "SortedLeaves"),
    assigned(10, "uniquetree", "UniqueTreeValues"),
    assigned(10, "treetighten", "TreeTighten"),
    assigned(10, "leaftrails", "LeafTrails", details="use TreeMap"),
    assigned(10, "leafcollector", "LeafCollector", details="loop AND recursion"),
    assigned(10, "allpaths", "AllPaths", details="challenge"),
    assigned(11, "huff", "HuffmanDecoding"),
    assigned(11, "friendscore", "FriendScore"),
    assigned(11, "olympic", "OlympicCandles", details="greedy"),
    assigned(
        11,
        "bstcount",
        "BSTCount",
        details="memoize, bit.ly/201fall19-apt-hah (copy paste)",
    ),
    assigned(11, "internet", "Internet", details="encouraged, challenging, graphs"),
    assigned(11, "ograph", "Ograph"),
    assigned(11, "wordladder", "WordLadder", details="bfs in class, challenge"),
)


BY_CATALOG_ID: Final[dict[str, AptProblem]] = {
    problem.catalog_id.casefold(): problem for problem in CATALOG
}


def _aliases(problem: AptProblem) -> tuple[str, ...]:
    return problem.slug.casefold(), problem.class_name.casefold()


def find_apt_name(name: str) -> AptProblem | None:
    """Resolve a catalog ID, class name, or form slug.

    When a practice APT repeats an assigned APT, the unqualified name resolves to
    the assigned version. Practice entries remain available through catalog IDs
    such as ``quiz2-discussion/sortedleaves``.
    """
    normalized = name.strip().casefold()
    exact = BY_CATALOG_ID.get(normalized)
    if exact is not None:
        return exact
    matches = [problem for problem in CATALOG if normalized in _aliases(problem)]
    assigned_matches = [
        problem for problem in matches if problem.set_number is not None
    ]
    if len(assigned_matches) == 1:
        return assigned_matches[0]
    return matches[0] if len(matches) == 1 else None
