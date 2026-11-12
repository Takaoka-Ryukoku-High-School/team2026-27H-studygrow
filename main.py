import asyncio
import calendar
import io
import json
import math
import random
import sys
import wave
from array import array
from datetime import date
from pathlib import Path
from time import monotonic
from uuid import uuid4

import flet as ft
import flet_audio as fta


DATA_FILE = Path.home() / ".daily_note_tasks.json"
ASSIGNMENTS_FILE = Path.home() / ".studygrow_assignments.json"
EVENTS_FILE = Path.home() / ".studygrow_events.json"
GREEN = "#2E6654"
GREEN_LIGHT = "#E2EDE5"
PAPER = "#F6F5EF"
INK = "#202C2A"
MUTED = "#77807B"
CORAL = "#CF6048"
# 文面が決まったら、この仮コメント一覧を差し替える。
MOTIVATION_COMMENTS = (
    "まずは一歩、始めてみよう。",
    "小さな積み重ねが力になる。",
    "今日の自分にできることから。",
)


def make_wav(samples, sample_rate):
    sample_data = array("h", samples)
    if sys.byteorder != "little":
        sample_data.byteswap()

    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(sample_data.tobytes())
    return output.getvalue()


def make_ambient_audio():
    sample_rate = 16000
    random_source = random.Random(2026)
    filtered_noise = 0.0
    samples = array("h")
    for index in range(sample_rate * 6):
        filtered_noise = filtered_noise * 0.96 + random_source.uniform(-1, 1) * 0.04
        time_seconds = index / sample_rate
        tone = (
            0.08 * math.sin(2 * math.pi * 110 * time_seconds)
            + 0.035 * math.sin(2 * math.pi * 165 * time_seconds)
        )
        samples.append(round((tone + filtered_noise * 0.12) * 32767))
    return make_wav(samples, sample_rate)


