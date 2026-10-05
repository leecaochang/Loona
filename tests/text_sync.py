"""Keep README.md, README.zh-Hans.md and the text inside the app in step.

README.md is the source of truth for product terms and prose. This module turns
that rule into checks that fail, with a list of what to update, as soon as the
three drift apart:

* structure: README.zh-Hans.md has exactly the structure of README.md.
* baseline: every README.md heading, paragraph, list item and table cell is
  fingerprinted in text_sync.json. Editing one fails the check until the
  matching README.zh-Hans.md unit has changed too, and the report lists the app
  strings that quote or resemble it.
* sentences: a sentence the app quotes from README.md word for word (form
  descriptions, card help, benchmark report) must stay identical in both places,
  and the Chinese must stay identical in README.zh-Hans.md and the app.
* terms: every UI term README.md puts in bold or in a table label column must
  exist in the app with the same Chinese, and every settings, button and sensor
  label in the app must appear in README.md.
* style: no dashes, arrows or emojis, Markdown emphasis that pairs up under
  CommonMark (Chinese punctuation next to the bold markers is a common trap) and
  one source line per paragraph.
* dictionary: no duplicate, dead or placeholder-mismatched entries in the
  Chinese dictionary in frontend/i18n.js.

After the Chinese README and the app text follow a README.md change, record the
new baseline with:

    venv/bin/python tests/text_sync.py --accept

Add --zh-unchanged when an English edit, such as a typo fix, needs no Chinese
edit, and --reviewed once you have checked that the app sentences which reword a
README.md sentence still say the right thing. Without arguments the script
prints the same report as the test, and --coverage shows which README.md units
the app text covers.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).with_name("text_sync.json")
ACCEPT_COMMAND = "venv/bin/python tests/text_sync.py --accept"

# Dashes, arrows, dingbats and emoji are not allowed in source or documentation.
BANNED_RANGES = ((0x2013, 0x2014), (0x2190, 0x21FF), (0x2600, 0x27BF), (0x2B00, 0x2BFF), (0xFE0F, 0xFE0F), (0x1F000, 0x1FAFF))
HEADING = re.compile(r"^(#{1,6}) (.+)$")
LIST_ITEM = re.compile(r"^\s*([-*]|\d+\.) (.*)$")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]*)\)")
BOLD = re.compile(r"\*\*(.+?)\*\*")
DICTIONARY_LINE = re.compile(r'^  ("(?:\\.|[^"\\])*"): ("(?:\\.|[^"\\])*"),?$')
SWITCHER = re.compile(r"English.*简体中文|简体中文.*English")
PLACEHOLDER = re.compile(r"\{\w+\}")
CJK_QUOTES = "\N{LEFT DOUBLE QUOTATION MARK}\N{RIGHT DOUBLE QUOTATION MARK}\N{LEFT SINGLE QUOTATION MARK}\N{RIGHT SINGLE QUOTATION MARK}\N{LEFT CORNER BRACKET}\N{RIGHT CORNER BRACKET}"
ELLIPSIS = "\N{HORIZONTAL ELLIPSIS}" * 2
MIN_WORDS = 5
ADAPTED_EN = 0.75
ADAPTED_ZH = 0.8
RELATED_OVERLAP = 0.6

# strings.json leaves whose text is a label the README must mention.
LABEL_PATHS = re.compile(
    r"^(?:entity\.[a-z_]+\.[a-z_]+\.name"
    r"|options\.step\.(?:filters|idle|resource_preview)\.data\.[a-z_]+"
    r"|selector\.[a-z_]+\.options\.[a-z_]+)$"
)


@dataclass(frozen=True)
class Sources:
    """Where the checked files live; tests use the repository, dry runs use a copy."""

    root: Path = ROOT
    manifest: Path = MANIFEST

    @property
    def component(self) -> Path:
        return self.root / "custom_components" / "loona"

    @property
    def readme_en(self) -> Path:
        return self.root / "README.md"

    @property
    def readme_zh(self) -> Path:
        return self.root / "README.zh-Hans.md"

    def relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def short(self, path: Path) -> str:
        """Path as shown in reports: relative to the integration folder when inside it."""
        try:
            return path.relative_to(self.component).as_posix()
        except ValueError:
            return self.relative(path)


@dataclass(frozen=True)
class Unit:
    """One heading, paragraph, list item, table cell or code block of a README."""

    kind: str
    where: str
    text: str
    line: int


@dataclass(frozen=True)
class AppString:
    """An English string of the app with its Chinese translation and its home."""

    ref: str
    en: str
    zh: str
    path: str = ""
    home: str = ""


@dataclass
class State:
    """Everything the checks read, loaded once."""

    sources: Sources
    en_units: list[Unit]
    zh_units: list[Unit]
    en_switcher: Unit | None
    zh_switcher: Unit | None
    layout_problems: list[str]
    app: list[AppString]
    dictionary: list[AppString]
    duplicate_keys: list[str]
    manifest: dict | None


# ---------------------------------------------------------------------------
# Parsing and text helpers
# ---------------------------------------------------------------------------


def parse_readme(markdown: str, name: str) -> tuple[list[Unit], list[str]]:
    """Split Markdown into units, and report layout that breaks the repo rules."""
    lines = markdown.split("\n")
    units: list[Unit] = []
    problems: list[str] = []
    path: list[str] = []
    ordinals: dict[tuple[str, str], int] = {}
    previous = ""

    def add(kind: str, text: str, number: int, label: str | None = None) -> None:
        section = " > ".join(path)
        if label is None:
            count = ordinals[(section, kind)] = ordinals.get((section, kind), 0) + 1
            label = f"{kind} {count}"
        units.append(Unit(kind, f"{section} ({label})", text, number))

    index = 0
    while index < len(lines):
        line, number = lines[index], index + 1
        if not line.strip():
            previous, index = "", index + 1
            continue
        if line.startswith("```"):
            end = index + 1
            while end < len(lines) and not lines[end].startswith("```"):
                end += 1
            add("code", "\n".join(lines[index : end + 1]), number)
            previous, index = "", end + 1
            continue
        heading = HEADING.match(line)
        if heading:
            level = len(heading[1])
            path[level - 1 :] = [heading[2].strip()]
            add(f"h{level}", heading[2].strip(), number, "heading")
            previous = "heading"
        elif line.startswith("|"):
            row = 0
            while index < len(lines) and lines[index].startswith("|"):
                if row != 1:
                    cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                    for column, cell in enumerate(cells):
                        label = f"table header, column {column + 1}" if row == 0 else f"table row '{cells[0]}', column {column + 1}"
                        add(f"cell{row}.{column}", cell, index + 1, label)
                row, index = row + 1, index + 1
            previous = "table"
            continue
        elif item := LIST_ITEM.match(line):
            add("number" if item[1][0].isdigit() else "bullet", item[2].strip(), number)
            previous = "item"
        else:
            if previous in ("para", "item", "table"):
                problems.append(f"[style] {name}:{number}: text continues the line above; keep one source line per paragraph")
            add("para", line.strip(), number)
            previous = "para"
        index += 1
    return units, problems


def split_switcher(units: list[Unit]) -> tuple[Unit | None, list[Unit]]:
    """Remove the language switcher line that follows the title, if there is one."""
    if len(units) > 1 and units[1].kind == "para" and SWITCHER.search(units[1].text):
        return units[1], units[:1] + units[2:]
    return None, units


def banned_character(line: str) -> str | None:
    """The first dash, arrow, dingbat or emoji in the line, if any."""
    for char in line:
        if any(low <= ord(char) <= high for low, high in BANNED_RANGES):
            return char
    return None


def digest(text: str) -> str:
    """Whitespace-insensitive fingerprint of a unit."""
    return hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()[:12]


def excerpt(text: str, limit: int = 80) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def strip_label(text: str) -> str:
    """Drop a leading bold label such as '**Off by default.**' or '**Idle mode:**'."""
    match = re.match(r"^\*\*(?P<label>[^*]+)\*\*(?P<colon>[:：])?\s*", text)
    if match and (match["colon"] or match["label"][-1] in ".:。："):
        return text[match.end() :]
    return text


def clean_en(text: str) -> str:
    text = LINK.sub(r"\1", strip_label(text.strip()))
    return " ".join(text.replace("**", "").replace("`", "").replace("\N{RIGHT SINGLE QUOTATION MARK}", "'").split())


def clean_zh(text: str) -> str:
    """Chinese compares without spaces, quotes or Markdown markers; a placeholder reads as an ellipsis."""
    text = PLACEHOLDER.sub(ELLIPSIS, LINK.sub(r"\1", strip_label(text.strip())))
    return "".join(re.sub(f"[*`{CJK_QUOTES}\"']", "", text).split())


def sentences(text: str, lang: str) -> list[str]:
    """Normalized sentences of a unit or app string, one source line at a time."""
    found: list[str] = []
    for line in text.split("\n"):
        line = re.sub(r"^\s*[-*]\s+", "", line)
        if lang == "en":
            parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])", clean_en(line))
        else:
            parts = re.split(r"(?<=[。！？])", clean_zh(line))
        found.extend(part for part in parts if part)
    return found


def eligible(sentence: str) -> bool:
    """Short fragments are labels or filler, not quotes worth tracking."""
    return len(sentence.split()) >= MIN_WORDS


def inline_code(text: str) -> list[str]:
    return re.findall(r"`[^`\n]+`", text)


def link_targets(text: str) -> list[str]:
    return [target for _, target in LINK.findall(text)]


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", text.lower()))


def has_term(corpus: str, term: str) -> bool:
    """Whole-word occurrence, so 'Go' does not match 'Google'."""
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", corpus) is not None


@dataclass
class EmphasisRun:
    """A run of '*' characters and whether CommonMark lets it open or close emphasis."""

    can_open: bool
    can_close: bool
    original: int
    length: int


def emphasis_runs(text: str, legacy: bool) -> list[EmphasisRun]:
    """Delimiter runs of a line; 'legacy' is the punctuation rule before CommonMark 0.31 added symbols."""

    def is_space(char: str) -> bool:
        return char == "" or char.isspace() or unicodedata.category(char) == "Zs"

    def is_punct(char: str) -> bool:
        if char == "":
            return False
        category = unicodedata.category(char)
        if legacy:
            return category[0] == "P" or (ord(char) < 128 and not char.isalnum() and not char.isspace())
        return category[0] in "PS"

    runs = []
    for match in re.finditer(r"\*+", text):
        start, end = match.span()
        before = text[start - 1] if start else ""
        after = text[end] if end < len(text) else ""
        can_open = not is_space(after) and (not is_punct(after) or is_space(before) or is_punct(before))
        can_close = not is_space(before) and (not is_punct(before) or is_space(after) or is_punct(after))
        runs.append(EmphasisRun(can_open, can_close, end - start, end - start))
    return runs


def runs_pair_up(runs: list[EmphasisRun]) -> bool:
    """CommonMark's process-emphasis algorithm: True when every '*' ends up in a matched pair."""
    index = 0
    while index < len(runs):
        closer = runs[index]
        if not closer.can_close or closer.length == 0:
            index += 1
            continue
        found = None
        for back in range(index - 1, -1, -1):
            opener = runs[back]
            if not opener.can_open or opener.length == 0:
                continue
            total = opener.original + closer.original
            if (opener.can_close or closer.can_open) and total % 3 == 0 and not (opener.original % 3 == 0 and closer.original % 3 == 0):
                continue
            found = back
            break
        if found is None:
            index += 1
            continue
        opener = runs[found]
        used = 2 if opener.length >= 2 and closer.length >= 2 else 1
        opener.length -= used
        closer.length -= used
        for between in runs[found + 1 : index]:
            between.length = 0
        if closer.length == 0:
            index += 1
    return all(run.length == 0 for run in runs)


