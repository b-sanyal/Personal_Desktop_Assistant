# AURA Desktop Assistant

A deployable Python desktop assistant.

## Features
- Time-aware greetings and live clock
- Persistent SQLite reminders
- Background reminder monitor and pop-up alerts
- Battery percentage / charging state
- Open the default browser / internet
- Launch common system-installed apps
- Open common web services
- Web search
- Persistent notes
- System information
- Modern Tkinter GUI

## Install
```bash
python -m pip install -r requirements.txt
python assistant.py
```

Check Tkinter:
```bash
python -m tkinter
```

## Commands
`battery`
`time`
`date`
`open internet`
`open chrome`
`open notepad`
`open calculator`
`open explorer`
`open youtube`
`open gmail`
`search quantum computing`
`remind me to study at 7:30 pm`
`remind me to submit report at 20 Aug 2026 18:00`
`note buy a notebook`
`show notes`
`system info`
`help`

## Windows executable
```bash
python -m pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name AURA assistant.py
```

For a single executable:
```bash
pyinstaller --noconfirm --clean --onefile --windowed --name AURA assistant.py
```

The reminder database is kept in `data/reminders.db`. Reminders are monitored while AURA is running. For reminders after a reboot/application close, configure the built app to start with Windows (Startup/Task Scheduler).