def make_alarm_audio():
    sample_rate = 16000
    samples = array("h")
    pulse_length = int(sample_rate * 0.65)
    on_length = int(sample_rate * 0.3)
    fade_length = int(sample_rate * 0.015)
    for index in range(sample_rate * 3):
        pulse_position = index % pulse_length
        if pulse_position >= on_length:
            samples.append(0)
            continue
        fade = min(1.0, pulse_position / fade_length, (on_length - pulse_position) / fade_length)
        frequency = 880 if (index // pulse_length) % 2 == 0 else 660
        value = 0.32 * fade * math.sin(2 * math.pi * frequency * index / sample_rate)
        samples.append(round(value * 32767))
    return make_wav(samples, sample_rate)


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
    current_filter = "all"
    current_section = "plan"
    visible_month = date.today().replace(day=1)
    selected_date = date.today()
    stopwatch_running = False
    stopwatch_elapsed = 0.0
    stopwatch_started_at = None
    stopwatch_generation = 0
    timer_running = False
    timer_remaining = None
    timer_started_at = None
    timer_generation = 0
    timer_alarm_active = False

    ambient_audio = fta.Audio(
        src=make_ambient_audio(),
        autoplay=False,
        release_mode=fta.ReleaseMode.LOOP,
        volume=0.16,
    )
    alarm_audio = fta.Audio(
        src=make_alarm_audio(),
        autoplay=False,
        release_mode=fta.ReleaseMode.STOP,
        volume=0.65,
    )
    page.services.extend([ambient_audio, alarm_audio])

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
        hint_text="自分の課題（例：数学ワーク p.10）",
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
    calendar_event_list = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO)
    calendar_selected_date = ft.Text(size=13, color=GREEN)
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
    motivation_text = ft.Text(
        random.choice(MOTIVATION_COMMENTS),
        size=17,
        color=INK,
        weight=ft.FontWeight.W_600,
        expand=True,
    )

    def show_random_motivation(event):
        choices = [
            comment
            for comment in MOTIVATION_COMMENTS
            if comment != motivation_text.value
        ]
        motivation_text.value = random.choice(choices or MOTIVATION_COMMENTS)
        page.update()

    motivation_panel = ft.Container(
        content=ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("今日の応援コメント", size=12, color=GREEN),
                        motivation_text,
                    ],
                    spacing=6,
                    expand=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    icon_color=GREEN,
                    tooltip="別のコメントを見る",
                    on_click=show_random_motivation,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=18,
        bgcolor=GREEN_LIGHT,
        border_radius=8,
    )
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
                ft.Text("自分の課題を追加", size=16, color=INK, weight=ft.FontWeight.W_600),
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
                    [task_panel, assignment_panel],
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
    stopwatch_display = ft.Text(
        "00:00:00.00",
        size=48,
        color=GREEN,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER,
    )
    stopwatch_message = ft.Text(size=13, color=MUTED, text_align=ft.TextAlign.CENTER)
    stopwatch_start_pause_button = ft.Button(
        "スタート",
        on_click=lambda event: toggle_stopwatch(),
        bgcolor=GREEN,
        color="white",
    )
    stopwatch_stop_button = ft.Button(
        "リセット",
        on_click=lambda event: stop_stopwatch(),
    )
    stopwatch_home_button = ft.TextButton(
        "ホームに戻る",
        icon=ft.Icons.ARROW_BACK,
        on_click=lambda event: show_home(),
    )
    stopwatch_mode_row = ft.Row(
        [
            ft.TextButton("ストップウォッチ", on_click=lambda event: show_stopwatch_mode()),
            ft.TextButton("タイマー", on_click=lambda event: show_timer_mode()),
        ],
        spacing=8,
    )
    stopwatch_container = ft.Container(
        content=ft.Column(
            [
                stopwatch_mode_row,
                stopwatch_home_button,
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("ストップウォッチ", size=28, color=INK, weight=ft.FontWeight.W_600),
                            stopwatch_display,
                            stopwatch_message,
                            ft.Row(
                                [stopwatch_start_pause_button, stopwatch_stop_button],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=12,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=24,
                    ),
                    padding=32,
                    bgcolor="#FFFEFA",
                    border=ft.Border.all(1, "#E3E3D9"),
                    border_radius=8,
                ),
            ],
            width=700,
            spacing=24,
        ),
        width=700,
        padding=ft.Padding.only(top=18, bottom=32),
    )
    timer_hours_input = ft.TextField(
        value="00",
        label="時間",
        width=92,
        text_align=ft.TextAlign.CENTER,
    )
    timer_minutes_input = ft.TextField(
        value="25",
        label="分",
        width=92,
        text_align=ft.TextAlign.CENTER,
    )
    timer_seconds_input = ft.TextField(
        value="00",
        label="秒",
        width=92,
        text_align=ft.TextAlign.CENTER,
    )
    timer_input_row = ft.Row(
        [
            timer_hours_input,
            ft.Text(":", size=20, color=MUTED),
            timer_minutes_input,
            ft.Text(":", size=20, color=MUTED),
            timer_seconds_input,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    timer_display = ft.Text(
        "00:25:00.00",
        size=48,
        color=GREEN,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER,
    )
    timer_message = ft.Text(
        "時間を設定してタイマーを開始してください。",
        size=13,
        color=MUTED,
        text_align=ft.TextAlign.CENTER,
    )
    timer_mode_row = ft.Row(
        [
            ft.TextButton("ストップウォッチ", on_click=lambda event: show_stopwatch_mode()),
            ft.TextButton("タイマー", on_click=lambda event: show_timer_mode()),
        ],
        spacing=8,
    )
    timer_home_button = ft.TextButton(
        "ホームに戻る",
        icon=ft.Icons.ARROW_BACK,
        on_click=lambda event: show_home(),
    )
    timer_toggle_button = ft.Button(
        "タイマー開始",
        on_click=lambda event: toggle_timer(event),
        bgcolor=GREEN,
        color="white",
    )
    timer_reset_button = ft.Button("リセット", on_click=lambda event: reset_timer(event))
    timer_alarm_stop_button = ft.Button(
        "アラーム停止",
        on_click=lambda event: stop_timer_alarm(event),
    )
    timer_container = ft.Container(
        content=ft.Column(
            [
                timer_mode_row,
                timer_home_button,
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("タイマー", size=28, color=INK, weight=ft.FontWeight.W_600),
                            timer_input_row,
                            timer_display,
                            timer_message,
                            ft.Row(
                                [
                                    timer_toggle_button,
                                    timer_reset_button,
                                    timer_alarm_stop_button,
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=12,
                                wrap=True,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=24,
                    ),
                    padding=32,
                    bgcolor="#FFFEFA",
                    border=ft.Border.all(1, "#E3E3D9"),
                    border_radius=8,
                ),
            ],
            width=700,
            spacing=24,
        ),
        width=700,
        padding=ft.Padding.only(top=18, bottom=32),
    )

    def format_stopwatch(seconds):
        centiseconds = int(seconds * 100)
        hours, remainder = divmod(centiseconds, 360000)
        minutes, remainder = divmod(remainder, 6000)
        whole_seconds, fraction = divmod(remainder, 100)
        return f"{hours:02}:{minutes:02}:{whole_seconds:02}.{fraction:02}"

    def render_stopwatch():
        elapsed = stopwatch_elapsed
        if stopwatch_running and stopwatch_started_at is not None:
            elapsed += monotonic() - stopwatch_started_at
        stopwatch_display.value = format_stopwatch(elapsed)
        stopwatch_home_button.visible = not stopwatch_running
        stopwatch_mode_row.visible = not stopwatch_running
        stopwatch_start_pause_button.text = (
            "一時停止" if stopwatch_running else "再開" if stopwatch_elapsed else "スタート"
        )
        stopwatch_stop_button.visible = not stopwatch_running
        stopwatch_stop_button.text = "リセット"
        stopwatch_message.value = (
            "計測中は一時停止以外の操作ができません。"
            if stopwatch_running
            else "計測中は画面がロックされます。"
        )
        page.title = "ストップウォッチ | StudyGrow"
        page.controls.clear()
        page.add(stopwatch_container)
        page.update()

    def render_timer():
        if timer_remaining is None:
            try:
                displayed_seconds = int(timer_hours_input.value or 0) * 3600
                displayed_seconds += int(timer_minutes_input.value or 0) * 60
                displayed_seconds += int(timer_seconds_input.value or 0)
            except ValueError:
                displayed_seconds = 0
        else:
            displayed_seconds = timer_remaining

        if timer_running and timer_started_at is not None and timer_remaining is not None:
            displayed_seconds = max(
                0,
                timer_remaining - (monotonic() - timer_started_at),
            )
        timer_display.value = format_stopwatch(displayed_seconds)
        timer_home_button.visible = not timer_running
        timer_mode_row.visible = not timer_running
        timer_input_row.visible = timer_remaining is None and not timer_running
        timer_display.visible = timer_remaining is not None or timer_running
        timer_toggle_button.visible = not timer_alarm_active
        timer_toggle_button.text = (
            "一時停止"
            if timer_running
            else "再開"
            if timer_remaining is not None and timer_remaining > 0
            else "タイマー開始"
        )
        timer_reset_button.visible = not timer_running and not timer_alarm_active
        timer_alarm_stop_button.visible = timer_alarm_active
        if timer_running:
            timer_message.value = "タイマー動作中は一時停止以外の操作ができません。"
        page.title = "タイマー | StudyGrow"
        page.controls.clear()
        page.add(timer_container)
        page.update()

    async def update_stopwatch(generation):
        while stopwatch_running and generation == stopwatch_generation:
            render_stopwatch()
            await asyncio.sleep(0.1)

    def toggle_stopwatch():
        nonlocal stopwatch_running, stopwatch_elapsed, stopwatch_started_at, stopwatch_generation
        if timer_running:
            return
        if stopwatch_running:
            if stopwatch_started_at is not None:
                stopwatch_elapsed += monotonic() - stopwatch_started_at
            stopwatch_started_at = None
            stopwatch_running = False
            stopwatch_generation += 1
            render_stopwatch()
            return

        stopwatch_started_at = monotonic()
        stopwatch_running = True
        stopwatch_generation += 1
        generation = stopwatch_generation
        render_stopwatch()
        page.run_task(update_stopwatch, generation)

    def stop_stopwatch():
        nonlocal stopwatch_running, stopwatch_elapsed, stopwatch_started_at, stopwatch_generation
        stopwatch_running = False
        stopwatch_elapsed = 0.0
        stopwatch_started_at = None
        stopwatch_generation += 1
        render_stopwatch()

    def show_stopwatch_mode():
        if stopwatch_running or timer_running:
            return
        render_stopwatch()

    def show_timer_mode():
        if stopwatch_running or timer_running:
            return
        render_timer()

    def read_timer_duration():
        try:
            hours = int(timer_hours_input.value or 0)
            minutes = int(timer_minutes_input.value or 0)
            seconds = int(timer_seconds_input.value or 0)
        except ValueError as error:
            raise ValueError("時間・分・秒には整数を入力してください。") from error

        if not 0 <= hours <= 99 or not 0 <= minutes < 60 or not 0 <= seconds < 60:
            raise ValueError("時間は0〜99、分と秒は0〜59で入力してください。")
        duration = hours * 3600 + minutes * 60 + seconds
        if duration == 0:
            raise ValueError("1秒以上の時間を設定してください。")
        return duration

    async def toggle_timer(event):
        nonlocal timer_running, timer_remaining, timer_started_at, timer_generation
        if stopwatch_running:
            return

        if timer_running:
            if timer_started_at is not None and timer_remaining is not None:
                timer_remaining = max(
                    0,
                    timer_remaining - (monotonic() - timer_started_at),
                )
            timer_started_at = None
            timer_running = False
            timer_generation += 1
            timer_message.value = "一時停止中です。再開するか、リセットできます。"
            render_timer()
            await ambient_audio.pause()
            return

        if timer_remaining is None or timer_remaining <= 0:
            try:
                timer_remaining = float(read_timer_duration())
            except ValueError as error:
                timer_message.value = str(error)
                render_timer()
                return

        timer_started_at = monotonic()
        timer_running = True
        timer_generation += 1
        generation = timer_generation
        timer_message.value = "タイマー動作中は一時停止以外の操作ができません。"
        render_timer()
        page.run_task(update_timer, generation)
        await ambient_audio.play()

    async def update_timer(generation):
        nonlocal timer_running, timer_remaining, timer_started_at
        nonlocal timer_generation, timer_alarm_active
        while timer_running and generation == timer_generation:
            if timer_remaining is None or timer_started_at is None:
                return
            remaining = timer_remaining - (monotonic() - timer_started_at)
            if remaining <= 0:
                timer_remaining = 0.0
                timer_started_at = None
                timer_running = False
                timer_generation += 1
                timer_alarm_active = True
                timer_message.value = "時間になりました。アラームを再生しています。"
                render_timer()
                await ambient_audio.pause()
                await alarm_audio.play()
                await asyncio.sleep(3)
                if timer_alarm_active:
                    timer_alarm_active = False
                    timer_message.value = "タイマーが終了しました。"
                    render_timer()
                return

            timer_display.value = format_stopwatch(remaining)
            page.update()
            await asyncio.sleep(0.1)

    async def reset_timer(event):
        nonlocal timer_remaining, timer_alarm_active
        if timer_running:
            return
        alarm_was_active = timer_alarm_active
        timer_alarm_active = False
        timer_remaining = None
        timer_message.value = "時間を設定してタイマーを開始してください。"
        render_timer()
        if alarm_was_active:
            await alarm_audio.pause()

    async def stop_timer_alarm(event):
        nonlocal timer_alarm_active
        timer_alarm_active = False
        timer_message.value = "タイマーが終了しました。"
        render_timer()
        await alarm_audio.pause()

    def show_home():
        if stopwatch_running or timer_running:
            return
        page.title = "StudyGrow | ホーム"
        page.controls.clear()
        page.add(home_container)
        page.update()

    def open_section(section):
        nonlocal current_section, current_filter
        if stopwatch_running or timer_running:
            return
        current_section = section
        current_filter = "active" if section == "assignments" else "all"
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
            page.title = "課題 | StudyGrow"
            section_title.value = "課題"
            section_description.value = "自分の課題を追加し、完了状況を管理しましょう。"
            page.controls.clear()
            page.add(app_container)
            render_assignments()
        elif section == "calendar":
            page.title = "カレンダー | StudyGrow"
            section_title.value = "カレンダー"
            section_description.value = ""
            page.controls.clear()
            page.add(calendar_container)
            render_calendar()
        else:
            render_stopwatch()

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
        calendar_selected_date.value = f"{selected_date.strftime('%Y年%m月%d日')} の予定"
        calendar_event_list.controls = (
            [
                ft.Row(
                    [
                        ft.Text(f"• {event['text']}", expand=True, color=INK, size=22),
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
            or [ft.Text("この日の予定はありません。", size=18, color=MUTED)]
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
        calendar_event_bubble = ft.Container(
            content=ft.Column(
                [
                    ft.Text("選択日の予定", size=18, color=INK, weight=ft.FontWeight.W_600),
                    calendar_selected_date,
                    ft.Divider(height=1, color="#C8D9CC"),
                    calendar_event_list,
                ],
                spacing=12,
            ),
            padding=20,
            bgcolor=GREEN_LIGHT,
            border=ft.Border.all(1, "#C8D9CC"),
            border_radius=20,
        )
        viewport_width = page.width or 748
        calendar_content_width = min(1000, max(272, viewport_width - page.padding * 2))
        show_calendar_side_by_side = calendar_content_width >= 760
        if show_calendar_side_by_side:
            calendar_panel.width = (calendar_content_width - 20) * 0.62
            calendar_event_bubble.width = (calendar_content_width - 20) * 0.38
            calendar_event_bubble.height = 460
            calendar_event_list.height = 350
            calendar_schedule_layout = ft.Row(
                [calendar_panel, calendar_event_bubble],
                spacing=20,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        else:
            calendar_panel.width = calendar_content_width
            calendar_event_bubble.width = calendar_content_width
            calendar_event_bubble.height = 300
            calendar_event_list.height = 190
            calendar_schedule_layout = ft.Column(
                [calendar_panel, calendar_event_bubble],
                spacing=16,
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
                        ft.Text("", size=13, color=MUTED),
                    ],
                    spacing=4,
                ),
                calendar_schedule_layout,
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
            ],
            width=calendar_content_width,
            spacing=24,
        )
        calendar_container.content = calendar_content
        calendar_container.width = calendar_content_width
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
            make_home_card("02", ft.Icons.CHECKLIST, "課題", "自分の課題を追加・管理する", "assignments"),
            make_home_card("03", ft.Icons.CALENDAR_MONTH, "カレンダー", "月ごとの予定を確認", "calendar"),
            make_home_card("04", ft.Icons.TIMER_OUTLINED, "ストップウォッチ", "学習時間を計測する", "stopwatch"),
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
            motivation_panel,
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
        stopwatch_container.width = content_width
        stopwatch_container.content.width = content_width
        timer_container.width = content_width
        timer_container.content.width = content_width
        calendar_container.width = min(1000, max(272, viewport_width - page.padding * 2))
        if current_section == "calendar":
            render_calendar()
            return
        if timer_running:
            render_timer()
            return
        if stopwatch_running:
            render_stopwatch()
            return
        page.update()

    page.on_resize = resize_page
    show_home()
    render()


if __name__ == "__main__":
    ft.run(main, host="0.0.0.0", port=8000, view=ft.AppView.WEB_BROWSER)