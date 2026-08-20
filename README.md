# MiniDesk

A small LAN remote-control tool. Run it on a couple of machines on the same
network and MiniDesk finds them for you, then gives you a web-based terminal
to run commands on any of them — handy for poking at a home server or another
desktop without leaving your seat.

## Features

- Auto-discovers other MiniDesk machines over UDP broadcast + a subnet scan
- Web UI that lists every device it finds on the LAN
- A web terminal for running commands on a remote MiniDesk device
- System tray icon with a quick link to the web UI
- Windows executable build with PyInstaller
- Single-file executable with no console window

## Requirements

### Running from source

- Python 3.9+ (built and tested on Python 3.11)
- Dependencies from `requirements.txt`

### Running the built executable

No Python installation is required on the target machine when using the
PyInstaller executable.

## Setup

```bash
git clone <repo-url>
cd minidesk
pip install -r requirements.txt
```

## Configuration

Everything is optional — the defaults work out of the box. If a port clashes
with something already running, copy `.env.example` to `.env` and change it:

| Variable          | Default | Purpose                            |
| ----------------- | ------- | ---------------------------------- |
| `APP_PORT`        | `6969`  | Port for the web UI                |
| `BROADCAST_PORT`  | `7979`  | UDP port used for device discovery |
| `COMMAND_PORT`    | `9000`  | TCP port for remote commands       |

## Usage

### Run from source

```bash
python minidesk.py
```

A tray icon appears. Open the web UI at
`http://localhost:6969`, wait a moment for devices to show up, hit
**Connect Terminal** and type your command.

### Build the Windows executable

MiniDesk uses PyInstaller to package the application into a standalone
Windows executable.

Install PyInstaller:

```bash
pip install pyinstaller
```

Build a **single-file executable with no console window**:

```bash
pyinstaller --onefile --noconsole --name MiniDesk --icon=icon.ico minidesk.py
```

The executable will be created at:

```text
dist/MiniDesk.exe
```

You can copy `dist/MiniDesk.exe` to another Windows machine and run it
without installing Python or the project dependencies.

> **Note:** `--noconsole` hides the terminal window. If you are debugging
> startup or runtime errors, temporarily remove `--noconsole` so errors are
> visible in the console.

### Build from a clean environment

If you want to rebuild from scratch:

```bash
rmdir /s /q build
rmdir /s /q dist
del MiniDesk.spec
pyinstaller --onefile --noconsole --name MiniDesk --icon=icon.ico minidesk.py
```

If `icon.ico` is not available, omit the `--icon=icon.ico` option.

## Project Structure

```text
minidesk.py            Main application: discovery, command server, web UI, tray
templates/             Flask HTML templates (device list + terminal)
icon.png / icon.ico    Tray / application icon
requirements.txt       Python dependencies
.env.example           Port configuration template
README.md              Project documentation
```

## Troubleshooting

- **Devices not appearing?** Make sure both machines run MiniDesk and are on
  the same subnet. Broadcasts are sent every 10s and a scan runs every
  5 minutes, so it can take a little while on first start.
- **The remote command times out?** Commands that take very long can hit the
  10s socket timeout in `exec_remote` — keep them short.
- **The executable does not start?** Build once without `--noconsole` to see
  any Python/PyInstaller error output.
- **Flask/templates are missing in the executable?** If the application loads
  templates from the `templates/` directory at runtime, PyInstaller may need
  the templates bundled explicitly. Add the required data files with
  `--add-data` or configure them in the generated `.spec` file.
- **Windows Defender or SmartScreen warning?** Unsigned PyInstaller
  executables can trigger reputation warnings on Windows. This does not
  necessarily mean the executable is malicious.

## Security

The command server runs whatever you send it as a shell command on the target
machine. Only run MiniDesk on networks and machines you trust.

MiniDesk is intended for trusted LAN environments and should not be exposed
directly to the public internet without adding proper authentication,
authorization, encryption, and other security controls.
