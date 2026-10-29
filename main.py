# ============================================================
#  main.py — Study Planner (Full PySide6 Rebuild)
#  Run: python main.py
# ============================================================
import sys
import os
import json
import datetime
import uuid
import random
import calendar
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QStackedWidget, QLineEdit,
    QCheckBox, QComboBox, QMessageBox, QDialog, QFormLayout,
    QDialogButtonBox, QSystemTrayIcon, QScroller, QProgressBar,
    QDateEdit, QTimeEdit, QCalendarWidget, QStyledItemDelegate, QSpinBox, QToolButton
)
from PySide6.QtCore import Qt, QTimer, QUrl, QSize, QRect, QDate, QTime, Signal
from PySide6.QtGui import (
    QColor, QFont, QIcon, QPainter, QPalette, QPen, QDesktopServices, QPixmap,
    QTextCharFormat
)

def resource_path(name):
    """Path to a bundled resource (works from source and from a PyInstaller build)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


# ============================================================
#  Data Store & Settings (1:1 port from your CustomTkinter app)
# ============================================================
APP_DIR = Path.home() / ".study_planner"
DATA_FILE = APP_DIR / "data.json"
SETTINGS_FILE = APP_DIR / "settings.json"

TASK_TYPES = ("deadline", "test", "study")
TYPE_LABELS = {"deadline": "Deadline", "test": "Test", "study": "Study Session"}
TYPE_COLORS = {"deadline": "#ec4899", "test": "#f59e0b", "study": "#3b82f6"}

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKDAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
LESSON_KINDS = ("Lecture", "Tutorial", "Lab", "Seminar", "Other")
LESSON_KIND_COLORS = {
    "Lecture": "#3b82f6", "Tutorial": "#2fa572", "Lab": "#8b5cf6",
    "Seminar": "#f59e0b", "Other": "#64748b",
}
UNIT_COLOR_NAMES = {
    "Green": "#2fa572", "Blue": "#3b82f6", "Purple": "#8b5cf6",
    "Pink": "#ec4899", "Amber": "#f59e0b", "Red": "#ef4444",
    "Teal": "#14b8a6", "Indigo": "#6366f1",
}
UNIT_COLORS = list(UNIT_COLOR_NAMES.values())
ACCENT_OPTIONS = {
    "Blue": "#3b82f6", "Green": "#2fa572", "Purple": "#8b5cf6",
    "Pink": "#ec4899", "Amber": "#f59e0b", "Red": "#ef4444", "Teal": "#14b8a6",
}

DEFAULT_SETTINGS = {
    "appearance_mode": "Dark", "accent_color": "#14b8a6", "ui_scale": "80%", "layout_v2": False,
    "daily_goal_hours": 3, "show_daily_tip": True, "notify_deadlines": True,
    "notify_tests": True, "notify_timetable": True, "username": "", "name_prompted": False,
    "notify_per_day": 2, "break_reminders": True, "notify_lessons": True,
    "lesson_reminder_minutes": 10, "notify_session_start": True,
}

def new_id(): return uuid.uuid4().hex[:8]

def parse_due(value):
    if not value: return None
    if isinstance(value, datetime.datetime): return value
    text = str(value).strip()
    if len(text) == 10:
        try: return datetime.datetime.combine(datetime.date.fromisoformat(text), datetime.time(23, 59))
        except ValueError: pass
    try: return datetime.datetime.fromisoformat(text)
    except ValueError: pass
    try: return datetime.datetime.combine(datetime.date.fromisoformat(text), datetime.time(23, 59))
    except ValueError: return None

def fmt_due(value):
    d = parse_due(value)
    if not d: return "no date"
    today = datetime.date.today()
    delta = (d.date() - today).days
    if delta == 0: return f"today {d.strftime('%H:%M')}"
    if delta == 1: return f"tomorrow {d.strftime('%H:%M')}"
    if delta < 0: return f"overdue by {-delta}d"
    return d.strftime("%b %d, %H:%M")

def fmt_countdown(value, now=None):
    due = parse_due(value)
    if not due: return "no due date", "#8a8a8a"
    now = now or datetime.datetime.now()
    total = int((due - now).total_seconds())
    secs = abs(total)
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days: span = f"{days}d {hours}h"
    elif hours: span = f"{hours}h {minutes:02d}m"
    else: span = f"{minutes}m"
    if total < 0: return f"Overdue by {span}", "#ef4444"
    if total < 86400: return f"{span} left", "#ef4444"
    if total < 3 * 86400: return f"{span} left", "#d97706"
    return f"{span} left", "#2fa572"

def fmt_duration(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h: return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def fmt_minutes(seconds):
    m = int(seconds) // 60
    h, m = divmod(m, 60)
    if h: return f"{h}h {m:02d}m"
    return f"{m}m"

def parse_time(value):
    if not value: return None
    text = str(value).strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try: return datetime.datetime.strptime(text, fmt).time()
        except ValueError: continue
    return None

class DataStore:
    def __init__(self):
        self.units, self.tasks, self.sessions, self.lessons = [], [], [], []
        self.load()

    def load(self):
        if DATA_FILE.exists():
            try:
                raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
                self.units = raw.get("units", [])
                self.tasks = raw.get("tasks", [])
                self.sessions = raw.get("sessions", [])
                self.lessons = raw.get("lessons", [])
                return
            except Exception: pass
        self.save()

    def save(self):
        try:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            DATA_FILE.write_text(json.dumps(
                {"units": self.units, "tasks": self.tasks,
                 "sessions": self.sessions, "lessons": self.lessons},
                indent=2), encoding="utf-8")
        except Exception: pass

    def add_unit(self, name, code="", color=None, save=True):
        unit = {"id": new_id(), "name": (name or "Untitled").strip(), "code": (code or "").strip(), "color": color or UNIT_COLORS[len(self.units) % len(UNIT_COLORS)]}
        self.units.append(unit)
        if save: self.save()
        return unit

    def get_unit(self, uid): return next((u for u in self.units if u["id"] == uid), None)
    def unit_name(self, uid): return self.get_unit(uid)["name"] if self.get_unit(uid) else "General"
    def unit_color(self, uid): return self.get_unit(uid)["color"] if self.get_unit(uid) else "#8a8a8a"
    
    def update_unit(self, uid, save=True, **fields):
        u = self.get_unit(uid)
        if u:
            u.update(fields)
            if save: self.save()

    def remove_unit(self, uid, delete_tasks=False):
        self.units = [u for u in self.units if u["id"] != uid]
        if delete_tasks: self.tasks = [t for t in self.tasks if t.get("unit_id") != uid]
        else:
            for t in self.tasks:
                if t.get("unit_id") == uid: t["unit_id"] = None
        self.lessons = [l for l in self.lessons if l.get("unit_id") != uid]
        self.save()

    def add_task(self, title, type_, due, unit_id=None, notes="", file_path="", save=True):
        task = {"id": new_id(), "title": (title or "Untitled").strip(), "type": type_ if type_ in TASK_TYPES else "deadline", "unit_id": unit_id, "due": due, "notes": notes, "file_path": file_path, "done": False, "completed_at": None}
        self.tasks.append(task)
        if save: self.save()
        return task

    def get_task(self, tid): return next((t for t in self.tasks if t["id"] == tid), None)
    
    def update_task(self, tid, save=True, **fields):
        t = self.get_task(tid)
        if t:
            t.update(fields)
            if save: self.save()

    def remove_task(self, tid):
        self.tasks = [t for t in self.tasks if t["id"] != tid]
        self.sessions = [s for s in self.sessions if s.get("task_id") != tid]
        self.save()

    def toggle_done(self, tid):
        t = self.get_task(tid)
        if t:
            t["done"] = not t.get("done")
            t["completed_at"] = datetime.datetime.now().isoformat(timespec="seconds") if t["done"] else None
            self.save()

    def add_session(self, task_id, unit_id, seconds, note=""):
        s = {"id": new_id(), "task_id": task_id, "unit_id": unit_id, "seconds": int(seconds), "note": (note or "").strip(), "when": datetime.datetime.now().isoformat(timespec="seconds")}
        self.sessions.append(s)
        self.save()

    def total_seconds_for_task(self, task_id):
        return sum(int(s.get("seconds", 0)) for s in self.sessions if s.get("task_id") == task_id)
        
    def seconds_today(self):
        today = datetime.date.today()
        total = 0
        for s in self.sessions:
            try:
                if datetime.datetime.fromisoformat(s["when"]).date() == today:
                    total += int(s.get("seconds", 0))
            except ValueError: pass
        return total

    def add_lesson(self, unit_id, day, start, end, kind="Lecture", location="", save=True):
        lesson = {"id": new_id(), "unit_id": unit_id, "day": int(day) % 7, "start": (start or "09:00").strip(), "end": (end or "10:00").strip(), "kind": kind, "location": (location or "").strip()}
        self.lessons.append(lesson)
        if save: self.save()
        return lesson

    def get_lesson(self, lid): return next((l for l in self.lessons if l["id"] == lid), None)
    
    def update_lesson(self, lid, save=True, **fields):
        l = self.get_lesson(lid)
        if l:
            l.update(fields)
            if "day" in fields: l["day"] = int(fields["day"]) % 7
            if save: self.save()

    def remove_lesson(self, lid):
        self.lessons = [l for l in self.lessons if l["id"] != lid]
        self.save()

    def lessons_for_day(self, day):
        out = [l for l in self.lessons if int(l.get("day", 0)) % 7 == day % 7]
        return sorted(out, key=lambda l: (l.get("start", ""), l.get("end", "")))
        
    def lessons_today(self): return self.lessons_for_day(datetime.date.today().weekday())

    def revision_suggestions(self, lessons=None, limit=3):
        lessons = self.lessons_today() if lessons is None else lessons
        unit_ids = []
        for l in lessons:
            uid = l.get("unit_id")
            if uid and uid not in unit_ids: unit_ids.append(uid)
        now = datetime.datetime.now()
        scored = []
        for uid in unit_ids:
            unit = self.get_unit(uid)
            if not unit: continue
            soonest, soonest_task = None, None
            for t in self.tasks:
                if t.get("unit_id") != uid or t.get("done") or t.get("type") not in ("test", "deadline"): continue
                due = parse_due(t.get("due"))
                if not due or due < now: continue
                if soonest is None or due < soonest: soonest, soonest_task = due, t
            urgency = 0.0
            if soonest: urgency += max(0.0, 14.0 - ((soonest - now).total_seconds() / 86400.0))
            if soonest_task: reason = f"{TYPE_LABELS.get(soonest_task.get('type'), 'Task')} '{soonest_task.get('title', 'Untitled')}' coming up ({fmt_due(soonest_task.get('due'))})"
            else: reason = "Not revised yet — lock in today's lecture"
            scored.append({"unit": unit, "reason": reason, "urgency": urgency})
        scored.sort(key=lambda x: -x["urgency"])
        return scored[:limit]

    def overall_stats(self):
        total, done = len(self.tasks), sum(1 for t in self.tasks if t.get("done"))
        return {"total": total, "done": done, "open": total - done, "percent": (done / total * 100) if total else 0.0}

    def unit_stats(self, uid):
        ts = [t for t in self.tasks if t.get("unit_id") == uid]
        done = sum(1 for t in ts if t.get("done"))
        return {"total": len(ts), "done": done, "open": len(ts) - done, "percent": (done / len(ts) * 100) if ts else 0.0}

class SettingsManager:
    def __init__(self):
        self.data = dict(DEFAULT_SETTINGS)
        if SETTINGS_FILE.exists():
            try: self.data.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
            except Exception: pass
        # One-time migration so existing settings files pick up the new look
        # (teal accent, 80% text size). After this, the user's own choices stick.
        if not self.data.get("layout_v2"):
            if str(self.data.get("accent_color", "")).lower() == "#3b82f6":
                self.data["accent_color"] = DEFAULT_SETTINGS["accent_color"]
            if self.data.get("ui_scale") == "100%":
                self.data["ui_scale"] = DEFAULT_SETTINGS["ui_scale"]
            self.data["layout_v2"] = True
            self.save()

    def get(self, key, default=None): return self.data.get(key, default)
    def set(self, key, value): self.data[key] = value
    def save(self):
        try:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            SETTINGS_FILE.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        except Exception: pass

# ============================================================
#  Study Tips content
# ============================================================
TIPS = {
    "Focus": {"color": "#2563eb", "tips": [
        "Work in 25-minute blocks with 5-minute breaks. The brain stays sharpest when effort is bounded.",
        "Put your phone in another room, not face-down on the desk. Proximity alone costs attention.",
        "Start with the smallest possible action. Opening the document is enough to break inertia.",
        "Use a single browser window. Extra tabs quietly tax your working memory.",
        "Silence notifications during study sessions and batch replies afterwards.",
    ]},
    "Memory": {"color": "#7c3aed", "tips": [
        "Test yourself instead of rereading. Pulling an answer out of memory beats passive review.",
        "Space your reviews: 1 day, 3 days, 1 week, then 1 month.",
        "Explain the idea out loud as if teaching a friend. Gaps in your explanation are gaps in your understanding.",
        "Mix problem types within a session. It feels harder, but it makes learning stick.",
        "Sleep after studying. Memories consolidate overnight, so late-night cramming backfires.",
    ]},
    "Time Management": {"color": "#d97706", "tips": [
        "Give every task a deadline and a home in your week. An untimed task is a wish.",
        "Plan tomorrow before you stop today.",
        "Do the hardest task when your energy is highest, usually early in the day.",
        "Break big assignments into steps that each fit inside one study session.",
        "Add a 20% buffer to every time estimate. Things almost always take longer than planned.",
    ]},
    "Exam Prep": {"color": "#dc2626", "tips": [
        "Work backwards from the exam date and give every topic a revision slot.",
        "Practise past papers under timed conditions at least once before the exam.",
        "Keep a list of your mistakes and review it the night before. Errors repeat.",
        "Prepare your things the evening before so the exam morning stays calm.",
        "Read every question twice and sketch a quick plan before you start writing.",
    ]},
    "Wellbeing": {"color": "#0d9488", "tips": [
        "Aim for 7 to 9 hours of sleep. Tired brains learn slowly and forget fast.",
        "Take a short walk between sessions. Movement resets attention.",
        "Eat regular meals and keep water nearby. Studying on empty rarely goes well.",
        "Talk to someone when you feel overwhelmed. Asking for help is part of studying well.",
        "Schedule real time off each week and protect it like a lecture.",
    ]},
    "Note Taking": {"color": "#db2777", "tips": [
        "Write notes in your own words instead of copying slides word for word.",
        "Leave a margin for questions, and review your notes within 24 hours.",
        "Use headings and numbering so your notes can be scanned quickly.",
        "Summarise each page in one sentence at the bottom.",
        "Turn your notes into questions and use them as flashcards.",
    ]},
}


def tip_of_the_day():
    cats = list(TIPS.keys())
    n = datetime.date.today().toordinal()
    cat = cats[n % len(cats)]
    tips = TIPS[cat]["tips"]
    return cat, tips[(n // len(cats)) % len(tips)]


# ============================================================
#  Look & feel helpers
# ============================================================
THEMES = {
    "Dark": dict(
        BG="#242424", SIDEBAR_BG="#212121", CARD="#2b2b2b", CARD_INNER="#313131",
        NAV_ACTIVE="#3f3f3f", HOVER="#2f2f2f", MUTED="#8a8a8a", TEXT="#ffffff",
        TEXT_DIM="#e6e6e6", INPUT_BG="#343638", INPUT_BORDER="#565b5e", TRACK="#3a3a3a",
        BORDER="#444444", SWITCH_OFF="#4a4d50", KNOB="#d5d9de", THUMB="#4d4d4d"),
    "Light": dict(
        BG="#f3f4f6", SIDEBAR_BG="#e5e7eb", CARD="#ffffff", CARD_INNER="#f1f5f9",
        NAV_ACTIVE="#d1d5db", HOVER="#e5e7eb", MUTED="#6b7280", TEXT="#111827",
        TEXT_DIM="#374151", INPUT_BG="#f9fafb", INPUT_BORDER="#cbd5e1", TRACK="#d1d5db",
        BORDER="#d1d5db", SWITCH_OFF="#9ca3af", KNOB="#ffffff", THUMB="#b6bcc6"),
}
FONT_MAIN = "Arial"
FONT_NARROW = "Arial Narrow"   # headings and buttons
GRAY_BTN = "#5a5a5a"
RED = "#ef4444"
GREEN = "#2fa572"
ACCENT = "#14b8a6"
COMBO_BLUE = ACCENT          # dropdowns, follow the accent colour (see set_accent)
SWITCH_BLUE = ACCENT         # toggle switches and Settings dropdowns, follow the accent colour
SWITCH_BLUE_DARK = "#0e8074"


def set_theme(mode):
    """Switch the module-level colour constants to the Dark or Light palette."""
    for key, value in THEMES.get(mode, THEMES["Dark"]).items():
        globals()[key] = value


set_theme("Dark")

# Base sizes in this file are written for 100% text scale; the app starts at 80%
# (as in the design) and the Text -/+ buttons in the sidebar change it live.
UI_SCALE = [0.8]
_CHEVRON = [None]


def S(n):
    """Scale a pixel size by the current text scale."""
    return max(1, int(round(n * UI_SCALE[0])))


def lighter(color, factor=115):
    return QColor(color).lighter(factor).name()


def darker(color, factor=135):
    return QColor(color).darker(factor).name()


def set_accent(color):
    """Point every accent-driven colour (toggles, dropdowns, radio/check boxes, highlights) at one colour."""
    global ACCENT, COMBO_BLUE, SWITCH_BLUE, SWITCH_BLUE_DARK
    ACCENT = COMBO_BLUE = SWITCH_BLUE = color
    SWITCH_BLUE_DARK = darker(color)


def make_label(text="", size=14, color=None, bold=False, wrap=False, align=None):
    color = color or TEXT
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {color}; font-size: {S(size)}px; "
        f"font-family: '{FONT_NARROW if bold else FONT_MAIN}'; "
        f"font-weight: {'bold' if bold else 'normal'}; background: transparent;")
    if wrap:
        lbl.setWordWrap(True)
    if align is not None:
        lbl.setAlignment(align)
    return lbl


def make_button(text, bg, fg="#ffffff", w=None, h=32, size=12, bold=False, radius=6, on_click=None):
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    if w:
        b.setFixedWidth(S(w))
    b.setFixedHeight(S(h))
    b.setStyleSheet(
        f"QPushButton {{ background-color: {bg}; color: {fg}; border: none; "
        f"border-radius: {S(radius)}px; font-size: {S(size)}px; font-family: '{FONT_NARROW}'; "
        f"font-weight: {'bold' if bold else 'normal'}; padding: 0 {S(10)}px; }} "
        f"QPushButton:hover {{ background-color: {lighter(bg)}; }}")
    if on_click:
        # clicked() emits a 'checked' bool; swallow it so lambdas with default
        # arguments (e.g. `lambda u=unit: ...`) keep their bound values.
        b.clicked.connect(lambda _checked=False, cb=on_click: cb())
    return b


def make_card(bg=None, radius=12, border=None, name="card"):
    bg = bg or CARD
    f = QFrame()
    f.setObjectName(name)
    b = f"border: {border};" if border else "border: none;"
    f.setStyleSheet(f"QFrame#{name} {{ background-color: {bg}; {b} border-radius: {S(radius)}px; }}")
    return f


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())
            item.layout().deleteLater()


def greeting():
    h = datetime.datetime.now().hour
    if h < 12: return "Good morning"
    if h < 17: return "Good afternoon"
    return "Good evening"


def chevron_url():
    """Small white chevron used on the blue filter dropdowns (generated once)."""
    if _CHEVRON[0] is None:
        path = APP_DIR / "chevron.png"
        try:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            pm = QPixmap(24, 24)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            pen = QPen(QColor("white"))
            pen.setWidth(3)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawLine(6, 9, 12, 15)
            p.drawLine(12, 15, 18, 9)
            p.end()
            pm.save(str(path), "PNG")
            _CHEVRON[0] = path.as_posix()
        except Exception:
            _CHEVRON[0] = ""
    return _CHEVRON[0]


def filter_combo_css(blue=None, dark=None):
    blue = blue or COMBO_BLUE
    dark = dark or darker(blue)
    arrow = f"image: url(\"{chevron_url()}\"); width: {S(12)}px; height: {S(12)}px;" if chevron_url() else ""
    return (
        f"QComboBox {{ background-color: {blue}; color: white; border: none; "
        f"border-radius: {S(5)}px; padding-left: {S(12)}px; font-size: {S(15)}px; }} "
        f"QComboBox::drop-down {{ border: none; background-color: {dark}; width: {S(32)}px; "
        f"border-top-right-radius: {S(5)}px; border-bottom-right-radius: {S(5)}px; }} "
        f"QComboBox::down-arrow {{ {arrow} }} "
        f"QComboBox QAbstractItemView {{ background-color: {CARD}; color: {TEXT}; border: 1px solid {BORDER}; "
        f"selection-background-color: {blue}; selection-color: white; outline: 0; }}")


def style_combo(cb, blue=None, dark=None):
    """Apply the blue filter style AND make the popup list readable in both themes.

    The combo itself has white text on blue, which the popup list used to inherit;
    in the Light theme that gave white text on a white list.
    """
    cb.setStyleSheet(filter_combo_css(blue, dark))
    cb.setItemDelegate(QStyledItemDelegate(cb))      # honours the ::item rules below
    accent = blue or COMBO_BLUE
    view = cb.view()
    pal = view.palette()
    for role, col in ((QPalette.Base, CARD), (QPalette.Window, CARD),
                      (QPalette.Text, TEXT), (QPalette.WindowText, TEXT),
                      (QPalette.Highlight, accent), (QPalette.HighlightedText, "#ffffff")):
        pal.setColor(role, QColor(col))
    view.setPalette(pal)
    view.setStyleSheet(
        f"QAbstractItemView {{ background-color: {CARD}; color: {TEXT}; border: 1px solid {BORDER}; "
        f"selection-background-color: {accent}; selection-color: #ffffff; outline: 0; }} "
        f"QAbstractItemView::item {{ color: {TEXT}; padding: {S(4)}px {S(8)}px; min-height: {S(22)}px; }} "
        f"QAbstractItemView::item:selected, QAbstractItemView::item:hover {{ background-color: {accent}; color: #ffffff; }}")


def scrollbar_css(thumb=None, track="transparent"):
    thumb = thumb or THUMB
    return (
        f"QScrollBar:vertical {{ background: {track}; width: {S(10)}px; margin: 0; border-radius: {S(5)}px; }} "
        f"QScrollBar::handle:vertical {{ background: {thumb}; border-radius: {S(5)}px; min-height: {S(30)}px; }} "
        f"QScrollBar:horizontal {{ background: {track}; height: {S(10)}px; margin: 0; border-radius: {S(5)}px; }} "
        f"QScrollBar::handle:horizontal {{ background: {thumb}; border-radius: {S(5)}px; min-width: {S(30)}px; }} "
        "QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; background: none; } "
        "QScrollBar::add-page, QScrollBar::sub-page { background: none; }")


# ============================================================
#  Custom Widgets
# ============================================================
class ScrollContainer(QScrollArea):
    """Vertical scroll area whose content is a QVBoxLayout (`vbox`)."""
    def __init__(self, parent=None, left=0, right=14):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("QScrollArea { background: transparent; border: none; } " + scrollbar_css())
        self.viewport().setAutoFillBackground(False)
        self.container = QWidget()
        self.container.setObjectName("scrollContainer")
        self.container.setStyleSheet("QWidget#scrollContainer { background: transparent; }")
        self.vbox = QVBoxLayout(self.container)
        self.vbox.setContentsMargins(S(left), 0, S(right), 0)
        self.vbox.setSpacing(S(10))
        self.setWidget(self.container)
        self._saved = 0

    def begin_rebuild(self):
        self._saved = self.verticalScrollBar().value()
        clear_layout(self.vbox)

    def end_rebuild(self):
        self.vbox.addStretch(1)
        v = self._saved
        QTimer.singleShot(0, lambda: self._restore(v))

    def _restore(self, v):
        try:
            self.verticalScrollBar().setValue(v)
        except RuntimeError:
            pass  # widget was destroyed by a UI rebuild


class StatCard(QFrame):
    def __init__(self, label, val, color):
        super().__init__()
        self.setObjectName("statCard")
        self.setStyleSheet(f"QFrame#statCard {{ background-color: {CARD}; border-radius: {S(12)}px; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(S(12), S(16), S(12), S(14))
        lay.setSpacing(S(4))
        lay.addWidget(make_label(str(val), 34, color, True, align=Qt.AlignCenter))
        lay.addWidget(make_label(label, 13, MUTED, align=Qt.AlignCenter))


class Toast(QWidget):
    def __init__(self, parent, title, message, accent="#14b8a6"):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setObjectName("toast")
        self.setStyleSheet(f"QWidget#toast {{ background-color: {CARD}; border: 1px solid {accent}; border-radius: 8px; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)

        t = QLabel(title)
        t.setStyleSheet(f"color: {accent}; font-weight: bold; font-size: 13px; border: none; background: transparent;")
        m = QLabel(message)
        m.setStyleSheet(f"color: {TEXT}; font-size: 12px; border: none; background: transparent;")
        m.setWordWrap(True)
        layout.addWidget(t)
        layout.addWidget(m)

        self.adjustSize()
        if parent:
            p_geo = parent.geometry()
            self.move(p_geo.x() + p_geo.width() - self.width() - 20, p_geo.y() + 40)

        self.show()
        QTimer.singleShot(4000, lambda: self.deleteLater())


# ============================================================
#  Dialogs
# ============================================================
# ---- Modern date / time picker widgets ---------------------------------
def glyph_url(kind, color):
    """Small anti-aliased PNG glyph ('up', 'down' or 'calendar') in `color`, cached on disk."""
    path = APP_DIR / f"glyph_{kind}_{str(color).lstrip('#')}.png"
    try:
        if not path.exists():
            APP_DIR.mkdir(parents=True, exist_ok=True)
            pm = QPixmap(48, 48)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            pen = QPen(QColor(color))
            pen.setWidth(4 if kind != "calendar" else 3)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            if kind == "up":
                p.drawLine(13, 30, 24, 18); p.drawLine(24, 18, 35, 30)
            elif kind == "down":
                p.drawLine(13, 18, 24, 30); p.drawLine(24, 30, 35, 18)
            else:
                p.drawRoundedRect(7, 10, 34, 31, 7, 7)
                p.drawLine(7, 21, 41, 21)
                p.drawLine(16, 5, 16, 14); p.drawLine(32, 5, 32, 14)
                p.setPen(Qt.NoPen); p.setBrush(QColor(color))
                p.drawEllipse(15, 27, 5, 5); p.drawEllipse(28, 27, 5, 5)
            p.end()
            pm.save(str(path), "PNG")
        return path.as_posix()
    except Exception:
        return ""


class ModernCalendar(QCalendarWidget):
    """Clean month view: round selection, ringed 'today', single-letter weekdays, no grid."""
    def __init__(self, accent):
        super().__init__()
        self.accent = accent
        self.setGridVisible(False)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QCalendarWidget.SingleLetterDayNames)
        self.setNavigationBarVisible(True)
        self.setFirstDayOfWeek(Qt.Monday)
        self.setMinimumSize(320, 300)

        head = QTextCharFormat()
        head.setForeground(QColor(MUTED))
        head.setFontWeight(QFont.Bold)
        self.setHeaderTextFormat(head)
        for d in (Qt.Saturday, Qt.Sunday):
            self.setWeekdayTextFormat(d, QTextCharFormat())

        for name, glyph in (("qt_calendar_prevmonth", "‹"), ("qt_calendar_nextmonth", "›")):
            b = self.findChild(QToolButton, name)
            if b is not None:
                b.setIcon(QIcon())
                b.setText(glyph)
                b.setCursor(Qt.PointingHandCursor)
        for name in ("qt_calendar_monthbutton", "qt_calendar_yearbutton"):
            b = self.findChild(QToolButton, name)
            if b is not None:
                b.setCursor(Qt.PointingHandCursor)

        self.setStyleSheet(f"""
            QCalendarWidget {{ background-color: {CARD}; border: 1px solid {BORDER}; }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{ background-color: {CARD}; padding: 6px 6px 2px 6px; }}
            QCalendarWidget QToolButton {{ background: transparent; color: {TEXT}; border: none;
                border-radius: 8px; padding: 6px 10px; font-size: 14px; font-weight: bold; }}
            QCalendarWidget QToolButton:hover {{ background-color: {HOVER}; }}
            QCalendarWidget QToolButton#qt_calendar_prevmonth,
            QCalendarWidget QToolButton#qt_calendar_nextmonth {{ font-size: 22px; min-width: 30px; padding: 0 8px; }}
            QCalendarWidget QToolButton::menu-indicator {{ image: none; width: 0px; }}
            QCalendarWidget QMenu {{ background-color: {CARD}; color: {TEXT}; border: 1px solid {BORDER}; padding: 4px; }}
            QCalendarWidget QMenu::item {{ padding: 6px 18px; border-radius: 6px; }}
            QCalendarWidget QMenu::item:selected {{ background-color: {accent}; color: white; }}
            QCalendarWidget QSpinBox {{ background-color: {INPUT_BG}; color: {TEXT}; border: 1px solid {INPUT_BORDER};
                border-radius: 6px; padding: 2px 6px; font-size: 14px; selection-background-color: {accent}; }}
            QCalendarWidget QAbstractItemView {{ background-color: {CARD}; color: {TEXT};
                selection-background-color: transparent; selection-color: {TEXT}; outline: 0; font-size: 13px; }}
            QCalendarWidget QAbstractItemView:disabled {{ color: {MUTED}; }}
        """)

    def paintCell(self, painter, rect, date):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        selected = date == self.selectedDate()
        today = date == QDate.currentDate()
        in_month = date.month() == self.monthShown() and date.year() == self.yearShown()
        enabled = self.minimumDate() <= date <= self.maximumDate()

        d = max(8, min(rect.width(), rect.height()) - 6)
        circle = QRect(0, 0, d, d)
        circle.moveCenter(rect.center())
        if selected:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(self.accent))
            painter.drawEllipse(circle)
        elif today:
            pen = QPen(QColor(self.accent))
            pen.setWidthF(1.6)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(circle.adjusted(1, 1, -1, -1))

        if selected:
            color = QColor("white")
        elif not enabled:
            color = QColor(MUTED); color.setAlpha(90)
        elif not in_month:
            color = QColor(MUTED); color.setAlpha(120)
        elif today:
            color = QColor(self.accent)
        else:
            color = QColor(TEXT)
        font = painter.font()
        font.setBold(selected or today)
        painter.setFont(font)
        painter.setPen(color)
        painter.drawText(rect, Qt.AlignCenter, str(date.day()))
        painter.restore()


class ModernDateEdit(QDateEdit):
    """Rounded date field with a calendar glyph that opens the modern calendar popup."""
    def __init__(self, accent):
        super().__init__()
        self.setCalendarPopup(True)
        self.setCalendarWidget(ModernCalendar(accent))
        self.setDisplayFormat("ddd, d MMM yyyy")
        self.setMinimumDate(QDate(2000, 1, 1))
        self.setCursor(Qt.PointingHandCursor)
        icon = glyph_url("calendar", accent)
        arrow = f'image: url("{icon}"); width: 18px; height: 18px;' if icon else ""
        self.setStyleSheet(f"""
            QDateEdit {{ background-color: {INPUT_BG}; color: {TEXT}; border: 1px solid {INPUT_BORDER};
                border-radius: 8px; padding: 8px 40px 8px 12px; font-size: 14px; font-weight: bold;
                selection-background-color: {accent}; }}
            QDateEdit:hover {{ border-color: {accent}; }}
            QDateEdit:focus {{ border: 2px solid {accent}; padding: 7px 39px 7px 11px; }}
            QDateEdit:disabled {{ color: #6a6a6a; border-color: {BORDER}; }}
            QDateEdit::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right;
                width: 36px; border: none; background: transparent; }}
            QDateEdit::down-arrow {{ {arrow} }}
        """)


class ZeroPadSpin(QSpinBox):
    def textFromValue(self, value):
        return f"{value:02d}"


class TimePicker(QWidget):
    """HH : MM stepper. Wheel, arrow keys, the little chevrons and typing all work."""
    timeChanged = Signal(QTime)

    def __init__(self, accent):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.hour, self.minute = ZeroPadSpin(), ZeroPadSpin()
        self.hour.setRange(0, 23)
        self.minute.setRange(0, 59)
        up, down = glyph_url("up", MUTED), glyph_url("down", MUTED)
        css = f"""
            QSpinBox {{ background-color: {INPUT_BG}; color: {TEXT}; border: 1px solid {INPUT_BORDER};
                border-radius: 8px; padding: 8px 22px 8px 8px; font-size: 16px; font-weight: bold;
                selection-background-color: {accent}; }}
            QSpinBox:hover {{ border-color: {accent}; }}
            QSpinBox:focus {{ border: 2px solid {accent}; padding: 7px 21px 7px 7px; }}
            QSpinBox:disabled {{ color: #6a6a6a; border-color: {BORDER}; }}
            QSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right;
                width: 22px; border: none; background: transparent; margin: 3px 3px 0 0; border-top-right-radius: 6px; }}
            QSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right;
                width: 22px; border: none; background: transparent; margin: 0 3px 3px 0; border-bottom-right-radius: 6px; }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background-color: {HOVER}; }}
            QSpinBox::up-arrow {{ image: url("{up}"); width: 10px; height: 10px; }}
            QSpinBox::down-arrow {{ image: url("{down}"); width: 10px; height: 10px; }}
        """
        for sp in (self.hour, self.minute):
            sp.setWrapping(True)
            sp.setAccelerated(True)
            sp.setAlignment(Qt.AlignCenter)
            sp.setFixedWidth(86)
            sp.setStyleSheet(css)
            sp.valueChanged.connect(lambda _=0: self.timeChanged.emit(self.time()))
        colon = QLabel(":")
        colon.setStyleSheet(f"color: {TEXT}; font-size: 18px; font-weight: bold; background: transparent;")
        lay.addWidget(self.hour)
        lay.addWidget(colon)
        lay.addWidget(self.minute)
        lay.addStretch(1)

    def time(self):
        return QTime(self.hour.value(), self.minute.value())

    def setTime(self, t):
        self.hour.setValue(t.hour())
        self.minute.setValue(t.minute())


def make_chip(text, accent):
    """Small pill button for quick picks (Today, Tomorrow, 09:00, ...)."""
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet(
        f"QPushButton {{ background-color: transparent; color: {TEXT}; border: 1px solid {INPUT_BORDER}; "
        f"border-radius: 13px; padding: 4px 13px; font-size: 12px; }} "
        f"QPushButton:hover {{ background-color: {accent}; border-color: {accent}; color: white; }} "
        f"QPushButton:disabled {{ color: #6a6a6a; border-color: {BORDER}; background-color: transparent; }}")
    return b


class BaseDialog(QDialog):
    def __init__(self, parent=None, title="Dialog", w=400, h=400):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(w, h)
        self.accent = getattr(parent, "accent", "#14b8a6")
        self.setStyleSheet(f"""
            QDialog {{ background-color: {BG}; color: {TEXT}; }}
            QLabel {{ color: {TEXT}; background: transparent; }}
            QLineEdit, QComboBox {{ background-color: {INPUT_BG}; color: {TEXT}; padding: 6px; border: 1px solid {INPUT_BORDER}; border-radius: 6px; }}
            QLineEdit:focus, QComboBox:focus {{ border-color: {self.accent}; }}
            QCheckBox {{ color: {TEXT}; spacing: 6px; }}
            QComboBox QAbstractItemView {{ background-color: {CARD}; color: {TEXT}; selection-background-color: {self.accent}; selection-color: white; }}
            QPushButton {{ background-color: {GRAY_BTN}; color: white; padding: 8px 15px; border-radius: 4px; border: none; }}
            QPushButton:hover {{ background-color: #6b6b6b; }}
        """)
        self.root = QVBoxLayout(self)


class UnitDialog(BaseDialog):
    def __init__(self, parent, store, on_save, unit=None):
        super().__init__(parent, "Edit Unit" if unit else "Add Unit", 350, 250)
        self.store, self.on_save, self.unit = store, on_save, unit

        form = QFormLayout()
        self.name_inp = QLineEdit(unit.get("name", "") if unit else "")
        self.code_inp = QLineEdit(unit.get("code", "") if unit else "")

        self.color_cb = QComboBox()
        self.color_cb.addItems(list(UNIT_COLOR_NAMES.keys()))
        if unit:
            for k, v in UNIT_COLOR_NAMES.items():
                if v.lower() == unit.get("color", "").lower():
                    self.color_cb.setCurrentText(k)
                    break

        form.addRow("Name:", self.name_inp)
        form.addRow("Code:", self.code_inp)
        form.addRow("Color:", self.color_cb)
        self.root.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.save)
        btns.rejected.connect(self.reject)
        self.root.addWidget(btns)

    def save(self):
        name = self.name_inp.text().strip()
        if not name: return
        color = UNIT_COLOR_NAMES[self.color_cb.currentText()]
        if self.unit: self.store.update_unit(self.unit["id"], name=name, code=self.code_inp.text().strip(), color=color)
        else: self.store.add_unit(name, self.code_inp.text().strip(), color)
        self.on_save()
        self.accept()


class TaskDialog(BaseDialog):
    def __init__(self, parent, store, on_save, task=None, preset_unit=None, preset_type=None):
        super().__init__(parent, "Edit Task" if task else "Add Task", 480, 560)
        self.store, self.task, self.on_save = store, task, on_save

        form = QFormLayout()
        self.title_inp = QLineEdit(task.get("title", "") if task else "")
        form.addRow("Title:", self.title_inp)

        self.type_cb = QComboBox()
        self.type_cb.addItems([TYPE_LABELS[t] for t in TASK_TYPES])
        if task: self.type_cb.setCurrentText(TYPE_LABELS.get(task.get("type"), "Deadline"))
        elif preset_type: self.type_cb.setCurrentText(TYPE_LABELS.get(preset_type, "Deadline"))
        form.addRow("Type:", self.type_cb)

        self.unit_cb = QComboBox()
        self.unit_map = {"General": None}
        for u in store.units:
            lbl = f"{u['name']} ({u['code']})" if u.get("code") else u["name"]
            self.unit_map[lbl] = u["id"]
            self.unit_cb.addItem(lbl)
        self.unit_cb.addItem("General")
        if task and task.get("unit_id"):
            for lbl, uid in self.unit_map.items():
                if uid == task["unit_id"]: self.unit_cb.setCurrentText(lbl); break
        elif preset_unit:
            for lbl, uid in self.unit_map.items():
                if uid == preset_unit: self.unit_cb.setCurrentText(lbl); break
        form.addRow("Unit:", self.unit_cb)

        existing_due = parse_due(task.get("due")) if task else None
        self.has_due_cb = QCheckBox("Set a due date")
        self.has_due_cb.setChecked(existing_due is not None or task is None)
        form.addRow("Due:", self.has_due_cb)

        acc = self.accent
        self.date_inp = ModernDateEdit(acc)
        self.time_inp = TimePicker(acc)
        if existing_due:
            self.date_inp.setDate(QDate(existing_due.year, existing_due.month, existing_due.day))
            self.time_inp.setTime(QTime(existing_due.hour, existing_due.minute))
        else:
            self.date_inp.setDate(QDate.currentDate())
            self.time_inp.setTime(QTime(23, 59))
        form.addRow("Date:", self.date_inp)

        # Quick date picks
        date_chips = []
        quick_dates = QHBoxLayout()
        quick_dates.setSpacing(8)
        for text, days in (("Today", 0), ("Tomorrow", 1), ("Next week", 7)):
            chip = make_chip(text, acc)
            chip.clicked.connect(lambda _=False, n=days: self.date_inp.setDate(QDate.currentDate().addDays(n)))
            quick_dates.addWidget(chip)
            date_chips.append(chip)
        quick_dates.addStretch(1)
        form.addRow("", quick_dates)

        form.addRow("Time:", self.time_inp)

        # Quick time picks
        time_chips = []
        quick_times = QHBoxLayout()
        quick_times.setSpacing(8)
        for text in ("09:00", "12:00", "18:00", "23:59"):
            chip = make_chip(text, acc)
            hh, mm = (int(x) for x in text.split(":"))
            chip.clicked.connect(lambda _=False, h=hh, m=mm: self.time_inp.setTime(QTime(h, m)))
            quick_times.addWidget(chip)
            time_chips.append(chip)
        quick_times.addStretch(1)
        form.addRow("", quick_times)

        # Live summary of what will be saved
        self.due_summary = QLabel()
        self.due_summary.setWordWrap(True)
        form.addRow("", self.due_summary)

        self._due_widgets = (self.date_inp, self.time_inp, *date_chips, *time_chips)
        self.date_inp.dateChanged.connect(lambda _d: self._update_due_summary())
        self.time_inp.timeChanged.connect(lambda _t: self._update_due_summary())
        self.has_due_cb.toggled.connect(self._toggle_due)
        self._toggle_due(self.has_due_cb.isChecked())

        self.notes_inp = QLineEdit(task.get("notes", "") if task else "")
        form.addRow("Notes:", self.notes_inp)

        self.root.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.save)
        btns.rejected.connect(self.reject)
        self.root.addWidget(btns)

    def _toggle_due(self, on):
        for w in self._due_widgets:
            w.setEnabled(on)
        self._update_due_summary()

    def _update_due_summary(self):
        if not self.has_due_cb.isChecked():
            self.due_summary.setText("No due date")
            col = MUTED
        else:
            d, t = self.date_inp.date(), self.time_inp.time()
            dt = datetime.datetime(d.year(), d.month(), d.day(), t.hour(), t.minute())
            span, col = fmt_countdown(dt)
            self.due_summary.setText(f"{dt.strftime('%a, %d %b %Y')} · {dt.strftime('%H:%M')}  —  {span}")
        self.due_summary.setStyleSheet(f"color: {col}; font-size: 12px; font-weight: bold; background: transparent;")

    def save(self):
        title = self.title_inp.text().strip()
        if not title: return
        type_key = next(k for k, v in TYPE_LABELS.items() if v == self.type_cb.currentText())
        uid = self.unit_map.get(self.unit_cb.currentText())
        if self.has_due_cb.isChecked():
            d, t = self.date_inp.date(), self.time_inp.time()
            due = datetime.datetime(d.year(), d.month(), d.day(), t.hour(), t.minute()).isoformat(timespec="minutes")
        else:
            due = ""
        if self.task:
            self.store.update_task(self.task["id"], title=title, type=type_key, unit_id=uid, due=due, notes=self.notes_inp.text().strip())
        else:
            self.store.add_task(title, type_key, due, uid, self.notes_inp.text().strip())
        self.on_save()
        self.accept()


class LessonDialog(BaseDialog):
    def __init__(self, parent, store, on_save, lesson=None):
        super().__init__(parent, "Edit Lesson" if lesson else "Add Lesson", 400, 350)
        self.store, self.lesson, self.on_save = store, lesson, on_save

        form = QFormLayout()
        self.unit_cb = QComboBox()
        for u in store.units:
            lbl = f"{u['name']} ({u['code']})" if u.get("code") else u["name"]
            self.unit_cb.addItem(lbl, u["id"])
        if lesson:
            for i in range(self.unit_cb.count()):
                if self.unit_cb.itemData(i) == lesson["unit_id"]: self.unit_cb.setCurrentIndex(i); break
        form.addRow("Unit:", self.unit_cb)

        self.day_cb = QComboBox()
        self.day_cb.addItems(WEEKDAY_NAMES)
        if lesson: self.day_cb.setCurrentIndex(lesson.get("day", 0))
        form.addRow("Day:", self.day_cb)

        self.start_inp = QLineEdit(lesson.get("start", "09:00") if lesson else "09:00")
        self.end_inp = QLineEdit(lesson.get("end", "10:00") if lesson else "10:00")
        form.addRow("Start (HH:MM):", self.start_inp)
        form.addRow("End (HH:MM):", self.end_inp)

        self.kind_cb = QComboBox()
        self.kind_cb.addItems(LESSON_KINDS)
        if lesson: self.kind_cb.setCurrentText(lesson.get("kind", "Lecture"))
        form.addRow("Type:", self.kind_cb)

        self.loc_inp = QLineEdit(lesson.get("location", "") if lesson else "")
        form.addRow("Location:", self.loc_inp)

        self.root.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.save)
        btns.rejected.connect(self.reject)
        self.root.addWidget(btns)

    def save(self):
        uid = self.unit_cb.currentData()
        day = self.day_cb.currentIndex()
        start, end = self.start_inp.text().strip(), self.end_inp.text().strip()
        if not uid or end <= start: return
        if self.lesson:
            self.store.update_lesson(self.lesson["id"], unit_id=uid, day=day, start=start, end=end, kind=self.kind_cb.currentText(), location=self.loc_inp.text().strip())
        else:
            self.store.add_lesson(uid, day, start, end, self.kind_cb.currentText(), self.loc_inp.text().strip())
        self.on_save()
        self.accept()


# ============================================================
#  Cards used by the pages
# ============================================================
def separator():
    return make_label("|", 12, "#5a5a5a")


class TaskCard(QFrame):
    """One row in the Planner."""
    def __init__(self, task, store, app):
        super().__init__()
        self.task, self.store, self.app = task, store, app
        self.setObjectName("taskCard")
        self.setStyleSheet(f"QFrame#taskCard {{ background-color: {CARD}; border-radius: {S(12)}px; }}")
        self.setMinimumHeight(S(100))

        outer = QHBoxLayout(self)
        outer.setContentsMargins(S(14), S(16), S(18), S(16))
        outer.setSpacing(S(14))

        self.cb = QCheckBox()
        self.cb.setChecked(bool(task.get("done", False)))
        self.cb.setCursor(Qt.PointingHandCursor)
        self.cb.setStyleSheet(
            f"QCheckBox {{ background: transparent; }} "
            f"QCheckBox::indicator {{ width: {S(24)}px; height: {S(24)}px; border-radius: {S(6)}px; "
            f"border: 2px solid #9a9a9a; background: transparent; }} "
            f"QCheckBox::indicator:hover {{ border-color: #d0d0d0; }} "
            f"QCheckBox::indicator:checked {{ background-color: {app.accent}; border-color: {app.accent}; }}")
        self.cb.clicked.connect(lambda: self.toggle())
        outer.addWidget(self.cb, 0, Qt.AlignTop)

        content = QVBoxLayout()
        content.setSpacing(S(12))
        content.addStretch(1)

        done = bool(task.get("done"))
        title_css = "color: #888888; text-decoration: line-through;" if done else f"color: {TEXT};"
        t_lbl = QLabel(task.get("title", "Untitled"))
        t_lbl.setStyleSheet(f"{title_css} font-weight: bold; font-size: {S(16)}px; background: transparent;")
        content.addWidget(t_lbl)

        meta = QHBoxLayout()
        meta.setSpacing(S(10))
        parts = []

        u_col = store.unit_color(task.get("unit_id"))
        parts.append(make_label(store.unit_name(task.get("unit_id")).upper(), 12, u_col))
        parts.append(make_label(TYPE_LABELS.get(task.get("type"), "Task"), 12, TYPE_COLORS.get(task.get("type"), TEXT)))
        parts.append(make_label(fmt_due(task.get("due")), 12, "#9a9a9a"))

        if not done and task.get("type") in ("deadline", "test") and task.get("due"):
            cd_txt, cd_col = fmt_countdown(task.get("due"))
            parts.append(make_label(cd_txt, 12, cd_col, True))

        logged = store.total_seconds_for_task(task["id"])
        if logged >= 30:
            parts.append(make_label(fmt_minutes(logged) + " logged", 12, GREEN))

        for i, p in enumerate(parts):
            if i: meta.addWidget(separator())
            meta.addWidget(p)
        meta.addStretch(1)
        content.addLayout(meta)
        content.addStretch(1)
        outer.addLayout(content, 1)

        # Buttons (right-aligned so Start/Edit/Delete line up across rows)
        if task.get("file_path"):
            open_btn = make_button("Open", GRAY_BTN, w=68, h=32,
                                   on_click=lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(task["file_path"])))
            outer.addWidget(open_btn, 0, Qt.AlignVCenter)
        outer.addWidget(make_button("Start", app.accent, w=68, h=32, on_click=lambda: app.start_session(task["id"])), 0, Qt.AlignVCenter)
        outer.addWidget(make_button("Edit", GRAY_BTN, w=68, h=32,
                                    on_click=lambda: TaskDialog(app, store, app.refresh_page, task=task).exec()), 0, Qt.AlignVCenter)
        outer.addWidget(make_button("Delete", RED, w=68, h=32, on_click=lambda: self.delete()), 0, Qt.AlignVCenter)

    def toggle(self):
        self.store.toggle_done(self.task["id"])
        QTimer.singleShot(0, self.app.refresh_page)

    def delete(self):
        self.store.remove_task(self.task["id"])
        QTimer.singleShot(0, self.app.refresh_page)


class LessonCard(QFrame):
    """One lesson row in the Timetable."""
    def __init__(self, lesson, store, app):
        super().__init__()
        self.lesson, self.store, self.app = lesson, store, app
        self.setObjectName("lessonCard")
        self.setStyleSheet(f"QFrame#lessonCard {{ background-color: {CARD}; border-radius: {S(12)}px; }}")
        self.setMinimumHeight(S(92))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(S(14), S(12), S(18), S(12))
        layout.setSpacing(S(12))

        time_col = QVBoxLayout()
        time_col.setSpacing(S(2))
        time_col.addStretch(1)
        # Start and end share the same size, weight and colour so neither is
        # visually dominant; the column sizes to its content so nothing is clipped.
        time_col.addWidget(make_label(lesson.get("start", "--:--"), 16, TEXT, True))
        time_col.addWidget(make_label(lesson.get("end", "--:--"), 16, TEXT, True))
        time_col.addStretch(1)
        time_w = QWidget()
        time_w.setLayout(time_col)
        time_w.setMinimumWidth(S(64))
        layout.addWidget(time_w)

        unit = store.get_unit(lesson.get("unit_id"))
        u_name = unit["name"] if unit else "General"
        u_code = f" ({unit['code']})" if unit and unit.get("code") else ""
        u_color = unit["color"] if unit else "#8a8a8a"

        info = QVBoxLayout()
        info.setSpacing(S(4))
        info.addStretch(1)
        info.addWidget(make_label(f"{u_name}{u_code}", 17, u_color, True))
        loc = lesson.get("location", "")
        if loc:
            info.addWidget(make_label(loc, 12, MUTED))
        info.addStretch(1)
        layout.addLayout(info, 1)

        kind = lesson.get("kind", "Lecture")
        badge = QLabel(kind)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedHeight(S(32))
        badge.setMinimumWidth(S(66))
        badge.setStyleSheet(
            f"background-color: {LESSON_KIND_COLORS.get(kind, '#555555')}; color: white; "
            f"font-size: {S(12)}px; font-weight: bold; padding: 0 {S(12)}px; border-radius: {S(6)}px;")
        layout.addWidget(badge, 0, Qt.AlignVCenter)
        layout.addWidget(make_button("Edit", GRAY_BTN, w=70, h=32,
                                     on_click=lambda: LessonDialog(app, store, app.refresh_page, lesson=lesson).exec()), 0, Qt.AlignVCenter)
        layout.addWidget(make_button("Delete", RED, w=76, h=32, on_click=lambda: self.delete()), 0, Qt.AlignVCenter)

    def delete(self):
        self.store.remove_lesson(self.lesson["id"])
        QTimer.singleShot(0, self.app.refresh_page)


# ============================================================
#  Pages
# ============================================================
def page_layout(widget, left=22, top=28, right=10, bottom=10):
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(S(left), S(top), S(right), S(bottom))
    layout.setSpacing(S(10))
    return layout


class DashboardPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app, self.store = app, app.store
        layout = page_layout(self, left=21, top=30, right=10, bottom=0)
        self.scroll = ScrollContainer(left=16, right=14)
        layout.addWidget(self.scroll)
        self.refresh()

    # ---- small builders -------------------------------------------------
    def _lesson_row(self, lesson, now):
        u = self.store.get_unit(lesson.get("unit_id"))
        row = QHBoxLayout()
        row.setSpacing(S(12))
        row.addWidget(make_label(f"{lesson.get('start', '')}\u2013{lesson.get('end', '')}", 14, TEXT, True))
        row.addWidget(make_label(u["name"] if u else "General", 14, u["color"] if u else TEXT))
        row.addStretch(1)
        start, end = parse_time(lesson.get("start")), parse_time(lesson.get("end"))
        t = now.time()
        if start and end and start <= t < end:
            badge = QLabel("ON NOW")
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedHeight(S(32))
            badge.setStyleSheet(
                f"background-color: {GREEN}; color: white; font-size: {S(12)}px; "
                f"font-weight: bold; padding: 0 {S(12)}px; border-radius: {S(8)}px;")
            row.addWidget(badge)
        elif end and end <= t:
            row.addWidget(make_label("done", 12, MUTED))
        return row

    def _task_row(self, task, show_countdown=True):
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, S(4), 0, S(4))
        row.setSpacing(S(12))

        bar = QFrame()
        bar.setObjectName("unitBar")
        bar.setFixedWidth(S(3))
        bar.setStyleSheet(f"QFrame#unitBar {{ background-color: {self.store.unit_color(task.get('unit_id'))}; border-radius: {S(1)}px; }}")
        row.addWidget(bar)

        info = QVBoxLayout()
        info.setSpacing(S(6))
        info.addWidget(make_label(task.get("title", "Untitled"), 14, TEXT, True, wrap=True))
        meta = QHBoxLayout()
        meta.setSpacing(S(8))
        if show_countdown:
            cd_txt, cd_col = fmt_countdown(task.get("due"))
            pill = QLabel(cd_txt)
            pill.setStyleSheet(
                f"background-color: {cd_col}; color: white; font-size: {S(12)}px; font-weight: bold; "
                f"padding: {S(4)}px {S(10)}px; border-radius: {S(8)}px;")
            meta.addWidget(pill)
            meta.addWidget(make_label(f"{TYPE_LABELS.get(task.get('type'), 'Task')} - {fmt_due(task.get('due'))}", 12, "#9a9a9a"))
        else:
            d = parse_due(task.get("due"))
            when = d.strftime("%H:%M") if d else ""
            meta.addWidget(make_label(f"{self.store.unit_name(task.get('unit_id'))} \u00b7 {when}".strip(" \u00b7"), 12, "#9a9a9a"))
        meta.addStretch(1)
        info.addLayout(meta)
        row.addLayout(info, 1)

        row.addWidget(make_button("Start", self.app.accent, w=64, h=26, on_click=lambda: self.app.start_session(task["id"])), 0, Qt.AlignVCenter)
        return w

    # ---- page -----------------------------------------------------------
    def refresh(self):
        s = self.scroll
        s.begin_rebuild()
        v = s.vbox
        app, store = self.app, self.store
        now = datetime.datetime.now()
        today = datetime.date.today()

        name = app.settings.get("username") or "Student"
        v.addWidget(make_label(f"{greeting()}, {name}! Ready to study?", 30, TEXT, True))
        v.addWidget(make_label(today.strftime("%A, %d %B %Y"), 15, MUTED))
        v.addSpacing(S(4))

        # Stat cards
        stats = store.overall_stats()
        open_d = len([t for t in store.tasks if t.get("type") == "deadline" and not t.get("done")])
        up_t = len([t for t in store.tasks if t.get("type") == "test" and not t.get("done")])
        st_t = len([t for t in store.tasks
                    if t.get("type") == "study" and not t.get("done")
                    and (parse_due(t.get("due")) or datetime.datetime.max).date() == today])
        f_t = fmt_minutes(store.seconds_today())
        try: goal = float(app.settings.get("daily_goal_hours", 3) or 3)
        except (TypeError, ValueError): goal = 3.0
        row = QHBoxLayout()
        row.setSpacing(S(14))
        for lbl, val, col in [("Open Deadlines", open_d, "#ec4899"), ("Upcoming Tests", up_t, "#f59e0b"),
                              ("Sessions Today", st_t, "#3b82f6"), (f"Focus (goal {goal:g}h)", f_t, app.accent),
                              ("Overall", f"{stats['percent']:.0f}%", app.accent)]:
            row.addWidget(StatCard(lbl, val, col), 1)
        v.addLayout(row)

        # Tip of the day
        if app.settings.get("show_daily_tip", True):
            cat, tip = tip_of_the_day()
            tip_card = make_card("#d97706", 16, name="tipCard")
            tl = QVBoxLayout(tip_card)
            tl.setContentsMargins(S(20), S(18), S(20), S(18))
            tl.setSpacing(S(12))
            tl.addWidget(make_label(f"TIP OF THE DAY  -  {cat.upper()}", 13, "#ffffff", True))
            tl.addWidget(make_label(tip, 18, "#ffffff", wrap=True))
            tl.addWidget(make_button("More tips", "#ffffff", fg="#444444", w=118, h=32, size=14,
                                     on_click=lambda: app.navigate("Study Tips", tips_category=cat)), 0, Qt.AlignLeft)
            v.addWidget(tip_card)

        # Today's lessons + revise next
        mid = make_card(CARD, 14, name="midCard")
        ml = QHBoxLayout(mid)
        ml.setContentsMargins(S(16), S(16), S(16), S(16))
        ml.setSpacing(S(16))

        left = QVBoxLayout()
        left.setSpacing(S(14))
        head = QHBoxLayout()
        head.addWidget(make_label("TODAY'S LESSONS", 14, app.accent, True))
        head.addStretch(1)
        head.addWidget(make_button("Open timetable", GRAY_BTN, w=118, h=32, on_click=lambda: app.navigate("Timetable")))
        left.addLayout(head)
        todays = store.lessons_today()
        if not todays:
            left.addWidget(make_label("No lessons today.", 14, MUTED))
        for l in todays:
            left.addLayout(self._lesson_row(l, now))
        left.addStretch(1)
        ml.addLayout(left, 3)

        right = make_card(CARD_INNER, 12, name="reviseCard")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(S(14), S(14), S(14), S(14))
        rl.setSpacing(S(12))
        rl.addWidget(make_label("REVISE NEXT", 14, app.accent, True))
        sugs = store.revision_suggestions(limit=1)
        if not sugs:
            rl.addWidget(make_label("No suggestions.", 13, MUTED))
        else:
            sg = sugs[0]
            rl.addWidget(make_label(sg["unit"]["name"], 18, sg["unit"]["color"], True, wrap=True))
            rl.addWidget(make_label(sg["reason"], 12, "#9a9a9a", wrap=True))
            rl.addWidget(make_button("Plan revision", sg["unit"]["color"], w=130, h=32,
                                     on_click=lambda u=sg["unit"]: TaskDialog(app, store, app.refresh_page, preset_unit=u["id"], preset_type="study").exec()),
                         0, Qt.AlignLeft)
        rl.addStretch(1)
        ml.addWidget(right, 2)
        v.addWidget(mid)

        # Upcoming + today's sessions
        bottom = QHBoxLayout()
        bottom.setSpacing(S(14))

        up_card = make_card(CARD, 14, name="upCard")
        ul = QVBoxLayout(up_card)
        ul.setContentsMargins(S(16), S(16), S(16), S(16))
        ul.setSpacing(S(8))
        ul.addWidget(make_label("Upcoming Deadlines & Tests", 18, TEXT, True))
        ul.addSpacing(S(6))
        upcoming = []
        for t in store.tasks:
            if t.get("done") or t.get("type") not in ("deadline", "test"): continue
            d = parse_due(t.get("due"))
            if d and d >= now: upcoming.append((d, t))
        upcoming.sort(key=lambda x: x[0])
        if not upcoming:
            ul.addWidget(make_label("Nothing coming up.", 14, MUTED))
        for _, t in upcoming[:5]:
            ul.addWidget(self._task_row(t))
        ul.addStretch(1)
        bottom.addWidget(up_card, 54)

        ses_card = make_card(CARD, 14, name="sesCard")
        sl = QVBoxLayout(ses_card)
        sl.setContentsMargins(S(16), S(16), S(16), S(16))
        sl.setSpacing(S(8))
        sl.addWidget(make_label("Today's Study Sessions", 18, TEXT, True))
        sl.addSpacing(S(6))
        todays_sessions = [t for t in store.tasks
                           if t.get("type") == "study" and not t.get("done")
                           and (parse_due(t.get("due")) or datetime.datetime.max).date() == today]
        if not todays_sessions:
            sl.addWidget(make_label("No sessions scheduled for today.", 15, MUTED))
        for t in todays_sessions:
            sl.addWidget(self._task_row(t, show_countdown=False))

        # Study sessions not scheduled for today (later, overdue or undated) used to be
        # hidden everywhere on the dashboard, e.g. after editing a test into a study session.
        today_ids = {t["id"] for t in todays_sessions}
        other_sessions = [t for t in store.tasks
                          if t.get("type") == "study" and not t.get("done") and t["id"] not in today_ids]
        other_sessions.sort(key=lambda t: (parse_due(t.get("due")) is None,
                                           parse_due(t.get("due")) or datetime.datetime.max))
        if other_sessions:
            sl.addSpacing(S(8))
            sl.addWidget(make_label("Other study sessions", 14, MUTED, True))
            for t in other_sessions[:3]:
                sl.addWidget(self._task_row(t))
            if len(other_sessions) > 3:
                sl.addWidget(make_label(f"+{len(other_sessions) - 3} more in Planner", 12, MUTED))
        sl.addStretch(1)
        bottom.addWidget(ses_card, 46)
        v.addLayout(bottom)

        s.end_rebuild()


class PlannerPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app, self.store = app, app.store
        layout = page_layout(self, left=21, top=20, right=10, bottom=8)

        h = QHBoxLayout()
        h.addWidget(make_label("Planner", 30, TEXT, True))
        h.addStretch(1)
        h.addWidget(make_button("Add Task", app.accent, w=142, h=32, size=14,
                                on_click=lambda: TaskDialog(app, self.store, self.refresh).exec()), 0, Qt.AlignTop)
        layout.addLayout(h)

        f = QHBoxLayout()
        f.setSpacing(S(16))
        self.unit_cb = QComboBox()
        self.type_cb = QComboBox()
        self.type_cb.addItems(["All Types", "Deadline", "Test", "Study Session"])
        self.status_cb = QComboBox()
        self.status_cb.addItems(["All", "Open", "Done", "Overdue"])
        for cb in (self.unit_cb, self.type_cb, self.status_cb):
            cb.setFixedSize(S(166), S(32))
            cb.setCursor(Qt.PointingHandCursor)
            style_combo(cb)
            cb.currentIndexChanged.connect(lambda _=0: self.refresh())
            f.addWidget(cb)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search titles")
        self.search.setFixedHeight(S(32))
        self.search.setStyleSheet(
            f"QLineEdit {{ background-color: {INPUT_BG}; color: {TEXT}; border: 2px solid {INPUT_BORDER}; "
            f"border-radius: {S(6)}px; padding: 0 {S(8)}px; font-size: {S(15)}px; }}")
        self.search.textChanged.connect(lambda _=None: self.refresh())
        f.addWidget(self.search, 1)
        layout.addLayout(f)

        self.scroll = ScrollContainer(left=10, right=14)
        self.scroll.vbox.setSpacing(S(9))
        layout.addWidget(self.scroll, 1)
        self.refresh()

    def _sync_units(self):
        names = ["All Units"] + [u["name"] for u in self.store.units] + ["General"]
        current = [self.unit_cb.itemText(i) for i in range(self.unit_cb.count())]
        if names != current:
            sel = self.unit_cb.currentText()
            self.unit_cb.blockSignals(True)
            self.unit_cb.clear()
            self.unit_cb.addItems(names)
            if sel in names: self.unit_cb.setCurrentText(sel)
            self.unit_cb.blockSignals(False)

    def refresh(self):
        self._sync_units()
        self.scroll.begin_rebuild()
        search_text = self.search.text().strip().lower()
        unit_sel, type_sel, status_sel = self.unit_cb.currentText(), self.type_cb.currentText(), self.status_cb.currentText()
        now = datetime.datetime.now()

        tasks = list(self.store.tasks)
        if unit_sel != "All Units":
            tasks = [t for t in tasks if self.store.unit_name(t.get("unit_id")) == unit_sel]
        if type_sel != "All Types":
            t_key = next((k for k, v in TYPE_LABELS.items() if v == type_sel), None)
            tasks = [t for t in tasks if t.get("type") == t_key]
        if status_sel == "Open":
            tasks = [t for t in tasks if not t.get("done")]
        elif status_sel == "Done":
            tasks = [t for t in tasks if t.get("done")]
        elif status_sel == "Overdue":
            tasks = [t for t in tasks if not t.get("done") and parse_due(t.get("due")) and parse_due(t.get("due")) < now]
        if search_text:
            tasks = [t for t in tasks if search_text in t.get("title", "").lower()]

        tasks.sort(key=lambda t: (bool(t.get("done")), parse_due(t.get("due")) or datetime.datetime.max))
        if not tasks:
            self.scroll.vbox.addWidget(make_label("No tasks match your filters.", 14, MUTED))
        for t in tasks:
            self.scroll.vbox.addWidget(TaskCard(t, self.store, self.app))
        self.scroll.end_rebuild()


class TimetablePage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app, self.store = app, app.store
        self.current_day = datetime.date.today().weekday()
        layout = page_layout(self, left=21, top=30, right=10, bottom=0)
        self.scroll = ScrollContainer(left=16, right=14)
        layout.addWidget(self.scroll)
        self.refresh()

    def select_day(self, d):
        self.current_day = d
        QTimer.singleShot(0, self.refresh)

    def refresh(self):
        s = self.scroll
        s.begin_rebuild()
        v = s.vbox
        app, store = self.app, self.store
        today = datetime.date.today().weekday()

        # Header
        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(S(4))
        titles.addWidget(make_label("Lesson Timetable", 30, TEXT, True))
        titles.addWidget(make_label("Your weekly class schedule, with revision suggestions", 14, MUTED))
        head.addLayout(titles, 1)
        head.addWidget(make_button("Add Lesson", app.accent, w=142, h=34, size=14,
                                   on_click=lambda: LessonDialog(app, store, self.refresh).exec()), 0, Qt.AlignTop)
        v.addLayout(head)

        # Day selector (name + number of lessons)
        days = QHBoxLayout()
        days.setSpacing(S(8))
        for i, name in enumerate(WEEKDAY_SHORT):
            n = len(store.lessons_for_day(i))
            b = QPushButton(f"{name}\n{n}" if n else name)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(S(56))
            sel = i == self.current_day
            bg = app.accent if sel else NAV_ACTIVE
            b.setStyleSheet(
                f"QPushButton {{ background-color: {bg}; color: {'white' if sel else TEXT}; border: none; border-radius: {S(8)}px; "
                f"font-size: {S(14)}px; font-weight: {'bold' if sel else 'normal'}; }} "
                f"QPushButton:hover {{ background-color: {lighter(bg, 112)}; }}")
            b.clicked.connect(lambda checked=False, d=i: self.select_day(d))
            days.addWidget(b, 1)
        v.addLayout(days)
        v.addSpacing(S(4))

        # Lessons header
        lessons = store.lessons_for_day(self.current_day)
        lh = QHBoxLayout()
        suffix = " (today)" if self.current_day == today else ""
        lh.addWidget(make_label(f"Lessons \u2014 {WEEKDAY_NAMES[self.current_day]}{suffix}", 18, TEXT, True))
        lh.addStretch(1)
        lh.addWidget(make_label(f"{len(lessons)} lesson(s)", 13, MUTED))
        v.addLayout(lh)

        if not lessons:
            v.addWidget(make_label("No lessons scheduled for this day.", 14, MUTED))
        for l in lessons:
            v.addWidget(LessonCard(l, store, app))

        # Revision suggestions
        v.addSpacing(S(14))
        rh = QHBoxLayout()
        rh.addWidget(make_label("Revision suggestions", 18, TEXT, True))
        rh.addStretch(1)
        rh.addWidget(make_label("Based on the lessons attended this day", 13, MUTED))
        v.addLayout(rh)

        sugs = store.revision_suggestions(lessons=lessons, limit=4)
        if not sugs:
            v.addWidget(make_label("No suggestions.", 14, MUTED))
        for i, sg in enumerate(sugs):
            col = sg["unit"]["color"]
            card = make_card(BG, 14, border=f"{max(1, S(2))}px solid {col}", name="revCard")
            cl = QHBoxLayout(card)
            cl.setContentsMargins(S(14), S(14), S(18), S(14))
            cl.setSpacing(S(14))

            num = QLabel(str(i + 1))
            num.setAlignment(Qt.AlignCenter)
            num.setFixedSize(S(48), S(48))
            num.setStyleSheet(f"background-color: {col}; color: white; font-size: {S(18)}px; font-weight: bold; border-radius: {S(24)}px; border: none;")
            cl.addWidget(num, 0, Qt.AlignVCenter)

            info = QVBoxLayout()
            info.setSpacing(S(4))
            info.addWidget(make_label(f"Revise: {sg['unit']['name']}", 16, col, True))
            info.addWidget(make_label(sg["reason"], 13, "#9a9a9a", wrap=True))
            cl.addLayout(info, 1)

            cl.addWidget(make_button("Plan revision", col, w=130, h=36, size=12,
                                     on_click=lambda u=sg["unit"]: TaskDialog(app, store, self.refresh, preset_unit=u["id"], preset_type="study").exec()),
                         0, Qt.AlignVCenter)
            v.addWidget(card)

        s.end_rebuild()


class UnitsPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app, self.store = app, app.store
        layout = page_layout(self, left=21, top=20, right=10, bottom=8)

        h = QHBoxLayout()
        h.addWidget(make_label("Course Units", 30, TEXT, True))
        h.addStretch(1)
        h.addWidget(make_button("Add Unit", app.accent, w=142, h=32, size=14,
                                on_click=lambda: UnitDialog(app, self.store, self.refresh).exec()), 0, Qt.AlignTop)
        layout.addLayout(h)

        self.scroll = ScrollContainer(left=10, right=14)
        layout.addWidget(self.scroll, 1)
        self.refresh()

    def refresh(self):
        self.scroll.begin_rebuild()
        for u in self.store.units:
            stats = self.store.unit_stats(u["id"])
            card = make_card(CARD, 12, name="unitCard")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(S(16), S(14), S(16), S(14))
            cl.setSpacing(S(8))

            row = QHBoxLayout()
            row.setSpacing(S(10))
            dot = QFrame()
            dot.setObjectName("unitDot")
            dot.setFixedSize(S(14), S(14))
            dot.setStyleSheet(f"QFrame#unitDot {{ background-color: {u['color']}; border-radius: {S(7)}px; }}")
            row.addWidget(dot, 0, Qt.AlignVCenter)
            row.addWidget(make_label(u["name"], 16, TEXT, True))
            if u.get("code"):
                row.addWidget(make_label(u["code"], 13, MUTED))
            row.addStretch(1)
            row.addWidget(make_button("Add Task", self.app.accent, w=84, h=30,
                                      on_click=lambda uid=u["id"]: TaskDialog(self.app, self.store, self.refresh, preset_unit=uid).exec()))
            row.addWidget(make_button("Edit", GRAY_BTN, w=68, h=30,
                                      on_click=lambda unit=u: UnitDialog(self.app, self.store, self.refresh, unit=unit).exec()))
            row.addWidget(make_button("Delete", RED, w=68, h=30, on_click=lambda uid=u["id"]: self.delete_unit(uid)))
            cl.addLayout(row)

            prog_row = QHBoxLayout()
            prog_row.addWidget(make_label(f"{stats['done']} of {stats['total']} tasks complete", 12, "#9a9a9a"))
            prog_row.addStretch(1)
            prog_row.addWidget(make_label(f"{stats['percent']:.0f}%", 12, "#9a9a9a"))
            cl.addLayout(prog_row)

            prog = QProgressBar()
            prog.setValue(int(stats["percent"]))
            prog.setTextVisible(False)
            prog.setFixedHeight(S(8))
            prog.setStyleSheet(
                f"QProgressBar {{ border: none; background: {TRACK}; border-radius: {S(4)}px; }} "
                f"QProgressBar::chunk {{ background: {u['color']}; border-radius: {S(4)}px; }}")
            cl.addWidget(prog)
            self.scroll.vbox.addWidget(card)
        if not self.store.units:
            self.scroll.vbox.addWidget(make_label("No units yet. Add your first course unit.", 14, MUTED))
        self.scroll.end_rebuild()

    def delete_unit(self, uid):
        reply = QMessageBox.question(self, "Delete", "Remove this unit? Tasks will be moved to General.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.store.remove_unit(uid, delete_tasks=False)
            self.refresh()


class ProgressPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app, self.store = app, app.store
        layout = page_layout(self, left=21, top=20, right=10, bottom=8)
        layout.addWidget(make_label("Progress Tracker", 30, TEXT, True))
        self.scroll = ScrollContainer(left=10, right=14)
        layout.addWidget(self.scroll, 1)
        self.refresh()

    def _bar(self, color):
        pb = QProgressBar()
        pb.setTextVisible(False)
        pb.setFixedHeight(S(8))
        pb.setStyleSheet(
            f"QProgressBar {{ border: none; background: {TRACK}; border-radius: {S(4)}px; }} "
            f"QProgressBar::chunk {{ background: {color}; border-radius: {S(4)}px; }}")
        return pb

    def refresh(self):
        s = self.scroll
        s.begin_rebuild()
        stats = self.store.overall_stats()

        c1 = make_card(CARD, 12, name="overallCard")
        l1 = QVBoxLayout(c1)
        l1.setContentsMargins(S(16), S(14), S(16), S(14))
        l1.setSpacing(S(8))
        top = QHBoxLayout()
        top.addWidget(make_label("Overall completion", 15, TEXT, True))
        top.addStretch(1)
        top.addWidget(make_label(f"{stats['percent']:.1f}%", 13, "#9a9a9a"))
        l1.addLayout(top)
        pb = self._bar(self.app.accent)
        pb.setValue(int(stats["percent"]))
        l1.addWidget(pb)
        s.vbox.addWidget(c1)

        s.vbox.addSpacing(S(6))
        s.vbox.addWidget(make_label("By task type", 18, TEXT, True))
        for typ in TASK_TYPES:
            ts = [t for t in self.store.tasks if t.get("type") == typ]
            done = sum(1 for t in ts if t.get("done"))
            pct = (done / len(ts) * 100) if ts else 0
            c = make_card(CARD, 12, name="typeCard")
            l = QVBoxLayout(c)
            l.setContentsMargins(S(16), S(14), S(16), S(14))
            l.setSpacing(S(8))
            r = QHBoxLayout()
            r.addWidget(make_label(TYPE_LABELS[typ], 15, TYPE_COLORS[typ], True))
            r.addStretch(1)
            r.addWidget(make_label(f"{done}/{len(ts)} ({pct:.0f}%)", 13, "#9a9a9a"))
            l.addLayout(r)
            pb = self._bar(TYPE_COLORS[typ])
            pb.setValue(int(pct))
            l.addWidget(pb)
            s.vbox.addWidget(c)
        s.end_rebuild()


class TipsPage(QWidget):
    RANDOM = "Random Tip"

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.current = "Focus"
        self.pills = {}
        layout = page_layout(self, left=21, top=20, right=10, bottom=8)

        # Category pill bar
        panel = make_card(CARD, 14, name="tipsPanel")
        pv = QVBoxLayout(panel)
        pv.setContentsMargins(S(16), S(16), S(16), S(8))
        pill_scroll = QScrollArea()
        pill_scroll.setFrameShape(QFrame.NoFrame)
        pill_scroll.setWidgetResizable(True)
        pill_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        pill_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        pill_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } " + scrollbar_css("#7a7a7a", HOVER))
        pill_scroll.viewport().setAutoFillBackground(False)
        pill_scroll.setFixedHeight(S(42 + 10 + 22))
        pill_host = QWidget()
        pill_host.setObjectName("pillHost")
        pill_host.setStyleSheet("QWidget#pillHost { background: transparent; }")
        ph = QHBoxLayout(pill_host)
        ph.setContentsMargins(0, 0, 0, S(12))
        ph.setSpacing(S(10))
        for cat in TIPS:
            b = QPushButton(cat)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedSize(S(166), S(42))
            b.clicked.connect(lambda checked=False, c=cat: self.show_category(c))
            self.pills[cat] = b
            ph.addWidget(b)
        rnd = QPushButton(self.RANDOM)
        rnd.setCursor(Qt.PointingHandCursor)
        rnd.setFixedSize(S(166), S(42))
        rnd.setStyleSheet(
            f"QPushButton {{ background-color: {app.accent}; color: white; border: none; border-radius: {S(21)}px; font-size: {S(15)}px; }} "
            f"QPushButton:hover {{ background-color: {lighter(app.accent)}; }}")
        rnd.clicked.connect(lambda: self.show_random())
        ph.addWidget(rnd)
        ph.addStretch(1)
        pill_scroll.setWidget(pill_host)
        pv.addWidget(pill_scroll)
        layout.addWidget(panel)

        self.heading = QLabel()
        self.heading.setContentsMargins(S(16), S(6), 0, 0)
        layout.addWidget(self.heading)

        self.scroll = ScrollContainer(left=16, right=14)
        self.scroll.vbox.setSpacing(S(16))
        layout.addWidget(self.scroll, 1)
        self.show_category(self.current)

    def _style_pills(self):
        for cat, b in self.pills.items():
            col = TIPS[cat]["color"]
            sel = cat == self.current
            bg = col if sel else "transparent"
            hover = lighter(col, 112) if sel else HOVER
            b.setStyleSheet(
                f"QPushButton {{ background-color: {bg}; color: {'white' if sel else TEXT}; border: 2px solid {col}; "
                f"border-radius: {S(21)}px; font-size: {S(15)}px; font-weight: {'bold' if sel else 'normal'}; }} "
                f"QPushButton:hover {{ background-color: {hover}; }}")

    def _set_heading(self, text, color):
        self.heading.setText(text)
        self.heading.setStyleSheet(f"color: {color}; font-size: {S(26)}px; font-weight: bold; background: transparent;")

    def _tip_card(self, number, text, color):
        card = make_card(color, 20, name="tipItem")
        card.setMinimumHeight(S(70))
        cl = QHBoxLayout(card)
        cl.setContentsMargins(S(16), S(10), S(20), S(10))
        cl.setSpacing(S(16))
        num = QLabel(str(number))
        num.setAlignment(Qt.AlignCenter)
        num.setFixedSize(S(48), S(48))
        num.setStyleSheet(f"background-color: white; color: {color}; font-size: {S(17)}px; font-weight: bold; border-radius: {S(24)}px; border: none;")
        cl.addWidget(num, 0, Qt.AlignVCenter)
        cl.addWidget(make_label(text, 16, "#ffffff", wrap=True), 1, Qt.AlignVCenter)
        return card

    def show_category(self, cat):
        if cat not in TIPS: cat = "Focus"
        self.current = cat
        self._style_pills()
        color = TIPS[cat]["color"]
        self._set_heading(cat, color)
        self.scroll.begin_rebuild()
        for i, tip in enumerate(TIPS[cat]["tips"], 1):
            self.scroll.vbox.addWidget(self._tip_card(i, tip, color))
        self.scroll.end_rebuild()

    def show_random(self):
        cat = random.choice(list(TIPS.keys()))
        tip = random.choice(TIPS[cat]["tips"])
        self.current = None
        self._style_pills()
        color = TIPS[cat]["color"]
        self._set_heading(f"Random Tip \u00b7 {cat}", color)
        self.scroll.begin_rebuild()
        self.scroll.vbox.addWidget(self._tip_card(1, tip, color))
        self.scroll.end_rebuild()

    def refresh(self):
        pass  # content is static; selection is kept as-is


class NoWheelCombo(QComboBox):
    """Combo box that ignores the mouse wheel, so scrolling the page never changes a setting."""
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event):
        event.ignore()


class ToggleSwitch(QCheckBox):
    """Pill-shaped on/off switch with its label drawn to the right."""
    def __init__(self, text="", checked=False):
        super().__init__(text)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(S(32))
        f = self.font()
        f.setPixelSize(S(16))
        self.setFont(f)

    def sizeHint(self):
        return QSize(S(40) + S(10) + self.fontMetrics().horizontalAdvance(self.text()) + S(4), S(32))

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        tw, th = S(40), S(20)
        y = (self.height() - th) // 2
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(SWITCH_BLUE if self.isChecked() else SWITCH_OFF))
        p.drawRoundedRect(0, y, tw, th, th / 2, th / 2)
        pad = max(2, S(3))
        d = th - 2 * pad
        x = tw - d - pad if self.isChecked() else pad
        p.setBrush(QColor(KNOB))
        p.drawEllipse(x, y + pad, d, d)
        p.setPen(QColor(TEXT))
        p.setFont(self.font())
        p.drawText(QRect(tw + S(10), 0, self.width() - tw - S(10), self.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, self.text())


class SettingsPage(QWidget):
    REMINDER_COUNTS = [str(n) for n in range(1, 11)]
    LESSON_MINUTES = ["5", "10", "15", "20", "30", "45", "60"]

    def __init__(self, app):
        super().__init__()
        self.app, self.settings = app, app.settings
        layout = page_layout(self, left=21, top=30, right=10, bottom=0)
        self.scroll = ScrollContainer(left=16, right=14)
        self.scroll.no_gesture = True   # drag-to-scroll would fight with text fields and dropdowns
        layout.addWidget(self.scroll)
        self._build()

    # ---- small builders ---------------------------------------------------
    def _set(self, key, value):
        self.settings.set(key, value)
        self.settings.save()

    def _new_card(self, name):
        card = make_card(CARD, 12, name=name)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(S(16), S(14), S(16), S(14))
        lay.setSpacing(S(10))
        return card, lay

    def _row(self, text, control, expand=False, hint=None, hint_width=500):
        box = QWidget()
        outer = QVBoxLayout(box)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(S(2))
        top = QHBoxLayout()
        top.setSpacing(S(16))
        lbl = make_label(text, 16, TEXT)
        if expand:
            lbl.setMinimumWidth(S(96))
        top.addWidget(lbl)
        if expand:
            top.addWidget(control, 1)
        else:
            top.addStretch(1)
            top.addWidget(control)
        top_w = QWidget()
        top_w.setLayout(top)
        top_w.setMinimumHeight(S(32))
        top.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(top_w)
        if hint:
            h = make_label(hint, 12, MUTED, wrap=True)
            h.setFixedSize(S(hint_width), S(32))
            h.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            outer.addWidget(h)
        return box

    def _edit(self, text, width=None):
        e = QLineEdit(text)
        e.setFixedHeight(S(32))
        if width:
            e.setFixedWidth(S(width))
        e.setStyleSheet(
            f"QLineEdit {{ background-color: {INPUT_BG}; color: {TEXT}; border: 2px solid {INPUT_BORDER}; "
            f"border-radius: {S(6)}px; padding: 0 {S(8)}px; font-size: {S(15)}px; }} "
            f"QLineEdit:focus {{ border-color: {self.app.accent}; }}")
        return e

    def _combo(self, items, current, width):
        cb = NoWheelCombo()
        cb.addItems(items)
        if str(current) not in items:
            cb.addItem(str(current))
        cb.setCurrentText(str(current))
        cb.setFixedSize(S(width), S(32))
        cb.setCursor(Qt.PointingHandCursor)
        style_combo(cb, SWITCH_BLUE, SWITCH_BLUE_DARK)
        return cb

    def _toggle(self, key, text, default=True):
        t = ToggleSwitch(text, bool(self.settings.get(key, default)))
        t.toggled.connect(lambda on, k=key: self._set(k, bool(on)))
        return t

    # ---- page -------------------------------------------------------------
    def _build(self):
        v, st = self.scroll.vbox, self.settings
        v.addWidget(make_label("Settings", 30, TEXT, True))
        v.addSpacing(S(16))

        # Profile
        v.addWidget(make_label("Profile", 18, TEXT, True))
        card, cl = self._new_card("profileCard")
        name = self._edit(st.get("username", ""))
        name.textChanged.connect(lambda t: self._set("username", t.strip()))
        cl.addWidget(self._row("Your name", name, expand=True))
        v.addWidget(card)
        v.addSpacing(S(12))

        # Appearance
        v.addWidget(make_label("Appearance", 18, TEXT, True))
        card, cl = self._new_card("appearanceCard")
        theme = self._combo(["Dark", "Light"], st.get("appearance_mode", "Dark"), 166)
        theme.currentTextChanged.connect(self._on_theme)
        cl.addWidget(self._row("Theme", theme))

        current_accent = next((k for k, c in ACCENT_OPTIONS.items()
                               if c.lower() == str(self.app.accent).lower()), "Teal")
        accent = self._combo(list(ACCENT_OPTIONS.keys()), current_accent, 166)
        accent.currentTextChanged.connect(self._on_accent)
        cl.addWidget(self._row("Accent colour", accent))
        size_hint = make_label("Text size is adjustable at the bottom of the sidebar.", 12, MUTED)
        size_hint.setFixedHeight(S(32))
        size_hint.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        cl.addWidget(size_hint)

        try: goal = float(st.get("daily_goal_hours", 3) or 3)
        except (TypeError, ValueError): goal = 3.0
        self.goal_inp = self._edit(f"{goal:.1f}", 94)
        self.goal_inp.editingFinished.connect(self._on_goal)
        cl.addWidget(self._row("Daily study goal (hours)", self.goal_inp))
        v.addWidget(card)
        v.addSpacing(S(12))

        # Content
        v.addWidget(make_label("Content", 18, TEXT, True))
        card, cl = self._new_card("contentCard")
        cl.addWidget(self._toggle("show_daily_tip", "Show tip of the day on dashboard"))
        v.addWidget(card)
        v.addSpacing(S(12))

        # Notifications
        v.addWidget(make_label("Notifications", 18, TEXT, True))
        card, cl = self._new_card("notifyCard")
        cl.addWidget(self._toggle("notify_deadlines", "Remind me about upcoming deadlines"))
        cl.addWidget(self._toggle("notify_tests", "Remind me about upcoming tests"))

        per_day = self._combo(self.REMINDER_COUNTS, int(st.get("notify_per_day", 2) or 2), 94)
        per_day.currentTextChanged.connect(lambda t: self._set("notify_per_day", int(t)))
        cl.addWidget(self._row(
            "Reminders per day (tests and deadlines)", per_day,
            hint="Reminders begin 7 days before the due time and are spread across the day while the app is open."))

        cl.addWidget(self._toggle("notify_session_start", "Notify when a study session starts"))
        cl.addWidget(self._toggle("notify_lessons", "Remind me before a lesson starts"))

        mins = self._combo(self.LESSON_MINUTES, int(st.get("lesson_reminder_minutes", 10) or 10), 94)
        mins.currentTextChanged.connect(lambda t: self._set("lesson_reminder_minutes", int(t)))
        cl.addWidget(self._row("Minutes before lesson to remind me", mins))

        cl.addWidget(self._toggle("break_reminders", "Remind me to take a break every 25 minutes of focus"))
        v.addWidget(card)
        self.scroll.end_rebuild()

    # ---- handlers ---------------------------------------------------------
    def _on_theme(self, mode):
        self._set("appearance_mode", mode)
        self.app.set_theme_mode()
        self.app.request_rebuild("Settings")

    def _on_accent(self, name):
        color = ACCENT_OPTIONS.get(name)
        if not color: return
        self._set("accent_color", color)
        self.app.accent = color
        set_accent(color)
        apply_palette(QApplication.instance())
        self.app.request_rebuild("Settings")

    def _on_goal(self):
        try:
            value = round(min(24.0, max(0.5, float(self.goal_inp.text().replace(",", ".")))), 1)
        except ValueError:
            value = float(self.settings.get("daily_goal_hours", 3) or 3)
        self.goal_inp.setText(f"{value:.1f}")
        self._set("daily_goal_hours", value)

    def refresh(self):
        pass


# ============================================================
#  Main Window
# ============================================================
class StudyPlannerApp(QMainWindow):
    NAV_ORDER = ["Dashboard", "Course Units", "Timetable", "Planner", "Progress", "Study Tips", "Settings"]

    def __init__(self):
        super().__init__()
        self.store = DataStore()
        self.settings = SettingsManager()
        self.accent = self.settings.get("accent_color", "#14b8a6")
        UI_SCALE[0] = self._parse_scale(self.settings.get("ui_scale", "80%"))
        set_accent(self.accent)
        self.set_theme_mode()

        self.setWindowTitle("Study Planner")
        self.resize(1280, 800)

        # Session state
        self._session = None
        self._session_accumulated = 0
        self._session_start = None
        self._focus_since_break = 0
        self._last_activity = datetime.datetime.now()
        self._tick_count = 0
        self.current_page = "Dashboard"
        self._fired = set()   # reminders already shown (kept in memory only)
        self.tray = None
        self._init_tray()

        self.build_ui("Dashboard")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

        self.notify_timer = QTimer(self)
        self.notify_timer.timeout.connect(self._check_notifications)
        self.notify_timer.start(60000)
        QTimer.singleShot(4000, self._check_notifications)

    def set_theme_mode(self):
        set_theme(self.settings.get("appearance_mode", "Dark"))
        apply_palette(QApplication.instance())

    @staticmethod
    def _parse_scale(text):
        try:
            return min(1.4, max(0.6, int(str(text).strip().rstrip("%")) / 100.0))
        except ValueError:
            return 0.8

    # ---- UI construction ---------------------------------------------------
    def apply_theme(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {BG}; }}
            QWidget {{ font-family: '{FONT_MAIN}'; color: {TEXT}; }}
            QLabel {{ background: transparent; }}
            QToolTip {{ background-color: {CARD}; color: {TEXT}; border: 1px solid {BORDER}; }}
            QRadioButton::indicator {{ width: {S(16)}px; height: {S(16)}px; border-radius: {S(9)}px;
                border: 2px solid {INPUT_BORDER}; background: transparent; }}
            QRadioButton::indicator:hover {{ border-color: {ACCENT}; }}
            QRadioButton::indicator:checked {{ border-color: {ACCENT};
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                    stop:0 {ACCENT}, stop:0.5 {ACCENT}, stop:0.6 transparent, stop:1 transparent); }}
            QCheckBox::indicator {{ width: {S(16)}px; height: {S(16)}px; border-radius: {S(4)}px;
                border: 2px solid {INPUT_BORDER}; background: transparent; }}
            QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
            QCheckBox::indicator:checked {{ background-color: {ACCENT}; border-color: {ACCENT}; }}
        """)

    def build_ui(self, page_name="Dashboard"):
        self.apply_theme()
        central = QWidget()
        central.setObjectName("central")
        central.setStyleSheet(f"QWidget#central {{ background-color: {BG}; }}")
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(S(250))
        sidebar.setStyleSheet(f"QFrame#sidebar {{ background-color: {SIDEBAR_BG}; border: none; }}")
        s_lay = QVBoxLayout(sidebar)
        s_lay.setContentsMargins(S(6), S(24), S(4), S(20))
        s_lay.setSpacing(S(10))

        title = make_label("Study Planner", 22, TEXT, True)
        title.setContentsMargins(S(13), 0, 0, S(8))
        s_lay.addWidget(title)

        nav_scroll = ScrollContainer(left=0, right=6)
        nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        nav_scroll.vbox.setSpacing(S(6))
        s_lay.addWidget(nav_scroll, 1)

        self.nav_btns = {}
        self.stack = QStackedWidget()
        self.pages = {
            "Dashboard": DashboardPage(self),
            "Course Units": UnitsPage(self),
            "Timetable": TimetablePage(self),
            "Planner": PlannerPage(self),
            "Progress": ProgressPage(self),
            "Study Tips": TipsPage(self),
            "Settings": SettingsPage(self),
        }
        for name in self.NAV_ORDER:
            page = self.pages[name]
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(S(46))
            btn.setStyleSheet(
                f"QPushButton {{ text-align: left; padding: 0 {S(8)}px; border: none; border-radius: {S(6)}px; "
                f"color: {TEXT_DIM}; font-size: {S(16)}px; background: transparent; }} "
                f"QPushButton:hover {{ background-color: {HOVER}; }} "
                f"QPushButton:checked {{ background-color: {NAV_ACTIVE}; color: {self.accent}; font-weight: bold; }}")
            btn.clicked.connect(lambda checked=False, n=name: self.navigate(n))
            nav_scroll.vbox.addWidget(btn)
            self.nav_btns[name] = btn
            self.stack.addWidget(page)
        nav_scroll.vbox.addStretch(1)

        # Focus strip
        focus = make_card(CARD, 12, name="focusStrip")
        f_lay = QVBoxLayout(focus)
        f_lay.setContentsMargins(S(14), S(14), S(14), S(14))
        f_lay.setSpacing(S(8))
        self.f_title = make_label("FOCUS", 12, "#9a9a9a", True)
        self.f_text = make_label("No active session", 14, TEXT)
        self.f_sub = make_label("Start one from a task", 12, "#7f7f7f")
        self.f_stop = make_button("Stop session", RED, w=110, h=26, size=12, on_click=lambda: self.stop_session())
        f_lay.addWidget(self.f_title)
        f_lay.addWidget(self.f_text)
        f_lay.addWidget(self.f_sub)
        f_lay.addWidget(self.f_stop, 0, Qt.AlignLeft)
        focus_wrap = QHBoxLayout()
        focus_wrap.setContentsMargins(S(6), 0, S(8), 0)
        focus_wrap.addWidget(focus)
        s_lay.addLayout(focus_wrap)

        # Text scale
        scale_row = QHBoxLayout()
        scale_row.setContentsMargins(S(10), 0, S(14), 0)
        scale_row.setSpacing(S(8))
        scale_row.addWidget(make_label("Text", 13, "#8a8a8a"))
        scale_row.addStretch(1)
        scale_row.addWidget(make_button("-", GRAY_BTN, w=34, h=32, size=14, on_click=lambda: self.adjust_scale(-10)))
        pct = make_label(f"{int(round(UI_SCALE[0] * 100))}%", 13, TEXT, align=Qt.AlignCenter)
        pct.setFixedWidth(S(46))
        scale_row.addWidget(pct)
        scale_row.addWidget(make_button("+", GRAY_BTN, w=34, h=32, size=14, on_click=lambda: self.adjust_scale(10)))
        s_lay.addLayout(scale_row)

        layout.addWidget(sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self._update_focus_strip()
        self.enable_smooth_scrolling()
        self.navigate(page_name)

    def request_rebuild(self, page_name=None):
        name = page_name or self.current_page
        QTimer.singleShot(0, lambda: self.build_ui(name))

    def navigate(self, name, tips_category=None):
        if name not in self.pages: return
        self.current_page = name
        self.nav_btns[name].setChecked(True)
        page = self.pages[name]
        self.stack.setCurrentWidget(page)
        if name == "Study Tips" and tips_category:
            page.show_category(tips_category)
        elif hasattr(page, "refresh"):
            page.refresh()

    def adjust_scale(self, delta):
        pct = int(round(UI_SCALE[0] * 100)) + delta
        pct = max(60, min(140, pct))
        UI_SCALE[0] = pct / 100.0
        self.settings.set("ui_scale", f"{pct}%")
        self.settings.save()
        self.request_rebuild()

    def enable_smooth_scrolling(self):
        for scroll in self.findChildren(ScrollContainer):
            if getattr(scroll, "no_gesture", False): continue
            QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
            QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.TouchGesture)

    # ---- Focus sessions ----------------------------------------------------
    def _update_focus_strip(self):
        if self._session:
            self.f_text.setText(self._session.get("title", "Untitled"))
            total = self._session_accumulated
            if self._session_start:
                total += int((datetime.datetime.now() - self._session_start).total_seconds())
            self.f_sub.setText(fmt_duration(total))
            self.f_stop.show()
        else:
            self.f_text.setText("No active session")
            self.f_sub.setText("Start one from a task")
            self.f_stop.hide()

    def start_session(self, task_id):
        task = self.store.get_task(task_id)
        if not task: return
        if self._session:
            self.stop_session(silent=True)

        self._session = task
        self._session_accumulated = 0
        self._session_start = datetime.datetime.now()
        self._focus_since_break = 0
        self._update_focus_strip()
        if self.settings.get("notify_session_start", True):
            Toast(self, "Session started", task.get("title", "Untitled"), self.accent)  # instant feedback, stays in-app

    def stop_session(self, silent=False):
        if not self._session: return
        elapsed = self._session_accumulated
        if self._session_start:
            elapsed += int((datetime.datetime.now() - self._session_start).total_seconds())

        if elapsed > 0:
            self.store.add_session(self._session["id"], self._session.get("unit_id"), elapsed, "")
        self._session = None
        self._session_start = None
        self._session_accumulated = 0
        self._focus_since_break = 0
        self._update_focus_strip()
        if not silent:
            Toast(self, "Session logged", f"{fmt_minutes(elapsed)} recorded.", self.accent)
        self.refresh_page()

    def _tick(self):
        if self._session and self._session_start:
            total = self._session_accumulated + int((datetime.datetime.now() - self._session_start).total_seconds())
            self.f_sub.setText(fmt_duration(total))
            # Break reminder: every 25 minutes of continuous focus
            self._focus_since_break += 1
            if self.settings.get("break_reminders", True) and self._focus_since_break >= 25 * 60:
                self._focus_since_break = 0
                self.notify("Time for a break", "You've focused for 25 minutes. Take a few minutes to rest.")
        self._tick_count += 1
        # Keep "ON NOW" / "done" / countdowns on the dashboard fresh
        if self._tick_count % 60 == 0 and self.current_page == "Dashboard":
            self.refresh_page()

    # ---- Notifications -----------------------------------------------------
    def _init_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(self)
        if self.windowIcon().isNull():
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(self.accent))
            self.tray.setIcon(QIcon(pixmap))
        else:
            self.tray.setIcon(self.windowIcon())
        self.tray.setToolTip("Study Planner")
        self.tray.messageClicked.connect(self._raise_window)
        self.tray.show()

    def _raise_window(self):
        """Clicking a system notification brings the app to the front."""
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def notify(self, title, message):
        """System (tray) notification whenever the OS supports it; in-app popup only as a fallback."""
        if self.tray is not None and self.tray.isVisible() and QSystemTrayIcon.supportsMessages():
            self.tray.showMessage(title, message, QSystemTrayIcon.Information, 6000)
        else:
            Toast(self, title, message, self.accent)

    def _check_notifications(self):
        st = self.settings
        now = datetime.datetime.now()
        today = now.date()

        # Deadlines and tests: begin 7 days before, N reminders spread over 08:00-22:00
        allowed = set()
        if st.get("notify_deadlines", True): allowed.add("deadline")
        if st.get("notify_tests", True): allowed.add("test")
        if allowed:
            try: per_day = max(1, int(st.get("notify_per_day", 2)))
            except (TypeError, ValueError): per_day = 2
            day_start = datetime.datetime.combine(today, datetime.time(8, 0))
            step = datetime.timedelta(hours=14) / per_day
            slot = -1
            for i in range(per_day):
                if day_start + step * i <= now: slot = i
            if slot >= 0:
                for t in self.store.tasks:
                    if t.get("done") or t.get("type") not in allowed: continue
                    due = parse_due(t.get("due"))
                    if not due or due <= now or (due - now) > datetime.timedelta(days=7): continue
                    key = ("task", t["id"], today, slot)
                    if key in self._fired: continue
                    for j in range(slot + 1):
                        self._fired.add(("task", t["id"], today, j))
                    countdown, _ = fmt_countdown(t.get("due"), now)
                    self.notify(f"Upcoming {TYPE_LABELS.get(t.get('type'), 'task')}",
                                f"{t.get('title', 'Untitled')} \u00b7 {countdown}")

        # Lessons: remind N minutes before they start
        if st.get("notify_lessons", True):
            try: minutes = int(st.get("lesson_reminder_minutes", 10))
            except (TypeError, ValueError): minutes = 10
            for l in self.store.lessons_today():
                start = parse_time(l.get("start"))
                if not start: continue
                diff = (datetime.datetime.combine(today, start) - now).total_seconds() / 60.0
                key = ("lesson", l["id"], today)
                if 0 < diff <= minutes and key not in self._fired:
                    self._fired.add(key)
                    unit = self.store.get_unit(l.get("unit_id"))
                    where = f" \u00b7 {l['location']}" if l.get("location") else ""
                    self.notify(f"{l.get('kind', 'Lesson')} starting soon",
                                f"{unit['name'] if unit else 'Lesson'} at {l.get('start')}{where} (in {max(1, round(diff))} min)")

    def refresh_page(self):
        current = self.stack.currentWidget()
        if hasattr(current, "refresh"):
            current.refresh()


def apply_palette(app):
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(BG))
    pal.setColor(QPalette.WindowText, QColor(TEXT))
    pal.setColor(QPalette.Base, QColor(CARD))
    pal.setColor(QPalette.AlternateBase, QColor(BG))
    pal.setColor(QPalette.Text, QColor(TEXT))
    pal.setColor(QPalette.Button, QColor(NAV_ACTIVE))
    pal.setColor(QPalette.ButtonText, QColor(TEXT))
    pal.setColor(QPalette.ToolTipBase, QColor(CARD))
    pal.setColor(QPalette.ToolTipText, QColor(TEXT))
    pal.setColor(QPalette.PlaceholderText, QColor(MUTED))
    pal.setColor(QPalette.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.HighlightedText, QColor("white"))
    app.setPalette(pal)


if __name__ == "__main__":
    # Make Windows show our own icon on the taskbar (not python.exe's)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("StudyPlanner.App.1")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Ensures consistent dark rendering
    app.setFont(QFont(FONT_MAIN, 10))

    icon_file = resource_path("app.ico")
    if os.path.exists(icon_file):
        app.setWindowIcon(QIcon(icon_file))  # window, taskbar and tray icon

    window = StudyPlannerApp()
    window.show()
    sys.exit(app.exec())