def unpaired_emphasis(text: str) -> bool:
    """True when bold or italic markers do not pair up, under either generation of CommonMark's rules."""
    masked = re.sub(r"`[^`\n]*`", lambda match: "`" * len(match.group()), text)
    return not all(runs_pair_up(emphasis_runs(masked, legacy)) for legacy in (True, False))


# ---------------------------------------------------------------------------
# App text
# ---------------------------------------------------------------------------


def json_leaves(text: str) -> dict[str, tuple[str, int]]:
    """Dotted path to (value, line number) for a document written with indent=2."""
    data = json.loads(text)
    leaves: dict[str, str] = {}

    def walk(node: dict, prefix: str = "") -> None:
        for key, value in node.items():
            if isinstance(value, dict):
                walk(value, prefix + key + ".")
            else:
                leaves[prefix + key] = value

    walk(data)
    lines: dict[str, int] = {}
    stack: list[str] = []
    for number, line in enumerate(text.split("\n"), 1):
        match = re.match(r'^( *)"((?:\\.|[^"\\])*)": ', line)
        if match:
            depth = len(match[1]) // 2 - 1
            del stack[depth:]
            stack.append(json.loads('"' + match[2] + '"'))
            lines[".".join(stack)] = number
    return {path: (value, lines.get(path, 0)) for path, value in leaves.items()}


