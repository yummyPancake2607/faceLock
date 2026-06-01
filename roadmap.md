# FaceLock - Linux Face Recognition App Lock

## Project Vision

FaceLock is a Linux desktop security application that allows users to lock installed applications and unlock them using facial authentication.

The software should work similarly to Android AppLock.

### Example Workflow

```text
User installs FaceLock

↓

User selects Blender and VS Code

↓

FaceLock locks those apps

↓

User clicks Blender

↓

FaceLock intercepts launch

↓

Webcam opens

↓

Face matches owner?

YES → Blender opens

NO  → Access denied
```

---

# Core Goals

The user should be able to:

1. View all installed applications
2. Select applications to lock
3. Register their face
4. Launch locked applications only after successful authentication
5. Manage locked applications through a GUI
6. Run protection automatically after login

---

# High-Level Architecture

```text
                 +------------------+
                 |      GUI         |
                 +------------------+
                           |
                           |
                           v
                 +------------------+
                 | SQLite Database  |
                 +------------------+
                           |
                           |
          +----------------+----------------+
          |                                 |
          v                                 v

+------------------+           +------------------+
| Face Recognition |           | App Management   |
+------------------+           +------------------+

          |                                 |
          +----------------+----------------+
                           |
                           v
                 +------------------+
                 | Background Daemon|
                 +------------------+
                           |
                           |
                           v
                 +------------------+
                 | Linux Processes  |
                 +------------------+
```

---

# Module 1: Face Recognition System

## Purpose

This module proves the identity of the user.

---

## Face Enrollment

First-time setup process.

User opens:

```text
Settings
 ↓
Register Face
```

The webcam opens and captures:

* Front view
* Left view
* Right view
* Slight upward angle
* Slight downward angle

Approximately:

```text
20-30 images
```

should be collected.

---

## Face Encoding

Raw images should not be stored for authentication.

Images are converted into mathematical face embeddings.

Example:

```python
face_encoding = [
    0.12,
    -0.43,
    0.91,
    ...
]
```

Store the resulting encoding:

```text
~/.facelock/face_encoding.pkl
```

---

## Authentication Flow

Whenever a locked application is opened:

```text
Capture webcam image
        ↓
Generate encoding
        ↓
Compare against stored encoding
```

Results:

```text
Match      → Authenticated
No Match   → Access Denied
```

---

# Module 2: Application Discovery

## Purpose

Automatically discover installed applications.

---

## Linux Desktop Applications

Linux GUI applications are represented by:

```text
.desktop files
```

Common locations:

```text
/usr/share/applications/

/usr/local/share/applications/

~/.local/share/applications/
```

Example:

```ini
Name=Blender
Exec=blender
Icon=blender
```

---

## Application Scanner

The scanner should:

1. Search all application directories
2. Parse .desktop files
3. Extract metadata

Example:

```python
{
    "name": "Blender",
    "exec": "blender",
    "icon": "blender"
}
```

---

## GUI Display

Applications should appear as:

```text
Installed Applications

☐ Blender
☐ Firefox
☐ VS Code
☐ Discord
☐ Steam
```

---

# Module 3: Database Layer

## Purpose

Store all application settings and security data.

---

## Database Choice

Use:

```text
SQLite
```

No external database required.

---

## Tables

### Users

Stores:

* Face encoding path
* User preferences
* Backup PIN

---

### Locked Applications

Stores:

* Application name
* Executable path
* Lock status

Example:

```text
Blender
Locked

VS Code
Locked
```

---

### Access Logs

Stores:

* Timestamp
* Application name
* Authentication result

Example:

```text
2026-05-30
Blender
Denied
```

---

# Module 4: GUI Application

## Technology

Use:

```text
PyQt6
```

---

## Main Window

```text
+--------------------------------+
| FaceLock                       |
+--------------------------------+

Installed Applications

☐ Blender
☐ VS Code
☐ Firefox

[ Lock Selected ]
```

---

## Locked Applications Page

```text
Locked Applications

✓ Blender
✓ VS Code

[ Unlock ]
```

---

## Face Registration Page

```text
Camera Preview

[ Capture Face ]
```

---

## Settings Page

```text
Face Match Threshold

Auto Start

Backup PIN

Intruder Detection
```

---

# Module 5: Application Launch Protection

