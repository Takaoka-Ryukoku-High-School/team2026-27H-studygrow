import calendar
import json
from datetime import date
from pathlib import Path
from uuid import uuid4

import flet as ft


DATA_FILE = Path.home() / ".daily_note_tasks.json"
ASSIGNMENTS_FILE = Path.home() / ".studygrow_assignments.json"
EVENTS_FILE = Path.home() / ".studygrow_events.json"
VOCABULARY_FILE = Path.home() / ".studygrow_vocabulary.json"
GREEN = "#2E6654"
GREEN_LIGHT = "#E2EDE5"
PAPER = "#F6F5EF"
INK = "#202C2A"
MUTED = "#77807B"
CORAL = "#CF6048"


def load_tasks():
    try:
        tasks = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if isinstance(tasks, list):
            return [
                task
                for task in tasks
                if isinstance(task, dict)
                and isinstance(task.get("id"), str)
                and isinstance(task.get("text"), str)
                and isinstance(task.get("done"), bool)
            ]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def save_tasks(tasks):
    DATA_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def load_assignments():
    try:
        assignments = json.loads(ASSIGNMENTS_FILE.read_text(encoding="utf-8"))
        if isinstance(assignments, list):
            return [
                assignment
                for assignment in assignments
                if isinstance(assignment, dict)
                and isinstance(assignment.get("id"), str)
                and isinstance(assignment.get("text"), str)
                and isinstance(assignment.get("done"), bool)
            ]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def save_assignments(assignments):
    ASSIGNMENTS_FILE.write_text(
        json.dumps(assignments, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_events():
    try:
        events = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
        if isinstance(events, list):
            return [
                event
                for event in events
                if isinstance(event, dict)
                and isinstance(event.get("id"), str)
                and isinstance(event.get("text"), str)
                and isinstance(event.get("date"), str)
                and _is_calendar_date(event["date"])
            ]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def _is_calendar_date(value):
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def save_events(events):
    EVENTS_FILE.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")


def load_vocabulary():
    try:
        vocabulary = json.loads(VOCABULARY_FILE.read_text(encoding="utf-8"))
        if isinstance(vocabulary, list):
            return [
                entry
                for entry in vocabulary
                if isinstance(entry, dict)
                and isinstance(entry.get("id"), str)
                and isinstance(entry.get("word"), str)
                and isinstance(entry.get("meaning"), str)
                and isinstance(entry.get("known"), bool)
            ]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def save_vocabulary(vocabulary):
    VOCABULARY_FILE.write_text(
        json.dumps(vocabulary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main(page: ft.Page):
    page.title = "今日の段取り | ToDo"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = PAPER
    page.padding = 24
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO

    tasks = load_tasks()
    assignments = load_assignments()
    events = load_events()
    vocabulary = load_vocabulary()
    current_filter = "all"
    current_section = "plan"
    current_plan_view = "tasks"
    vocabulary_index = 0
    vocabulary_answer_visible = False
    visible_month = date.today().replace(day=1)
    selected_date = date.today()

    task_input = ft.TextField(
        hint_text="次にやることは？",
        expand=True,
        autofocus=True,
        border_radius=6,
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor="#FFFEFA",
        text_size=15,
        on_submit=lambda event: add_task(event),
    )
    assignment_input = ft.TextField(
        hint_text="課題名（例：数学ワーク p.10）",
        expand=True,
        border_radius=6,
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor="#FFFEFA",
        text_size=15,
        on_submit=lambda event: add_assignment(event),
    )
    assignment_status = ft.Text(size=12, color=MUTED)
    assignment_list = ft.Column(spacing=0)
    assignment_count = ft.Text(color=MUTED, size=12)
    calendar_event_input = ft.TextField(
        hint_text="予定を入力",
        expand=True,
        border_radius=6,
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor="#FFFEFA",
        text_size=15,
        on_submit=lambda event: add_calendar_event(event),
    )
    calendar_event_status = ft.Text(size=12, color=MUTED)
    calendar_event_list = ft.Column(spacing=0)
    vocabulary_word_input = ft.TextField(
        label="英単語",
        expand=True,
        border_radius=6,
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor="#FFFEFA",
    )
    vocabulary_meaning_input = ft.TextField(
        label="日本語の意味",
        expand=True,
        border_radius=6,
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor="#FFFEFA",
    )
    vocabulary_example_input = ft.TextField(
        label="例文（任意）",
        expand=True,
        border_radius=6,
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor="#FFFEFA",
    )
    vocabulary_example_meaning_input = ft.TextField(
        label="例文の日本語訳（任意）",
        expand=True,
        border_radius=6,
        border_color="#D4DED5",
        focused_border_color=GREEN,
        bgcolor="#FFFEFA",
    )
    vocabulary_status = ft.Text(size=12, color=MUTED)
    vocabulary_review_status = ft.Text(size=12, color=MUTED)
    vocabulary_word_label = ft.Text(size=28, color=INK, weight=ft.FontWeight.W_600)
    vocabulary_meaning_label = ft.Text(size=17, color=GREEN)
    vocabulary_example_label = ft.Text(size=14, color=INK)
    vocabulary_example_meaning_label = ft.Text(size=13, color=MUTED)
    vocabulary_progress = ft.Text(size=12, color=MUTED)
    vocabulary_entry_list = ft.Column(spacing=0)
    task_list = ft.Column(spacing=0)
    task_count = ft.Text(color=MUTED, size=12)
    progress_label = ft.Text(color=MUTED, size=11)
    section_title = ft.Text(size=38, color=INK, weight=ft.FontWeight.W_600)
    section_description = ft.Text(size=13, color=MUTED)
    clear_done_button = ft.TextButton(
        "完了した項目を削除",
        icon=ft.Icons.DELETE_OUTLINE,
        style=ft.ButtonStyle(color=CORAL),
        on_click=lambda event: clear_done(event),
    )
    filter_buttons = {}

    def persist():
        try:
            save_tasks(tasks)
            progress_label.value = f"{sum(task['done'] for task in tasks)} / {len(tasks)} 件 完了"
        except OSError:
            progress_label.value = "保存できませんでした。書き込み権限をご確認ください。"

    def set_filter(value):
        nonlocal current_filter
        current_filter = value
        render()

    def add_task(event):
        text = task_input.value.strip()
        if not text:
            return
        tasks.insert(0, {"id": str(uuid4()), "text": text, "done": False})
        task_input.value = ""
        persist()
        set_filter("all")

    def toggle_task(task_id):
        for task in tasks:
            if task["id"] == task_id:
                task["done"] = not task["done"]
                break
        persist()
        render()

    def delete_task(task_id):
        tasks[:] = [task for task in tasks if task["id"] != task_id]
        persist()
        render()

    def clear_done(event):
        tasks[:] = [task for task in tasks if not task["done"]]
        persist()
        render()

    def add_assignment(event):
        text = assignment_input.value.strip()
        if not text:
            assignment_status.value = "課題名を入力してください。"
            assignment_status.color = CORAL
            page.update()
            return

        updated_assignments = [
            {"id": str(uuid4()), "text": text, "done": False},
            *assignments,
        ]
        try:
            save_assignments(updated_assignments)
        except OSError:
            assignment_status.value = "課題を保存できませんでした。書き込み権限をご確認ください。"
            assignment_status.color = CORAL
            page.update()
            return

        assignments[:] = updated_assignments
        assignment_input.value = ""
        assignment_status.value = "課題を追加しました。"
        assignment_status.color = GREEN
        render_assignments()

    def toggle_assignment(assignment_id):
        for assignment in assignments:
            if assignment["id"] == assignment_id:
                assignment["done"] = not assignment["done"]
                break
        try:
            save_assignments(assignments)
        except OSError:
            for assignment in assignments:
                if assignment["id"] == assignment_id:
                    assignment["done"] = not assignment["done"]
                    break
            assignment_status.value = "課題の状態を保存できませんでした。書き込み権限をご確認ください。"
            assignment_status.color = CORAL
            page.update()
            return
        render_assignments()

    def delete_assignment(assignment_id):
        updated_assignments = [
            assignment
            for assignment in assignments
            if assignment["id"] != assignment_id
        ]
        try:
            save_assignments(updated_assignments)
        except OSError:
            assignment_status.value = "課題を削除できませんでした。書き込み権限をご確認ください。"
            assignment_status.color = CORAL
            page.update()
            return

        assignments[:] = updated_assignments
        assignment_status.value = "課題を削除しました。"
        assignment_status.color = GREEN
        render_assignments()

    def render_vocabulary():
        nonlocal vocabulary_index
        known_count = sum(entry["known"] for entry in vocabulary)
        vocabulary_progress.value = f"覚えた単語 {known_count} / {len(vocabulary)} 件"
        vocabulary_review_status.color = MUTED

        if vocabulary:
            vocabulary_index %= len(vocabulary)
            entry = vocabulary[vocabulary_index]
            vocabulary_word_label.value = entry["word"]
            vocabulary_meaning_label.value = (
                entry["meaning"] if vocabulary_answer_visible else "答えを見るを押してください"
            )
            vocabulary_example_label.value = entry.get("example", "")
            vocabulary_example_label.visible = vocabulary_answer_visible and bool(
                entry.get("example")
            )
            vocabulary_example_meaning_label.value = entry.get("example_meaning", "")
            vocabulary_example_meaning_label.visible = (
                vocabulary_answer_visible and bool(entry.get("example_meaning"))
            )
            vocabulary_review_status.value = (
                "覚えた単語です" if entry["known"] else "これから覚える単語です"
            )
            vocabulary_card_counter.value = f"{vocabulary_index + 1} / {len(vocabulary)}"
            vocabulary_answer_button.text = (
                "答えを隠す" if vocabulary_answer_visible else "答えを見る"
            )
            vocabulary_review_buttons.visible = vocabulary_answer_visible
        else:
            vocabulary_word_label.value = "単語を登録しましょう"
            vocabulary_meaning_label.value = "英単語と日本語の意味を入力してください。"
            vocabulary_example_label.value = ""
            vocabulary_example_label.visible = False
            vocabulary_example_meaning_label.value = ""
            vocabulary_example_meaning_label.visible = False
            vocabulary_review_status.value = ""
            vocabulary_card_counter.value = "0 / 0"
            vocabulary_answer_button.text = "答えを見る"
            vocabulary_review_buttons.visible = False

        vocabulary_entry_list.controls = (
            [
                ft.Row(
                    [
                        ft.Text(entry["word"], expand=True, color=INK, size=14),
                        ft.Text(
                            "覚えた" if entry["known"] else "学習中",
                            color=GREEN if entry["known"] else MUTED,
                            size=12,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color=MUTED,
                            tooltip=f"「{entry['word']}」を削除",
                            on_click=lambda event, entry_id=entry["id"]: delete_vocabulary(entry_id),
                        ),
                    ],
                    spacing=8,
                )
                for entry in vocabulary
            ]
            or [ft.Text("登録した単語はありません。", size=13, color=MUTED)]
        )
        page.update()

    def add_vocabulary(event):
        nonlocal vocabulary_index, vocabulary_answer_visible
        word = vocabulary_word_input.value.strip()
        meaning = vocabulary_meaning_input.value.strip()
        if not word or not meaning:
            vocabulary_status.value = "英単語と日本語の意味を入力してください。"
            vocabulary_status.color = CORAL
            page.update()
            return

        entry = {"id": str(uuid4()), "word": word, "meaning": meaning, "known": False}
        example = vocabulary_example_input.value.strip()
        example_meaning = vocabulary_example_meaning_input.value.strip()
        if example:
            entry["example"] = example
        if example_meaning:
            entry["example_meaning"] = example_meaning
        vocabulary.append(entry)
        try:
            save_vocabulary(vocabulary)
        except OSError:
            vocabulary.pop()
            vocabulary_status.value = "単語を保存できませんでした。書き込み権限をご確認ください。"
            vocabulary_status.color = CORAL
            page.update()
            return

        vocabulary_index = len(vocabulary) - 1
        vocabulary_answer_visible = False
        vocabulary_word_input.value = ""
        vocabulary_meaning_input.value = ""
        vocabulary_example_input.value = ""
        vocabulary_example_meaning_input.value = ""
        vocabulary_status.value = "単語を登録しました。"
        vocabulary_status.color = GREEN
        render_vocabulary()

    def toggle_vocabulary_answer(event):
        nonlocal vocabulary_answer_visible
        if vocabulary:
            vocabulary_answer_visible = not vocabulary_answer_visible
            render_vocabulary()

    def move_vocabulary(offset):
        nonlocal vocabulary_index, vocabulary_answer_visible
        if vocabulary:
            vocabulary_index = (vocabulary_index + offset) % len(vocabulary)
            vocabulary_answer_visible = False
            render_vocabulary()

    def review_vocabulary(known):
        nonlocal vocabulary_index, vocabulary_answer_visible
        if not vocabulary:
            return

        entry = vocabulary[vocabulary_index]
        previous_known = entry["known"]
        entry["known"] = known
        try:
            save_vocabulary(vocabulary)
        except OSError:
            entry["known"] = previous_known
            vocabulary_review_status.value = (
                "進捗を保存できませんでした。書き込み権限をご確認ください。"
            )
            vocabulary_review_status.color = CORAL
            page.update()
            return

        vocabulary_index = (vocabulary_index + 1) % len(vocabulary)
        vocabulary_answer_visible = False
        render_vocabulary()

    def delete_vocabulary(entry_id):
        nonlocal vocabulary_index, vocabulary_answer_visible
        remaining_entries = [
            entry for entry in vocabulary if entry["id"] != entry_id
        ]
        try:
            save_vocabulary(remaining_entries)
        except OSError:
            vocabulary_status.value = "単語を削除できませんでした。書き込み権限をご確認ください。"
            vocabulary_status.color = CORAL
            page.update()
            return

        vocabulary[:] = remaining_entries
        if vocabulary:
            vocabulary_index %= len(vocabulary)
        else:
            vocabulary_index = 0
        vocabulary_answer_visible = False
        vocabulary_status.value = "単語を削除しました。"
        vocabulary_status.color = GREEN
        render_vocabulary()

    def render():
        visible_tasks = [
            task
            for task in tasks
            if current_filter == "all"
            or (current_filter == "active" and not task["done"])
            or (current_filter == "done" and task["done"])
        ]
        remaining = sum(not task["done"] for task in tasks)
        completed = len(tasks) - remaining
        task_count.value = f"未完了 {remaining} 件"
        progress_label.value = (
            f"{completed} / {len(tasks)} 件 完了" if tasks else "タスクはまだありません"
        )
        clear_done_button.visible = completed > 0 and current_section == "plan"

        for key, button in filter_buttons.items():
            selected = key == current_filter
            button.style = ft.ButtonStyle(
                color=GREEN if selected else MUTED,
                bgcolor=GREEN_LIGHT if selected else "transparent",
                shape=ft.RoundedRectangleBorder(radius=4),
            )

        rows = []
        for task in visible_tasks:
            checkbox = ft.Checkbox(
                value=task["done"],
                label=task["text"],
                expand=True,
                active_color=GREEN,
                label_style=ft.TextStyle(
                    color="#929992" if task["done"] else INK,
                    decoration=ft.TextDecoration.LINE_THROUGH if task["done"] else None,
                    size=14,
                ),
                on_change=lambda event, task_id=task["id"]: toggle_task(task_id),
            )
            delete_button = ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_color=MUTED,
                tooltip=f"「{task['text']}」を削除",
                on_click=lambda event, task_id=task["id"]: delete_task(task_id),
            )
            rows.extend(
                [
                    ft.Row([checkbox, delete_button], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Divider(height=1, thickness=1, color="#DEDFD5"),
                ]
            )

        if not visible_tasks:
            empty_text = (
                "未完了のタスクはありません。いい調子！"
                if current_filter == "active" and tasks
                else "完了したタスクはまだありません。"
                if current_filter == "done" and tasks
                else "まずは、やることをひとつ書いてみましょう。"
            )
            rows = [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("○", size=24, color="#9A7629", text_align=ft.TextAlign.CENTER),
                            ft.Text(empty_text, size=13, color=MUTED, text_align=ft.TextAlign.CENTER),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    padding=32,
                    alignment=ft.Alignment.CENTER,
                )
            ]

        task_list.controls = rows
        page.update()

    def render_assignments():
        remaining = sum(not assignment["done"] for assignment in assignments)
        assignment_count.value = (
            f"未完了 {remaining} 件 / 合計 {len(assignments)} 件"
        )
        assignment_list.controls = (
            [
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Checkbox(
                                    value=assignment["done"],
                                    label=assignment["text"],
                                    expand=True,
                                    active_color=GREEN,
                                    label_style=ft.TextStyle(
                                        color="#929992" if assignment["done"] else INK,
                                        decoration=(
                                            ft.TextDecoration.LINE_THROUGH
                                            if assignment["done"]
                                            else None
                                        ),
                                        size=14,
                                    ),
                                    on_change=lambda event, assignment_id=assignment["id"]: toggle_assignment(
                                        assignment_id
                                    ),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_color=MUTED,
                                    tooltip=f"「{assignment['text']}」を削除",
                                    on_click=lambda event, assignment_id=assignment["id"]: delete_assignment(
                                        assignment_id
                                    ),
                                ),
                            ],
                            spacing=8,
                        ),
                        ft.Divider(height=1, thickness=1, color="#DEDFD5"),
                    ],
                    spacing=0,
                )
                for assignment in assignments
            ]
            or [
                ft.Container(
                    content=ft.Text(
                        "課題はまだありません。課題名を入力して追加しましょう。",
                        size=13,
                        color=MUTED,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    padding=32,
                    alignment=ft.Alignment.CENTER,
                )
            ]
        )
        page.update()

    for key, label in (("all", "すべて"), ("active", "未完了"), ("done", "完了")):
        filter_buttons[key] = ft.TextButton(
            label,
            on_click=lambda event, value=key: set_filter(value),
        )

    today = ft.Text(
        date.today().strftime("%Y年%m月%d日"),
        size=12,
        color=MUTED,
    )
    home_today = ft.Text(today.value, size=12, color=MUTED)
    composer = ft.Row(
        [
            task_input,
            ft.Button(
                "追加  ＋",
                on_click=add_task,
                bgcolor=GREEN,
                color="white",
                height=48,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)),
            ),
        ],
        spacing=10,
    )
    composer_panel = ft.Container(content=composer, padding=18, bgcolor=GREEN_LIGHT)
    filter_panel = ft.Container(
        content=ft.Row(
            [ft.Row(list(filter_buttons.values()), spacing=0), task_count],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.Padding(left=18, right=18, top=8, bottom=8),
        border=ft.Border.only(bottom=ft.BorderSide(1, "#DEDFD5")),
    )
    assignment_composer = ft.Container(
        content=ft.Column(
            [
                ft.Text("課題を追加", size=16, color=INK, weight=ft.FontWeight.W_600),
                ft.Row(
                    [
                        assignment_input,
                        ft.Button(
                            "追加  ＋",
                            on_click=add_assignment,
                            bgcolor=GREEN,
                            color="white",
                            height=48,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)),
                        ),
                    ],
                    spacing=10,
                ),
                assignment_status,
            ],
            spacing=10,
        ),
        padding=18,
        bgcolor=GREEN_LIGHT,
    )
    assignment_panel = ft.Column(
        [
            assignment_composer,
            ft.Container(
                content=ft.Column(
                    [
                        assignment_count,
                        assignment_list,
                    ],
                    spacing=8,
                ),
                padding=ft.Padding.symmetric(horizontal=18, vertical=12),
            ),
        ],
        spacing=0,
        visible=False,
    )

    vocabulary_card_counter = ft.Text(size=12, color=MUTED)
    vocabulary_answer_button = ft.TextButton(
        "答えを見る",
        on_click=toggle_vocabulary_answer,
    )
    vocabulary_review_buttons = ft.Row(
        [
            ft.Button(
                "もう一度",
                on_click=lambda event: review_vocabulary(False),
                bgcolor="#F2E9D9",
                color=INK,
            ),
            ft.Button(
                "覚えた",
                on_click=lambda event: review_vocabulary(True),
                bgcolor=GREEN,
                color="white",
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=12,
        visible=False,
    )
    vocabulary_panel = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("英単語カード", size=18, color=INK, weight=ft.FontWeight.W_600),
                        vocabulary_card_counter,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            vocabulary_word_label,
                            vocabulary_meaning_label,
                            vocabulary_example_label,
                            vocabulary_example_meaning_label,
                            vocabulary_review_status,
                            ft.Row(
                                [
                                    ft.TextButton(
                                        "前へ",
                                        on_click=lambda event: move_vocabulary(-1),
                                    ),
                                    vocabulary_answer_button,
                                    ft.TextButton(
                                        "次へ",
                                        on_click=lambda event: move_vocabulary(1),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            vocabulary_review_buttons,
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                    ),
                    padding=20,
                    bgcolor=GREEN_LIGHT,
                    border_radius=8,
                ),
                vocabulary_progress,
                ft.Divider(height=1, color="#DEDFD5"),
                ft.Text("英単語を追加", size=16, color=INK, weight=ft.FontWeight.W_600),
                vocabulary_word_input,
                vocabulary_meaning_input,
                vocabulary_example_input,
                vocabulary_example_meaning_input,
                ft.Button(
                    "単語を登録",
                    on_click=add_vocabulary,
                    bgcolor=GREEN,
                    color="white",
                ),
                vocabulary_status,
                ft.Text("登録した単語", size=16, color=INK, weight=ft.FontWeight.W_600),
                vocabulary_entry_list,
            ],
            spacing=14,
        ),
        padding=18,
        visible=False,
    )
    plan_view_buttons = {}
    plan_view_selector = ft.Container(
        content=ft.Row(
            [
                ft.TextButton(
                    label,
                    on_click=lambda event, view=value: set_plan_view(view),
                )
                for value, label in (("tasks", "やること"), ("vocabulary", "英単語"))
            ],
            spacing=4,
        ),
        padding=ft.Padding(left=18, right=18, top=8, bottom=8),
        border=ft.Border.only(bottom=ft.BorderSide(1, "#DEDFD5")),
    )
    plan_view_buttons = {
        "tasks": plan_view_selector.content.controls[0],
        "vocabulary": plan_view_selector.content.controls[1],
    }

    def update_plan_view_styles():
        for key, button in plan_view_buttons.items():
            selected = key == current_plan_view
            button.style = ft.ButtonStyle(
                color=GREEN if selected else MUTED,
                bgcolor=GREEN_LIGHT if selected else "transparent",
                shape=ft.RoundedRectangleBorder(radius=4),
            )

    def set_plan_view(view, refresh=True):
        nonlocal current_plan_view
        current_plan_view = view
        task_panel.visible = view == "tasks"
        vocabulary_panel.visible = view == "vocabulary"
        update_plan_view_styles()
        if refresh:
            render_vocabulary() if view == "vocabulary" else render()

    task_panel = ft.Column(
        [
            composer_panel,
            filter_panel,
            ft.Container(content=task_list, padding=ft.Padding.symmetric(horizontal=18)),
            ft.Container(
                content=ft.Row(
                    [progress_label, clear_done_button],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding(left=18, right=18, top=8, bottom=8),
                border=ft.Border.only(top=ft.BorderSide(1, "#DEDFD5")),
            ),
        ],
        spacing=0,
    )
    update_plan_view_styles()

    content = ft.Column(
        [
            ft.Row(
                [
                    ft.TextButton(
                        "ホームに戻る",
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda event: show_home(),
                    )
                ]
            ),
            ft.Row(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Text("日", color="white", size=15, weight=ft.FontWeight.BOLD),
                                width=28,
                                height=28,
                                bgcolor=GREEN,
                                border_radius=14,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Text("STUDYGROW", size=12, color=GREEN, weight=ft.FontWeight.BOLD),
                        ],
                        spacing=10,
                    ),
                    today,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Column(
                [
                    section_title,
                    section_description,
                ],
                spacing=4,
            ),
            ft.Container(
                content=ft.Column(
                    [plan_view_selector, task_panel, vocabulary_panel, assignment_panel],
                    spacing=0,
                ),
                width=700,
                bgcolor="#FFFEFA",
                border=ft.Border.all(1, "#E3E3D9"),
                border_radius=8,
                shadow=ft.BoxShadow(blur_radius=28, color="#182D2314", offset=ft.Offset(0, 10)),
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            ),
        ],
        width=700,
        spacing=28,
    )

    app_container = ft.Container(content=content, width=700, padding=ft.Padding.only(top=18, bottom=32))
    workspace_card = content.controls[3]
    home_container = ft.Container(width=700, padding=ft.Padding.only(top=18, bottom=32))
    calendar_container = ft.Container(width=700, padding=ft.Padding.only(top=18, bottom=32))

    def show_home():
        page.title = "StudyGrow | ホーム"
        page.controls.clear()
        page.add(home_container)
        page.update()

    def open_section(section):
        nonlocal current_section, current_filter
        current_section = section
        current_filter = "active" if section == "assignments" else "all"
        set_plan_view("tasks", refresh=False)
        plan_view_selector.visible = section == "plan"
        task_panel.visible = section == "plan"
        assignment_panel.visible = section == "assignments"
        composer_panel.visible = section == "plan"
        filter_panel.visible = section == "plan"
        if section == "plan":
            page.title = "学習計画 | StudyGrow"
            section_title.value = "学習計画"
            section_description.value = "ひとつずつ、今日の学びを進めよう。"
            page.controls.clear()
            page.add(app_container)
            render()
        elif section == "assignments":
            page.title = "課題の確認 | StudyGrow"
            section_title.value = "課題の確認"
            section_description.value = "課題を登録し、完了状況を確認しましょう。"
            page.controls.clear()
            page.add(app_container)
            render_assignments()
        else:
            page.title = "カレンダー | StudyGrow"
            page.controls.clear()
            page.add(calendar_container)
            render_calendar()

    def shift_month(offset):
        nonlocal visible_month
        month_index = visible_month.year * 12 + visible_month.month - 1 + offset
        visible_month = date(month_index // 12, month_index % 12 + 1, 1)
        render_calendar()

    def select_calendar_date(day):
        nonlocal selected_date
        selected_date = visible_month.replace(day=day)
        render_calendar()

    def add_calendar_event(event):
        text = calendar_event_input.value.strip()
        if not text:
            calendar_event_status.value = "予定を入力してください。"
            calendar_event_status.color = CORAL
            page.update()
            return
        events.append({"id": str(uuid4()), "date": selected_date.isoformat(), "text": text})
        try:
            save_events(events)
        except OSError:
            events.pop()
            calendar_event_status.value = "予定を保存できませんでした。書き込み権限をご確認ください。"
            calendar_event_status.color = CORAL
            page.update()
            return
        calendar_event_input.value = ""
        calendar_event_status.value = "予定を保存しました。"
        calendar_event_status.color = GREEN
        render_calendar()

    def delete_calendar_event(event_id):
        deleted_events = [event for event in events if event["id"] != event_id]
        try:
            save_events(deleted_events)
        except OSError:
            calendar_event_status.value = "予定を削除できませんでした。書き込み権限をご確認ください。"
            calendar_event_status.color = CORAL
            page.update()
            return
        events[:] = deleted_events
        calendar_event_status.value = "予定を削除しました。"
        calendar_event_status.color = GREEN
        render_calendar()

    def render_calendar():
        month_label = ft.Text(
            visible_month.strftime("%Y年 %m月"),
            size=22,
            color=INK,
            weight=ft.FontWeight.BOLD,
        )
        weekday_row = ft.Row(
            [
                ft.Container(
                    content=ft.Text(label, size=12, color=CORAL if index == 6 else MUTED, text_align=ft.TextAlign.CENTER),
                    expand=1,
                    alignment=ft.Alignment.CENTER,
                    padding=8,
                )
                for index, label in enumerate(("月", "火", "水", "木", "金", "土", "日"))
            ],
            spacing=0,
        )
        weeks = []
        month_weeks = calendar.monthcalendar(visible_month.year, visible_month.month)
        for week in month_weeks:
            day_cells = []
            for day in week:
                if day == 0:
                    day_cells.append(ft.Container(expand=1, height=48))
                    continue
                day_date = visible_month.replace(day=day)
                is_selected = day_date == selected_date
                day_event_count = sum(event["date"] == day_date.isoformat() for event in events)
                day_cells.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.TextButton(
                                    str(day),
                                    on_click=lambda event, selected_day=day: select_calendar_date(selected_day),
                                    style=ft.ButtonStyle(
                                        color="white" if is_selected else INK,
                                        bgcolor=GREEN if is_selected else "transparent",
                                        shape=ft.RoundedRectangleBorder(radius=22),
                                    ),
                                ),
                                ft.Text(
                                    f"予定 {day_event_count}件" if day_event_count else "",
                                    size=8,
                                    color=GREEN,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                            ],
                            spacing=0,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        expand=1,
                        height=62,
                        alignment=ft.Alignment.CENTER,
                    )
                )
            weeks.append(ft.Row(day_cells, spacing=0))

        selected_events = [event for event in events if event["date"] == selected_date.isoformat()]
        calendar_event_list.controls = (
            [
                ft.Row(
                    [
                        ft.Text(event["text"], expand=True, color=INK, size=14),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color=MUTED,
                            tooltip=f"「{event['text']}」を削除",
                            on_click=lambda click_event, event_id=event["id"]: delete_calendar_event(event_id),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
                for event in selected_events
            ]
            or [ft.Text("この日の予定はありません。", size=13, color=MUTED)]
        )

        calendar_panel = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.CHEVRON_LEFT,
                                tooltip="前の月",
                                on_click=lambda event: shift_month(-1),
                            ),
                            month_label,
                            ft.IconButton(
                                icon=ft.Icons.CHEVRON_RIGHT,
                                tooltip="次の月",
                                on_click=lambda event: shift_month(1),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    weekday_row,
                    *weeks,
                ],
                spacing=4,
            ),
            padding=20,
            bgcolor="#FFFEFA",
            border=ft.Border.all(1, "#E3E3D9"),
            border_radius=8,
        )
        calendar_content = ft.Column(
            [
                ft.TextButton(
                    "ホームに戻る",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda event: show_home(),
                ),
                ft.Row(
                    [
                        ft.Row(
                            [
                                ft.Container(
                                    content=ft.Text("S", color="white", size=15, weight=ft.FontWeight.BOLD),
                                    width=28,
                                    height=28,
                                    bgcolor=GREEN,
                                    border_radius=14,
                                    alignment=ft.Alignment.CENTER,
                                ),
                                ft.Text("STUDYGROW", size=12, color=GREEN, weight=ft.FontWeight.BOLD),
                            ],
                            spacing=10,
                        ),
                        ft.Text(today.value, size=12, color=MUTED),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Column(
                    [
                        ft.Text("カレンダー", size=38, color=INK, weight=ft.FontWeight.W_600),
                        ft.Text("月ごとの日付を確認しましょう。", size=13, color=MUTED),
                    ],
                    spacing=4,
                ),
                calendar_panel,
                ft.Text(
                    f"{selected_date.strftime('%Y年%m月%d日')} を選択中",
                    size=14,
                    color=GREEN,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Row(
                    [
                        calendar_event_input,
                        ft.Button(
                            "予定を追加",
                            on_click=add_calendar_event,
                            bgcolor=GREEN,
                            color="white",
                            height=48,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)),
                        ),
                    ],
                    spacing=10,
                ),
                calendar_event_status,
                ft.Container(
                    content=calendar_event_list,
                    padding=ft.Padding.symmetric(horizontal=12),
                    bgcolor="#FFFEFA",
                    border=ft.Border.all(1, "#E3E3D9"),
                    border_radius=8,
                ),
            ],
            width=700,
            spacing=24,
        )
        calendar_container.content = calendar_content
        calendar_container.width = min(700, max(272, (page.width or 748) - page.padding * 2))
        page.update()

    def make_home_card(number, icon, title, description, section):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(icon, color=GREEN, size=21),
                                width=42,
                                height=42,
                                bgcolor=GREEN_LIGHT,
                                border_radius=21,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Text(number, size=12, color=MUTED),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(title, size=18, color=INK, weight=ft.FontWeight.W_600),
                    ft.Text(description, size=12, color=MUTED),
                    ft.Row(
                        [
                            ft.Text("開く", size=13, color=GREEN, weight=ft.FontWeight.W_600),
                            ft.Icon(ft.Icons.ARROW_FORWARD, size=16, color=GREEN),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=12,
            ),
            padding=18,
            bgcolor="#FFFEFA",
            border=ft.Border.all(1, "#E3E3D9"),
            border_radius=8,
            col={"xs": 12, "sm": 4},
            on_click=lambda event: open_section(section),
        )

    home_cards = ft.ResponsiveRow(
        [
            make_home_card("01", ft.Icons.EDIT_NOTE, "学習計画", "今日やることを整理する", "plan"),
            make_home_card("02", ft.Icons.CHECKLIST, "課題の確認", "未完了の課題をチェック", "assignments"),
            make_home_card("03", ft.Icons.CALENDAR_MONTH, "カレンダー", "月ごとの日付を確認する", "calendar"),
        ],
        spacing=12,
        run_spacing=12,
        breakpoints={"xs": 0, "sm": 600},
    )
    home_content = ft.Column(
        [
            ft.Row(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Text("S", color="white", size=15, weight=ft.FontWeight.BOLD),
                                width=28,
                                height=28,
                                bgcolor=GREEN,
                                border_radius=14,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Text("STUDYGROW", size=12, color=GREEN, weight=ft.FontWeight.BOLD),
                        ],
                        spacing=10,
                    ),
                    home_today,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Column(
                [
                    ft.Text("今日の学びを、ここから。", size=32, color=INK, weight=ft.FontWeight.W_600),
                    ft.Text("やりたいことを選んで、学習を始めましょう。", size=14, color=MUTED),
                ],
                spacing=6,
            ),
            home_cards,
        ],
        width=700,
        spacing=28,
    )
    home_container.content = home_content

    def resize_page(event):
        viewport_width = page.width or 748
        page.padding = 12 if viewport_width < 520 else 24
        content_width = min(700, max(272, viewport_width - page.padding * 2))
        app_container.width = content_width
        content.width = content_width
        workspace_card.width = content_width
        home_container.width = content_width
        home_content.width = content_width
        calendar_container.width = content_width
        page.update()

    page.on_resize = resize_page
    show_home()
    render()


if __name__ == "__main__":
    ft.run(main, host="0.0.0.0", port=8000, view=ft.AppView.WEB_BROWSER)