def load_dictionary(i18n: str) -> tuple[list[AppString], list[str], tuple[int, int]]:
    """Entries of the Chinese dictionary, duplicate keys, and its character span."""
    start = i18n.index("const chinese = {")
    end = i18n.index("\n};\n", start)
    first = i18n.count("\n", 0, start) + 1
    entries: list[AppString] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    for offset, line in enumerate(i18n[start:end].split("\n")):
        match = DICTIONARY_LINE.match(line)
        if not match:
            continue
        key, value = json.loads(match[1]), json.loads(match[2])
        if key in seen:
            duplicates.append(key)
        seen.add(key)
        entries.append(AppString(f"frontend/i18n.js:{first + offset}", key, value, home="frontend/i18n.js"))
    return entries, duplicates, (start, end)


def load_app_strings(sources: Sources) -> tuple[list[AppString], list[AppString], list[str]]:
    component = sources.component
    i18n = (component / "frontend" / "i18n.js").read_text(encoding="utf-8")
    dictionary, duplicates, _ = load_dictionary(i18n)
    english_text = (component / "strings.json").read_text(encoding="utf-8")
    chinese_text = (component / "translations" / "zh-Hans.json").read_text(encoding="utf-8")
    chinese = json_leaves(chinese_text)
    forms: list[AppString] = []
    for path, (value, line) in json_leaves(english_text).items():
        translated = chinese[path][0]
        ref, home = f"strings.json:{line} {path}", f"strings.json {path}"
        if "\n" in value and value.count("\n") == translated.count("\n"):
            forms.extend(AppString(ref, a, b, path, home) for a, b in zip(value.split("\n"), translated.split("\n")) if a.strip())
        else:
            forms.append(AppString(ref, value, translated, path, home))
    return dictionary + forms, dictionary, duplicates


def find_lines(files: list[Path], needles: list[str], sources: Sources, limit: int = 6) -> list[str]:
    """file:line of every source line that contains one of the needles."""
    hits: list[str] = []
    for path in files:
        if not path.exists():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            if any(needle and needle in line for needle in needles):
                hits.append(f"{sources.short(path)}:{number}")
    return hits[:limit]


def app_files(sources: Sources) -> list[Path]:
    """Files that hold the app's English text."""
    component = sources.component
    return [component / "strings.json", *sorted((component / "frontend").glob("*.js")), *sorted(component.glob("*.py"))]


def chinese_files(sources: Sources) -> list[Path]:
    component = sources.component
    return [component / "frontend" / "i18n.js", component / "translations" / "zh-Hans.json", sources.readme_zh]


def literal_forms(text: str) -> set[str]:
    """The ways a string can appear as a complete JavaScript or Python literal."""
    double = json.dumps(text, ensure_ascii=False)
    single = "'" + double[1:-1].replace('\\"', '"').replace("'", "\\'") + "'"
    return {double, single, f"`{text}`", f'"{text}"', f"'{text}'"}


def needles(text: str) -> list[str]:
    return [text, json.dumps(text, ensure_ascii=False)[1:-1], text.replace("'", "\N{RIGHT SINGLE QUOTATION MARK}")]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_state(sources: Sources = Sources()) -> State:
    en_units, en_layout = parse_readme(sources.readme_en.read_text(encoding="utf-8"), "README.md")
    zh_units, zh_layout = parse_readme(sources.readme_zh.read_text(encoding="utf-8"), "README.zh-Hans.md")
    en_switcher, en_units = split_switcher(en_units)
    zh_switcher, zh_units = split_switcher(zh_units)
    app, dictionary, duplicates = load_app_strings(sources)
    manifest = json.loads(sources.manifest.read_text(encoding="utf-8")) if sources.manifest.exists() else None
    return State(sources, en_units, zh_units, en_switcher, zh_switcher, en_layout + zh_layout, app, dictionary, duplicates, manifest)


# ---------------------------------------------------------------------------
# Checks. Each returns problems; "stale" problems are cleared by --accept.
# ---------------------------------------------------------------------------