## Purpose

Prevent locked applications from opening without authentication.

---

## The Problem

Users can launch applications directly:

```bash
blender
```

from a terminal.

This bypasses a simple GUI lock.

---

## Solution

Create a launcher wrapper.

Instead of:

```ini
Exec=blender
```

Use:

```ini
Exec=facelock blender
```

---

## Launch Flow

```text
User clicks Blender

↓

FaceLock launcher starts

↓

Face authentication

↓

Success?

YES → Launch Blender

NO → Exit
```

---

# Module 6: Background Monitoring Daemon

## Purpose

Provide additional protection.

---

## Why It Is Needed

Users may launch:

```bash
blender
```

directly from terminal.

This bypasses launcher protection.

---

## Daemon Behavior

Run continuously:

```python
while True:
    monitor_processes()
```

---

## Process Monitoring

Use:

```text
psutil
```

Monitor:

* Blender
* VS Code
* Firefox
* Any locked application

---

## Enforcement Logic

If a locked application launches:

```python
process.suspend()
```

Display authentication popup.

---

### Authentication Success

```python
process.resume()
```

Application continues.

---

### Authentication Failure

```python
process.kill()
```

Application closes.

---

# Module 7: System Startup Integration

## Purpose

Ensure FaceLock is always active.

---

## systemd User Service

Create:

```text
~/.config/systemd/user/facelock.service
```

Example:

```ini
[Unit]
Description=FaceLock

[Service]
ExecStart=/usr/bin/python daemon.py

[Install]
WantedBy=default.target
```

---

## Result

```text
User logs in

↓

FaceLock automatically starts

↓

Protection becomes active
```

---

# Module 8: Security Features

## Backup PIN

If camera authentication fails:

```text
Enter PIN
```

---

## Intruder Capture

Failed authentication attempt:

```text
Capture webcam image
Store timestamp
Save evidence
```

---

## Desktop Notifications

Display:

```text
Unauthorized access attempt detected
```

---

## Multiple Profiles

Support:

```text
Lakshit
Diya
```

Each user has separate face encodings.

---

# Recommended Project Structure

```text
facelock/

├── app.py
│
├── gui/
│   ├── main_window.py
│   ├── settings.py
│   ├── lock_page.py
│   └── register_face.py
│
├── auth/
│   ├── camera.py
│   ├── recognizer.py
│   └── encoder.py
│
├── database/
│   ├── db.py
│   └── models.py
│
├── daemon/
│   ├── monitor.py
│   └── watchdog.py
│
├── launcher/
│   └── launcher.py
│
├── services/
│   ├── app_scanner.py
│   └── desktop_parser.py
│
├── assets/
│
└── tests/
```

---

# Development Roadmap

## Phase 1

Face Recognition Prototype

Goal:

```text
Open webcam
Detect face
Recognize owner
Print "Authenticated"
```

---

## Phase 2

Application Discovery

Goal:

```text
Scan .desktop files
Display installed applications
```

---

## Phase 3

GUI Development

Goal:

```text
Show application list
Allow lock/unlock actions
```

---

## Phase 4

Database Integration

Goal:

```text
Store locked applications
Store settings
Store logs
```

---

## Phase 5

Launcher Protection

Goal:

```text
Authenticate face
Launch application
```

---

## Phase 6

Background Daemon

Goal:

```text
Monitor running processes
Suspend unauthorized applications
```

---

## Phase 7

systemd Integration

Goal:

```text
Auto-start protection after login
```

---

## Phase 8

Advanced Security Features

Goal:

```text
Backup PIN
Intruder Detection
Notifications
Multi-user Support
```

---

# Biggest Engineering Challenges

The hardest parts of the project are not face recognition.

The most difficult components are:

1. Linux process monitoring
2. Application launch interception
3. Preventing security bypasses
4. systemd integration
5. Safe process management
6. Desktop environment compatibility

Face recognition is only a small part of the complete system.

---

# Final Product

A fully functional Linux desktop application that:

* Detects installed applications
* Allows users to lock applications
* Uses face authentication for access
* Monitors processes in the background
* Starts automatically on login
* Prevents unauthorized application usage
* Provides audit logs and security features

Target Platform:

```text
Arch Linux (Primary)
Linux Desktop Environments
Wayland + X11 Support
```
