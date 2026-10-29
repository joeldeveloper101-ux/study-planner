# Study Planner

A desktop study planner for Windows, built with Python and PySide6. Keep your
courses, deadlines, tests and weekly timetable in one place, and get reminders
so nothing slips past you.

## Features

* **Dashboard** with a personalised greeting, daily study goal, and day/hour
countdowns to upcoming tests and deadlines
* **Course Units**: add and remove your subjects, each with its own colour
* **Planner**: add deadlines, tests and study sessions with calendar and clock
pickers, and mark them done
* **Timetable**: weekly view of lectures, tutorials, labs and seminars
* **Progress** tracking across your units and tasks
* **Study Tips** by category, plus an optional tip of the day
* **Reminders** for deadlines, tests, lessons, session starts and 25-minute
break reminders, with the number of reminders per day set by you
* **Settings**: dark/light theme, accent colour, UI scale and notification toggles
* Touchpad and mouse-wheel scrolling throughout

!\[Dashboard Tab In Dark Theme](screenshots/dashboard\_darktheme.png)

!\[Dashboard Tab In Light Theme](screenshots/dashboard\_light\_theme.png)

!\[Planner Tab](screenshots/planner\_tab.png)

!\[Settings Tab](screenshots/settings\_tab.png)

!\[Timetable Tab](screenshots/timetable\_tab.png)



## Download (Windows)

Get the latest installer from the
[Releases page](https://github.com/YOUR-USERNAME/study-planner/releases/latest).

1. Download the `.exe` installer
2. Run it and follow the prompts
3. If Windows SmartScreen shows "Windows protected your PC", click
**More info**, then **Run anyway**. The installer is not code-signed.

## Run from source

Requires Python 3.10 or newer.

```bash
git clone https://github.com/joeldeveloper101-ux/study-planner.git
cd study-planner
pip install -r requirements.txt
python main.py
```

## Build the installer yourself

You need [PyInstaller](https://pyinstaller.org) and
[Inno Setup](https://jrsoftware.org/isinfo.php) installed.

```bash
pip install pyinstaller
build.bat
```

`build.bat` packages the app with PyInstaller (`StudyPlanner.spec`), then
`StudyPlanner.iss` is compiled by Inno Setup into the final installer.

## Project files

|File|Purpose|
|-|-|
|`main.py`|The whole application|
|`app.ico`|Application icon|
|`requirements.txt`|Python dependencies|
|`StudyPlanner.spec`|PyInstaller build configuration|
|`StudyPlanner.iss`|Inno Setup installer script|
|`build.bat`|Build helper script|

## Your data

Everything is stored locally in a `.study\\\\\\\\\\\\\\\_planner` folder in your user
directory. Nothing is sent online.

## License

Released under the [MIT License](LICENSE).