def unit_run(units: list[Unit], low: int, high: int) -> str:
    """Line span of the run of same-kind units around units[low:high]; identical kinds are interchangeable."""
    last = min(max(high - 1, low), len(units) - 1)
    first = min(low, last)
    kind = units[first].kind
    while first > 0 and units[first - 1].kind == kind:
        first -= 1
    while last + 1 < len(units) and units[last + 1].kind == kind:
        last += 1
    return f"lines {units[first].line}-{units[last].line}" if first != last else f"line {units[first].line}"


def check_structure(state: State) -> list[str]:
    """README.zh-Hans.md mirrors README.md unit for unit."""
    problems: list[str] = []
    if state.zh_switcher is None or "(README.md)" not in state.zh_switcher.text:
        problems.append("[structure] README.zh-Hans.md needs a language switcher line after the title that links to README.md")
    if state.en_switcher is not None and "(README.zh-Hans.md)" not in state.en_switcher.text:
        problems.append("[structure] The language switcher in README.md must link to README.zh-Hans.md")
    en_kinds, zh_kinds = [unit.kind for unit in state.en_units], [unit.kind for unit in state.zh_units]
    if en_kinds != zh_kinds:
        matcher = difflib.SequenceMatcher(None, en_kinds, zh_kinds, autojunk=False)
        tag, i1, i2, j1, j2 = next(op for op in matcher.get_opcodes() if op[0] != "equal")
        en_run = unit_run(state.en_units, i1, i2)
        zh_run = unit_run(state.zh_units, j1, j2)
        what = {
            "insert": f"README.zh-Hans.md has {j2 - j1} more unit(s) than README.md among {zh_run}",
            "delete": f"README.md has {i2 - i1} more unit(s) than README.zh-Hans.md among {en_run}",
            "replace": f"README.md {en_run} and README.zh-Hans.md {zh_run} have a different layout",
        }[tag]
        where = state.en_units[min(i1, len(state.en_units) - 1)].where
        return problems + [
            f"[structure] {what} (near '{where}'). Give README.zh-Hans.md the same structure as README.md."
        ]
    for en, zh in zip(state.en_units, state.zh_units):
        where = f"README.md:{en.line} / README.zh-Hans.md:{zh.line} ({en.where})"
        if en.kind == "code" and en.text != zh.text:
            problems.append(f"[structure] Code block differs: {where}")
        if inline_code(en.text) != inline_code(zh.text):
            problems.append(f"[structure] Inline code differs, it is not translated: {where}")
        if link_targets(en.text) != link_targets(zh.text):
            problems.append(f"[structure] Link targets differ: {where}")
        if en.text.count("**") != zh.text.count("**"):
            problems.append(f"[structure] Bold markers differ: {where}")
        if en.text.replace("**", "").count("*") != zh.text.replace("**", "").count("*"):
            problems.append(f"[structure] Italic markers differ: {where}")
    return problems


def is_label_cell(unit: Unit) -> bool:
    """First column of a table body row: a UI label rather than prose."""
    match = re.fullmatch(r"cell(\d+)\.0", unit.kind)
    return match is not None and int(match[1]) >= 2


def readme_terms(state: State) -> tuple[list[tuple[str, str]], list[str]]:
    """Aligned (English, Chinese) UI terms: bold spans and table label columns."""
    pairs: list[tuple[str, str]] = []
    problems: list[str] = []
    for en, zh in zip(state.en_units, state.zh_units):
        if is_label_cell(en):
            left, right = en.text.split(", "), zh.text.split("、")
            if len(left) != len(right):
                problems.append(
                    f"[terms] Label cell lists {len(left)} names in README.md:{en.line} "
                    f"but {len(right)} in README.zh-Hans.md:{zh.line}"
                )
            pairs.extend(zip(left, right))
        pairs.extend(zip(BOLD.findall(en.text), BOLD.findall(zh.text)))
    return pairs, problems


def term_entries(pairs: list[tuple[str, str]], skip: set[str]) -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    for en, zh in pairs:
        if en not in skip:
            seen.setdefault(en, zh)
    return sorted(seen.items())


def check_terms(state: State) -> tuple[list[str], list[str]]:
    """README.md terms exist in the app with the same Chinese, and the reverse for labels."""
    manifest = state.manifest or {}
    skip = set(manifest.get("readme_only_terms", []))
    pairs, problems = readme_terms(state)
    stale: list[str] = []
    for en, zh in term_entries(pairs, skip):
        matches = [a for a in state.app if has_term(a.en, en)]
        if not matches:
            problems.append(
                f"[terms] README.md uses the term '{en}' but no app string contains it. Add it to the app, rename it "
                f"to match, or list it under readme_only_terms in tests/text_sync.json if it is README-only emphasis."
            )
            continue
        exact = [a for a in matches if a.en == en]
        want = clean_zh(zh)
        if exact:
            if want not in {clean_zh(a.zh) for a in exact}:
                problems.append(
                    f"[terms] '{en}' is '{exact[0].zh}' in the app ({exact[0].ref}) "
                    f"but README.zh-Hans.md says '{zh}'. Use the same Chinese in both."
                )
        elif not any(want in clean_zh(a.zh) for a in matches):
            problems.append(
                f"[terms] README.zh-Hans.md says '{zh}' for '{en}', but the Chinese of the app strings that use "
                f"'{en}' never contains it (for example {matches[0].ref})."
            )
    en_text = "\n".join(clean_en(u.text) for u in state.en_units if u.kind != "code")
    zh_text = "\n".join(clean_zh(u.text) for u in state.zh_units if u.kind != "code")
    exempt = set(manifest.get("labels_not_in_readme", []))
    for a in state.app:
        if not a.path or not LABEL_PATHS.match(a.path) or a.path in exempt:
            continue
        label = re.sub(r"\s*\(.*\)$", "", a.en)
        if not has_term(en_text, label):
            problems.append(f"[terms] The app label '{a.en}' ({a.ref}) does not appear in README.md. Add it to README.md or rename the app label.")
        elif clean_zh(re.sub(r"（.*）$", "", a.zh)) not in zh_text:
            problems.append(f"[terms] The Chinese label '{a.zh}' ({a.ref}) does not appear in README.zh-Hans.md.")
    baseline = {tuple(pair) for pair in manifest.get("terms", [])}
    current = set(term_entries(pairs, skip))
    if state.manifest is not None and current != baseline:
        added, removed = sorted(current - baseline), sorted(baseline - current)
        keep = set(manifest.get("terms_keep", []))
        current_en = [en for en, _ in current]
        for en, zh in removed:
            if en in keep or len(en.split()) < 2 or any(en in other for other in current_en):
                continue
            places = find_lines([*app_files(state.sources), state.sources.readme_en, *chinese_files(state.sources)], needles(en) + needles(zh), state.sources)
            if any(a.en == en or en in a.en for a in state.app) or places:
                problems.append(
                    f"[terms] README.md no longer uses the term '{en}' ('{zh}' in Chinese) but it is still used at: "
                    + ", ".join(places or ["the app text"])
                    + ". Rename it there too, or list it under terms_keep in tests/text_sync.json."
                )
        new_zh, old_zh = dict(added), dict(removed)
        notes = [f"'{en}' is now '{new_zh[en]}' in Chinese (was '{old_zh[en]}')" for en in sorted(new_zh.keys() & old_zh.keys())]
        notes += [f"'{en}' was added" for en in sorted(new_zh.keys() - old_zh.keys())]
        notes += [f"'{en}' was removed" for en in sorted(old_zh.keys() - new_zh.keys())]
        stale.append("[terms] README.md terms changed since the last sync: " + "; ".join(notes) + ".")
    return problems, stale


