"""README.md, README.zh-Hans.md and the app text must stay in step; text_sync.py explains the rules.

The first group of tests runs the checks on the repository. The second group
proves the checks fire, by editing a small synthetic project the way a real
README or app text edit would and expecting the right report.
"""

import json
from pathlib import Path

import pytest

import text_sync as sync


def fail(problems, stale=()):
    pytest.fail(sync.format_report(list(problems), list(stale)), pytrace=False)


@pytest.fixture(scope="module")
def state():
    for readme in (sync.Sources().readme_en, sync.Sources().readme_zh):
        if not readme.exists():
            pytest.fail(f"{readme.name} is missing; README.md and README.zh-Hans.md must both exist", pytrace=False)
    return sync.load_state()


def test_chinese_readme_mirrors_english_structure(state):
    problems = sync.check_structure(state)
    if problems:
        fail(problems)


def test_style_and_dictionary_rules(state):
    problems = sync.check_style(state) + sync.check_dictionary(state)
    if problems:
        fail(problems)


def test_readme_changes_reach_chinese_readme_and_app_text(state):
    if sync.check_structure(state):
        pytest.skip("README.zh-Hans.md differs in structure; see test_chinese_readme_mirrors_english_structure")
    problems, stale = sync.check_sync(state)
    if problems or stale:
        fail(problems, stale)


# A synthetic project with every kind of link: a quoted sentence, a reworded one, terms and a dictionary.

README_EN = """# Demo

Demo keeps things light. **Set it and forget it.**

## Settings

| Control | What it does |
| --- | --- |
| Entity filtering | **On by default.** Sends only the entities your chosen dashboards use. |
| Idle mode | **Off by default.** Stops live updates after a while with no activity. |

## Notes

Always reload the dashboard after you make a change.

Press **Go** to begin, or **Start over** to clear the result.
"""

README_ZH = """# Demo

[English](README.md) | 简体中文

Demo 让一切更轻量。**设置好就不用管了。**

## 设置

| 控件 | 作用 |
| --- | --- |
| 实体筛选 | **默认开启。** 只发送你所选仪表盘用到的实体。 |
| 空闲模式 | **默认关闭。** 一段时间没有操作后，会停止实时更新。 |

## 注意事项

每次修改后，请务必刷新仪表盘。

点击 **开始** 开始，或点击 **重新开始** 清除结果。
"""

STRINGS_EN = {
    "title": "Demo",
    "entity": {"switch": {"entity_filtering": {"name": "Entity filtering"}, "idle_updates": {"name": "Idle mode"}}},
    "options": {
        "step": {
            "filters": {
                "description": "Turn on the features you want.\n\n- **Entity filtering:** Sends only the entities your chosen dashboards use.\n- **Idle mode:** Stops live updates after a period with no activity."
            }
        }
    },
}

STRINGS_ZH = {
    "title": "Demo",
    "entity": {"switch": {"entity_filtering": {"name": "实体筛选"}, "idle_updates": {"name": "空闲模式"}}},
    "options": {
        "step": {
            "filters": {
                "description": "开启你需要的功能。\n\n- **实体筛选**：只发送你所选仪表盘用到的实体。\n- **空闲模式**：一段时间没有操作后，会停止实时更新。"
            }
        }
    },
}

DICTIONARY = """/* Fixture dictionary. */
const chinese = {
  "Always reload the dashboard after you make a change.": "每次修改后，请务必刷新仪表盘。",
  "Go": "开始",
  "Start over": "重新开始",
};
"""

CARD = 'const labels = ["Always reload the dashboard after you make a change.", "Go", "Start over"];\n'
ONLY_EN = "Sends only the entities your chosen dashboards use."
ONLY_ZH = "只发送你所选仪表盘用到的实体。"


