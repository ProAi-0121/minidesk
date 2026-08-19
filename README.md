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

## Requirements

- Python 3.9+ (built and tested on 3.11)
- `pip install -r requirements.txt`

## Setup

```bash
git clone <repo-url>
cd minidesk
pip install -r requirements.txt
```

## Configuration

Everything is optional — the defaults work out of the box. If a port clashes
with something already running, copy `.env.example` to `.env` and change it:

| Variable          | Default | Purpose                              |
| ----------------- | ------- | ------------------------------------ |
| `APP_PORT`        | `6969`  | Port for the web UI                  |
| `BROADCAST_PORT`  | `7979`  | UDP port used for device discovery   |
| `COMMAND_PORT`    | `9000`  | TCP port the remote command server   |

## Usage

```bash
python minidesk.py
```

A tray icon appears. Open the web UI (http://localhost:6969), wait a moment
for devices to show up, hit **Connect Terminal** and type your command.

> The command server runs whatever you send it as a shell command on the target
> machine. Only run MiniDesk on networks you trust.

## Project Structure

```
minidesk.py            CLI entry point: discovery, command server, web UI, tray
templates/             Flask HTML templates (device list + terminal)
icon.png / icon.ico    Tray / window icon
requirements.txt       Python dependencies
.env.example           Port configuration template
```

## Troubleshooting

- Devices not appearing? Make sure both machines run MiniDesk and are on the
  same subnet. Broadcasts are sent every 10s and a scan runs every 5 minutes,
  so it can take a little while on first start.
- The remote command times out? Commands that take very long can hit the 10s
  socket timeout in `exec_remote` — keep them short.