def readme_sentence_index(units: list[Unit], lang: str) -> dict[str, list[int]]:
    index: dict[str, list[int]] = {}
    for position, unit in enumerate(units):
        if unit.kind != "code" and not unit.kind.startswith("h"):
            for sentence in sentences(unit.text, lang):
                index.setdefault(sentence, []).append(position)
    return index


def app_sentence_index(app: list[AppString], lang: str) -> dict[str, list[AppString]]:
    index: dict[str, list[AppString]] = {}
    for a in app:
        for sentence in sentences(a.en if lang == "en" else a.zh, lang):
            index.setdefault(sentence, []).append(a)
    return index


def discover_pins(state: State) -> list[dict[str, str]]:
    """README.md sentences that an app string repeats word for word."""
    readme = readme_sentence_index(state.en_units, "en")
    pins: dict[str, str] = {}
    for a in state.app:
        for sentence in sentences(a.en, "en"):
            if eligible(sentence) and sentence in readme:
                pins.setdefault(sentence, a.home)
    order = sorted(pins, key=lambda sentence: min(readme[sentence]))
    return [{"en": sentence, "app": pins[sentence]} for sentence in order]


def check_exact_links(state: State) -> tuple[list[str], list[str]]:
    """Sentences the app repeats from README.md stay identical, and so does their Chinese."""
    problems: list[str] = []
    stale: list[str] = []
    readme_en = readme_sentence_index(state.en_units, "en")
    app_en = app_sentence_index(state.app, "en")
    sources = state.sources
    for pin in (state.manifest or {}).get("pins", []):
        sentence = pin["en"]
        in_readme, in_app = sentence in readme_en, sentence in app_en
        if in_readme and in_app:
            continue
        places = find_lines(app_files(sources), needles(sentence), sources)
        if in_readme:
            problems.append(
                f"[sentences] The app no longer says what README.md:{state.en_units[readme_en[sentence][0]].line} says "
                f"(it was at {pin['app']}):\n  {sentence}\n  Restore this wording in the app"
                + (f" ({', '.join(places)})" if places else "")
                + ", or change README.md and README.zh-Hans.md instead."
            )
        elif in_app:
            near = difflib.get_close_matches(sentence, list(readme_en), n=1, cutoff=0.5)
            problems.append(
                f"[sentences] README.md no longer has this sentence, but the app still does ({', '.join(places) or pin['app']}):\n"
                f"  app: {sentence}\n"
                + (f"  README.md now: {near[0]}\n" if near else "")
                + "  Update the app text and its Chinese to the README.md wording."
            )
        else:
            stale.append(f"[sentences] Recorded link is gone from README.md and the app: {excerpt(sentence)}")
    for a in state.app:
        english, chinese = sentences(a.en, "en"), sentences(a.zh, "zh")
        if len(english) != len(chinese):
            continue
        for sentence, translated in zip(english, chinese):
            if not eligible(sentence) or sentence not in readme_en:
                continue
            pool = {z for position in readme_en[sentence] for z in sentences(state.zh_units[position].text, "zh")}
            if translated not in pool:
                closest = difflib.get_close_matches(translated, sorted(pool), n=1, cutoff=0.0)
                problems.append(
                    f"[sentences] The English is identical in README.md and the app ({a.ref}) but the Chinese differs:\n"
                    f"  app: {translated}\n  README.zh-Hans.md: {closest[0] if closest else '(nothing)'}\n"
                    "  Use the same Chinese in both."
                )
    return problems, stale


def bigrams(text: str) -> set[str]:
    return {text[index : index + 2] for index in range(len(text) - 1)}


def long_enough_zh(sentence: str) -> bool:
    return len(sentence) >= 8