def write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def project(tmp_path):
    """A synthetic project whose README, Chinese README and app text agree and are recorded."""
    write(tmp_path, "README.md", README_EN)
    write(tmp_path, "README.zh-Hans.md", README_ZH)
    write(tmp_path, "custom_components/loona/strings.json", json.dumps(STRINGS_EN, indent=2, ensure_ascii=False) + "\n")
    write(tmp_path, "custom_components/loona/translations/zh-Hans.json", json.dumps(STRINGS_ZH, indent=2, ensure_ascii=False) + "\n")
    write(tmp_path, "custom_components/loona/frontend/i18n.js", DICTIONARY)
    write(tmp_path, "custom_components/loona/frontend/settings-card.js", CARD)
    seed = {"version": 1, "readme_only_terms": ["Set it and forget it.", "On by default.", "Off by default."]}
    write(tmp_path, "text_sync.json", json.dumps(seed))
    assert sync.accept(load(tmp_path), zh_unchanged=False, reviewed=True) == 0
    return tmp_path


def load(root: Path) -> sync.State:
    return sync.load_state(sync.Sources(root=root, manifest=root / "text_sync.json"))


def run(root: Path, **options):
    problems, stale = sync.run_checks(load(root), **options)
    return problems, stale


def tags(items):
    return {item.split("]")[0] + "]" for item in items}


def edit(root: Path, name: str, old: str, new: str) -> None:
    path = root / name
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{old!r} must appear exactly once in {name}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def test_project_in_step_is_clean(project):
    assert run(project) == ([], [])


def test_english_edit_without_chinese_or_app_edit_is_flagged(project):
    edit(project, "README.md", ONLY_EN, "Sends just the entities your chosen dashboards use.")
    problems, stale = run(project)
    assert tags(problems) == {"[baseline]", "[sentences]"}
    assert "has NOT changed" in "\n".join(problems)
    assert "strings.json" in "\n".join(problems)


def test_edit_that_reaches_chinese_and_app_only_needs_recording(project):
    new_en, new_zh = "Sends just the entities your chosen dashboards use.", "仅发送你所选仪表盘用到的实体。"
    edit(project, "README.md", ONLY_EN, new_en)
    edit(project, "README.zh-Hans.md", ONLY_ZH, new_zh)
    edit(project, "custom_components/loona/strings.json", ONLY_EN, new_en)
    edit(project, "custom_components/loona/translations/zh-Hans.json", ONLY_ZH, new_zh)
    problems, stale = run(project)
    assert problems == [] and tags(stale) == {"[baseline]", "[sentences]"}
    assert sync.accept(load(project), zh_unchanged=False, reviewed=False) == 0
    assert run(project) == ([], [])


def test_english_only_edit_needs_the_explicit_flag(project):
    edit(project, "README.md", "Demo keeps things light.", "Demo keeps everything light.")
    problems, _ = run(project)
    assert tags(problems) == {"[baseline]"}
    assert sync.accept(load(project), zh_unchanged=False, reviewed=False) == 1
    assert run(project)[0], "a refused accept must not record the edit"
    assert sync.accept(load(project), zh_unchanged=True, reviewed=False) == 0
    assert run(project) == ([], [])


def test_renamed_term_is_flagged_wherever_it_is_still_used(project):
    edit(project, "README.md", "| Idle mode |", "| Quiet mode |")
    edit(project, "README.zh-Hans.md", "| 空闲模式 |", "| 安静模式 |")
    problems, _ = run(project)
    text = "\n".join(problems)
    assert tags(problems) == {"[terms]"}
    assert "'Quiet mode'" in text and "'Idle mode'" in text and "strings.json" in text


def test_chinese_term_must_match_the_app(project):
    edit(project, "README.zh-Hans.md", "| 空闲模式 |", "| 闲置模式 |")
    problems, _ = run(project)
    assert tags(problems) == {"[terms]"} and "空闲模式" in "\n".join(problems)


def test_app_sentence_that_rewords_the_readme_must_be_reviewed(project):
    edit(project, "custom_components/loona/strings.json", "after a period with", "after a period of")
    problems, _ = run(project)
    assert tags(problems) == {"[adapted]"}
    edit(project, "custom_components/loona/strings.json", "after a period of", "after a period with")
    assert run(project) == ([], [])