def near_copies(readme: dict[str, list[int]], app: dict[str, list[AppString]], lang: str) -> list[tuple[str, str]]:
    """(README sentence, app sentence) pairs that are alike without being identical."""
    keep, parts, threshold = (eligible, words, ADAPTED_EN) if lang == "en" else (long_enough_zh, bigrams, ADAPTED_ZH)
    readme_parts = {sentence: parts(sentence) for sentence in readme if keep(sentence)}
    pairs: list[tuple[str, str]] = []
    for sentence in app:
        if sentence in readme or not keep(sentence):
            continue
        own = parts(sentence)
        for candidate, other in readme_parts.items():
            if len(own & other) / max(1, len(own | other)) < 0.5:
                continue
            if difflib.SequenceMatcher(None, candidate, sentence, autojunk=False).ratio() >= threshold:
                pairs.append((candidate, sentence))
    return sorted(pairs)


def adapted_pairs(state: State) -> set[tuple[str, str, str]]:
    found: set[tuple[str, str, str]] = set()
    for lang, units in (("en", state.en_units), ("zh", state.zh_units)):
        for readme_sentence, app_sentence in near_copies(readme_sentence_index(units, lang), app_sentence_index(state.app, lang), lang):
            found.add((lang, readme_sentence, app_sentence))
    return found


def check_adapted(state: State, reviewed: bool = False) -> tuple[list[str], list[str]]:
    """App sentences that reword a README sentence were reviewed, and both sides still match that review."""
    problems: list[str] = []
    stale: list[str] = []
    recorded = {(item["lang"], item["readme"], item["app"]) for item in (state.manifest or {}).get("adapted", [])}
    current = adapted_pairs(state)
    names = {"en": "README.md", "zh": "README.zh-Hans.md"}
    units = {"en": state.en_units, "zh": state.zh_units}
    indexes = {lang: (readme_sentence_index(units[lang], lang), app_sentence_index(state.app, lang)) for lang in units}
    messages: list[str] = []
    readme_en = indexes["en"][0]
    lost = {pin["en"] for pin in (state.manifest or {}).get("pins", []) if pin["en"] not in readme_en}
    for lang, readme_sentence, app_sentence in sorted(current - recorded):
        readme, app = indexes[lang]
        if any(sentence in lost for a in app[app_sentence] for sentence in sentences(a.en, "en")):
            continue  # already reported as an exact link that README.md changed under
        earlier = [item for item in recorded if item[0] == lang and (item[1] == readme_sentence or item[2] == app_sentence)]
        lines = [
            f"[adapted] An app sentence rewords a {names[lang]} sentence"
            + (", and one of them changed since the pair was reviewed:" if earlier else " and no review of the pair is recorded:"),
            f"  {names[lang]}:{units[lang][readme[readme_sentence][0]].line}: {readme_sentence}",
            f"  app ({app[app_sentence][0].ref}): {app_sentence}",
        ]
        for _, old_readme, old_app in earlier:
            lines.append(f"  reviewed before as {names[lang]}: {old_readme}" if old_readme != readme_sentence else f"  reviewed before as app: {old_app}")
        lines.append("  Make the app text follow the README, or confirm the difference is intended with --reviewed.")
        messages.append("\n".join(lines))
    involved = {sentence for _, readme_sentence, app_sentence in current for sentence in (readme_sentence, app_sentence)}
    for lang, readme_sentence, app_sentence in sorted(recorded - current):
        readme, app = indexes[lang]
        in_readme, in_app = readme_sentence in readme, app_sentence in app
        if in_readme and not in_app and readme_sentence not in involved:
            messages.append(
                f"[adapted] The app sentence reviewed against {names[lang]}:{units[lang][readme[readme_sentence][0]].line} changed beyond recognition:\n"
                f"  {names[lang]}: {readme_sentence}\n  was in the app: {app_sentence}\n  Update it, or confirm with --reviewed."
            )
        elif in_app and not in_readme and app_sentence not in involved:
            messages.append(
                f"[adapted] {names[lang]} changed beyond recognition under an app sentence that rewords it ({app[app_sentence][0].ref}):\n"
                f"  was in {names[lang]}: {readme_sentence}\n  app: {app_sentence}\n  Review the app text, or confirm with --reviewed."
            )
        else:
            stale.append(f"[adapted] Recorded pair is gone: {excerpt(readme_sentence)}")
    (stale if reviewed else problems).extend(messages)
    return problems, stale


def check_dictionary(state: State) -> list[str]:
    problems = [f"[dictionary] Duplicate key in frontend/i18n.js, the later entry silently wins: {excerpt(key)}" for key in state.duplicate_keys]
    component = state.sources.component
    i18n = (component / "frontend" / "i18n.js").read_text(encoding="utf-8")
    _, _, (start, end) = load_dictionary(i18n)
    corpus = i18n[:start] + i18n[end:]
    for path in sorted(component.rglob("*")):
        if path.suffix in (".js", ".py") and path.name != "i18n.js":
            corpus += "\n" + path.read_text(encoding="utf-8")
    for entry in state.dictionary:
        if not any(form in corpus for form in literal_forms(entry.en)):
            problems.append(
                f"[dictionary] {entry.ref} translates a string the app no longer contains, so the Chinese is lost "
                f"when the English was reworded: {excerpt(entry.en)}"
            )
        if sorted(PLACEHOLDER.findall(entry.en)) != sorted(PLACEHOLDER.findall(entry.zh)):
            problems.append(f"[dictionary] {entry.ref} uses different placeholders in English and Chinese: {excerpt(entry.en)}")
    return problems


def style_files(sources: Sources) -> list[Path]:
    files = [sources.readme_en, sources.readme_zh]
    for base in (sources.component, sources.root / "tests"):
        for path in sorted(base.rglob("*")):
            if path.suffix in {".py", ".js", ".mjs", ".json", ".md", ".html", ".css"} and "fixtures" not in path.parts and "__pycache__" not in path.parts:
                files.append(path)
    return files


def check_style(state: State) -> list[str]:
    problems = list(state.layout_problems)
    sources = state.sources
    for path in style_files(sources):
        for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            if char := banned_character(line):
                problems.append(f"[style] {sources.relative(path)}:{number}: U+{ord(char):04X} is not allowed (no dashes, arrows or emoji)")
            if path.suffix == ".md" and line != line.rstrip():
                problems.append(f"[style] {sources.relative(path)}:{number}: trailing whitespace")
    for name, units in (("README.md", state.en_units), ("README.zh-Hans.md", state.zh_units)):
        for unit in units:
            if unit.kind != "code" and unpaired_emphasis(unit.text):
                problems.append(f"[style] {name}:{unit.line}: bold or italic markers do not pair up when rendered. Put a space after a closing ** that follows punctuation: {excerpt(unit.text, 60)}")
    component = sources.component
    for name in ("strings.json", "translations/zh-Hans.json"):
        for path, (value, line) in json_leaves((component / name).read_text(encoding="utf-8")).items():
            if any(unpaired_emphasis(part) for part in value.split("\n")):
                problems.append(f"[style] custom_components/loona/{name}:{line}: bold markers in {path} do not pair up when rendered")
    return problems


def diff_hashes(old: list[str], new: list[str]) -> tuple[set[int], list[int]]:
    """Indexes of new units that differ from the baseline, and old units that vanished."""
    changed: set[int] = set()
    removed: list[int] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag in ("replace", "insert"):
            changed.update(range(j1, j2))
        if tag == "delete":
            removed.extend(range(i1, i2))
        elif tag == "replace" and (i2 - i1) > (j2 - j1):
            removed.extend(range(i1 + (j2 - j1), i2))
    return changed, removed


def related_app_text(state: State, text: str, limit: int = 5) -> list[tuple[float, AppString, str]]:
    """App sentences that resemble this README.md unit without matching any README.md sentence."""
    unit_words = words(clean_en(text))
    in_sync = readme_sentence_index(state.en_units, "en")
    found: list[tuple[float, AppString, str]] = []
    for a in state.app:
        for sentence in sentences(a.en, "en"):
            sentence_words = words(sentence)
            if sentence not in in_sync and len(sentence_words) >= 4 and unit_words:
                overlap = len(sentence_words & unit_words) / len(sentence_words)
                if overlap >= RELATED_OVERLAP:
                    found.append((overlap, a, sentence))
    found.sort(key=lambda item: -item[0])
    unique: list[tuple[float, AppString, str]] = []
    for item in found:
        if all(item[2] != other[2] for other in unique):
            unique.append(item)
    return unique[:limit]


def check_baseline(state: State, zh_unchanged: bool = False) -> tuple[list[str], list[str]]:
    """Every README.md edit must reach README.zh-Hans.md and be recorded."""
    manifest = state.manifest
    if manifest is None or "units" not in manifest:
        return [], [f"[baseline] No baseline is recorded in tests/text_sync.json. Create it with: {ACCEPT_COMMAND}"]
    old_en = [unit["en"] for unit in manifest["units"]]
    old_zh = [unit["zh"] for unit in manifest["units"]]
    new_en = [digest(unit.text) for unit in state.en_units]
    new_zh = [digest(unit.text) for unit in state.zh_units]
    changed_en, removed_en = diff_hashes(old_en, new_en)
    changed_zh, removed_zh = diff_hashes(old_zh, new_zh)
    problems: list[str] = []
    stale: list[str] = []
    for position in sorted(changed_en):
        en, zh = state.en_units[position], state.zh_units[position]
        lines = [f"README.md:{en.line} changed ({en.where}):", f"  now: {excerpt(en.text, 400)}"]
        if position in changed_zh:
            lines.append(f"  README.zh-Hans.md:{zh.line} changed too.")
        else:
            lines.append(f"  README.zh-Hans.md:{zh.line} has NOT changed, update it: {excerpt(zh.text, 400)}")
            lines.append(f"  (If the Chinese is still right, record the edit with: {ACCEPT_COMMAND} --zh-unchanged)")
        related = related_app_text(state, en.text)
        if related:
            lines.append("  App text that quotes or resembles it (update it and its Chinese):")
            for overlap, a, sentence in related:
                home = a.ref.split(" ")[0]
                also = [place for place in find_lines(app_files(state.sources), needles(sentence), state.sources) if place != home]
                lines.append(f"    {a.ref} [{overlap:.0%} of its words]: {excerpt(sentence, 100)}" + (f" (also at {', '.join(also)})" if also else ""))
        else:
            lines.append("  No app text resembles it.")
        message = "\n".join(lines)
        if position in changed_zh or zh_unchanged:
            stale.append("[baseline] " + message + ("\n  (accepted as needing no Chinese change)" if position not in changed_zh else ""))
        else:
            problems.append("[baseline] " + message)
    for position in removed_en:
        unit = manifest["units"][position]
        (stale if removed_zh else problems).append(f"[baseline] README.md no longer has: {unit['text']}")
    for position in sorted(changed_zh - changed_en):
        zh = state.zh_units[position]
        stale.append(f"[baseline] README.zh-Hans.md:{zh.line} changed on its own ({state.en_units[position].where}): {excerpt(zh.text, 120)}")
    return problems, stale


def check_layout(state: State) -> list[str]:
    """Problems that stand on their own: structure, style and the Chinese dictionary."""
    return check_structure(state) + check_style(state) + check_dictionary(state)


def check_sync(state: State, zh_unchanged: bool = False, reviewed: bool = False) -> tuple[list[str], list[str]]:
    """Terms, quoted and reworded sentences, and the baseline. Needs README.zh-Hans.md to mirror README.md."""
    problems: list[str] = []
    stale: list[str] = []
    for found, recorded in (
        check_terms(state),
        check_exact_links(state),
        check_adapted(state, reviewed),
        check_baseline(state, zh_unchanged),
    ):
        problems += found
        stale += recorded
    return problems, stale