def test_adapted_pair_can_be_confirmed_after_review(project):
    edit(project, "custom_components/loona/strings.json", "after a period with", "after a period of")
    assert sync.accept(load(project), zh_unchanged=False, reviewed=False) == 1
    assert sync.accept(load(project), zh_unchanged=False, reviewed=True) == 0
    assert run(project) == ([], [])


def test_chinese_that_differs_for_identical_english_is_flagged(project):
    edit(project, "custom_components/loona/translations/zh-Hans.json", ONLY_ZH, "仅发送你所选仪表盘用到的实体。")
    problems, _ = run(project)
    assert "[sentences]" in tags(problems)


def test_banned_character_is_flagged(project):
    edit(project, "README.md", "Demo keeps things light.", "Demo keeps things light \N{EM DASH} really.")
    assert "[style]" in tags(run(project)[0])


def test_chinese_bold_next_to_punctuation_is_flagged(project):
    edit(project, "README.zh-Hans.md", "**默认开启。** 只发送", "**默认开启。**只发送")
    assert "[style]" in tags(run(project)[0])


def test_hard_wrapped_paragraph_is_flagged(project):
    edit(project, "README.md", "Demo keeps things light.", "Demo keeps\nthings light.")
    assert "[style]" in tags(run(project)[0])


def test_dictionary_entry_without_a_matching_literal_is_flagged(project):
    edit(project, "custom_components/loona/frontend/settings-card.js", '"Start over"', '"Begin again"')
    problems, _ = run(project)
    assert tags(problems) == {"[dictionary]"} and "Start over" in problems[0]


def test_duplicate_dictionary_key_is_flagged(project):
    edit(project, "custom_components/loona/frontend/i18n.js", '  "Go": "开始",\n', '  "Go": "开始",\n  "Go": "走",\n')
    assert tags(run(project)[0]) == {"[dictionary]"}


def test_unbalanced_structure_is_reported_once(project):
    edit(project, "README.md", "## Notes\n", "## Notes\n\nA new paragraph.\n")
    problems, stale = run(project)
    assert tags(problems) == {"[structure]"} and len(problems) == 1 and stale == []


def test_readme_term_missing_from_the_app_is_flagged(project):
    edit(project, "README.md", "Press **Go** to begin", "Press **Go** to begin with the **Frobnicate** panel")
    edit(project, "README.zh-Hans.md", "点击 **开始** 开始", "点击 **开始** 并通过 **折腾** 面板开始")
    assert "'Frobnicate'" in "\n".join(run(project)[0])


def test_app_label_missing_from_the_readme_is_flagged(project):
    edit(project, "custom_components/loona/strings.json", '"name": "Idle mode"', '"name": "Quiet mode"')
    edit(project, "custom_components/loona/translations/zh-Hans.json", '"name": "空闲模式"', '"name": "安静模式"')
    assert "'Quiet mode'" in "\n".join(run(project)[0])


# Building blocks.


@pytest.mark.parametrize(
    "text,unpaired",
    [
        ("**默认关闭。**其他选项卡", True),
        ("**默认关闭。** 其他选项卡", False),
        ("选择**所选用户**或**所有用户**。", False),
        ("**实体筛选：**只发送", True),
        ("**foo bar **", True),
        ("how *fast* a page feels", False),
        ("`sensor.kitchen_*` stays code", False),
    ],
)
def test_unpaired_emphasis(text, unpaired):
    assert sync.unpaired_emphasis(text) is unpaired


def test_sentences_drop_labels_and_markdown():
    assert sync.sentences("**Off by default.** Prevents loading [card files](x). Reload now.", "en") == [
        "Prevents loading card files.",
        "Reload now.",
    ]
    assert sync.sentences("- **实体筛选**：只发送实体。请刷新。", "zh") == ["只发送实体。", "请刷新。"]


def test_diff_hashes_finds_changed_and_removed_units():
    assert sync.diff_hashes(["a", "b", "c"], ["a", "x", "c"]) == ({1}, [])
    assert sync.diff_hashes(["a", "b", "c"], ["a", "c"]) == (set(), [1])
    assert sync.diff_hashes(["a", "c"], ["a", "b", "c"]) == ({1}, [])