def run_checks(state: State, zh_unchanged: bool = False, reviewed: bool = False) -> tuple[list[str], list[str]]:
    """(problems that need an edit, stale records that --accept clears)."""
    layout = check_layout(state)
    if check_structure(state):
        return layout, []
    problems, stale = check_sync(state, zh_unchanged, reviewed)
    return layout + problems, stale


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def build_manifest(state: State) -> dict:
    previous = state.manifest or {}
    skip = set(previous.get("readme_only_terms", []))
    pairs, _ = readme_terms(state)
    return {
        "version": 1,
        "units": [
            {"en": digest(en.text), "zh": digest(zh.text), "text": excerpt(en.text, 60)}
            for en, zh in zip(state.en_units, state.zh_units)
        ],
        "pins": discover_pins(state),
        "adapted": [{"lang": lang, "readme": readme_sentence, "app": app_sentence} for lang, readme_sentence, app_sentence in sorted(adapted_pairs(state))],
        "terms": [list(pair) for pair in term_entries(pairs, skip)],
        "readme_only_terms": previous.get("readme_only_terms", []),
        "labels_not_in_readme": previous.get("labels_not_in_readme", []),
        "terms_keep": previous.get("terms_keep", []),
    }


def dump_manifest(manifest: dict) -> str:
    """One entry per line, so a README edit shows up as a small diff."""
    chunks = []
    for key, value in manifest.items():
        if isinstance(value, list):
            body = ",\n".join("    " + json.dumps(item, ensure_ascii=False) for item in value)
            chunks.append(f'  {json.dumps(key)}: [\n{body}\n  ]' if value else f"  {json.dumps(key)}: []")
        else:
            chunks.append(f"  {json.dumps(key)}: {json.dumps(value)}")
    return "{\n" + ",\n".join(chunks) + "\n}\n"


def accept(state: State, zh_unchanged: bool, reviewed: bool) -> int:
    problems, _ = run_checks(state, zh_unchanged, reviewed)
    if problems:
        print_report(problems, [], "Not recorded, fix these first:")
        return 1
    state.sources.manifest.write_text(dump_manifest(build_manifest(state)), encoding="utf-8")
    print(f"Recorded {len(state.en_units)} README units in {state.sources.relative(state.sources.manifest)}.")
    return 0


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def format_report(problems: list[str], stale: list[str], heading: str = "README and app text are out of step:") -> str:
    parts = [heading, *problems, *stale]
    if stale and not problems:
        parts.append(
            f"\nREADME.md, README.zh-Hans.md and the app text agree. Record the new baseline with: {ACCEPT_COMMAND}"
        )
    elif stale:
        parts.append(f"\nWhen everything above is fixed, record the new baseline with: {ACCEPT_COMMAND}")
    return "\n\n".join(parts)


def print_report(problems: list[str], stale: list[str], heading: str = "README and app text are out of step:") -> None:
    print(format_report(problems, stale, heading))


def coverage(state: State) -> str:
    """How far the checks reach into README.md, from enforced links down to the Chinese README alone."""
    skip = set((state.manifest or {}).get("readme_only_terms", []))
    app = app_sentence_index(state.app, "en")
    reworded = {readme_sentence for lang, readme_sentence, _ in adapted_pairs(state) if lang == "en"}
    prose = [
        position
        for position, unit in enumerate(state.en_units)
        if unit.kind != "code" and not unit.kind.startswith("h") and not unit.kind.startswith("cell0.")
    ]
    tiers: dict[str, list[int]] = {"quoted": [], "reworded": [], "term": [], "similar": [], "none": []}
    for position in prose:
        unit = state.en_units[position]
        found = sentences(unit.text, "en")
        if any(eligible(sentence) and sentence in app for sentence in found):
            tier = "quoted"
        elif any(sentence in reworded for sentence in found):
            tier = "reworded"
        elif is_label_cell(unit) or any(term not in skip for term in BOLD.findall(unit.text)):
            tier = "term"
        elif related_app_text(state, unit.text, 1):
            tier = "similar"
        else:
            tier = "none"
        tiers[tier].append(position)
    rows = [
        f"README.md has {len(prose)} paragraphs, list items and table cells. Each is tracked against README.zh-Hans.md. Beyond that:",
        f"  {len(tiers['quoted']):3} are quoted by the app word for word and must stay identical",
        f"  {len(tiers['reworded']):3} are reworded by the app in reviewed pairs",
        f"  {len(tiers['term']):3} carry a UI term or label the app also uses",
        f"  {len(tiers['similar']):3} only resemble app text, which is listed when they change",
        f"  {len(tiers['none']):3} have no app counterpart",
    ]
    if tiers["none"]:
        rows.append("Units with no app counterpart:")
        rows += [f"  README.md:{state.en_units[position].line} {excerpt(state.en_units[position].text, 70)}" for position in tiers["none"]]
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--accept", action="store_true", help="record the current README and app text as the new baseline")
    parser.add_argument("--zh-unchanged", action="store_true", help="with --accept: allow English edits that need no Chinese edit")
    parser.add_argument("--reviewed", action="store_true", help="with --accept: confirm the adapted app sentences in the report were reviewed against README.md")
    parser.add_argument("--coverage", action="store_true", help="show how much of README.md the app text covers")
    args = parser.parse_args(argv)
    if (args.zh_unchanged or args.reviewed) and not args.accept:
        parser.error("--zh-unchanged and --reviewed only apply together with --accept")
    state = load_state()
    if args.coverage:
        print(coverage(state))
        return 0
    if args.accept:
        return accept(state, args.zh_unchanged, args.reviewed)
    problems, stale = run_checks(state)
    if problems or stale:
        print_report(problems, stale)
        return 1
    print("README, Chinese README and app text are in step.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
