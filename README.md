# Nexus Gesture Controller

A real-time hand gesture interface for controlling mouse, navigation, and system audio through a webcam. Built with OpenCV, MediaPipe, and Python.

## Overview

Most webcam-based mouse controllers map camera coordinates directly to screen pixels, resulting in shaky movement, jittery clicks, and fatigue. Nexus Gesture Controller takes a different approach:

1. **Relative Air-Mouse Physics**: The cursor moves based on the delta movement of the palm center rather than absolute screen mapping, allowing natural hand movement anywhere in the camera frame.
2. **Adaptive OneEuro Filtering**: High-frequency hand tremors are filtered out during static holds, while high-velocity movements pass through with zero perceived latency.
3. **Intent State Machine**: Distinguishes intentional gestures from transition movements, preventing accidental clicks while moving the hand.
4. **Desktop and Media Integration**: Controls Windows volume proportionally and executes virtual desktop switching shortcuts.
5. **Real-time Status Overlay**: An optional Chrome extension connects over local WebSockets to display an unobtrusive status pill in the browser.

## Gesture Map

| Gesture | Action | Description |
|---|---|---|
| Open Palm or Pointing Index | Move Cursor | Relative movement with dynamic acceleration |
| Pinch Thumb + Index | Left Click | 0.4s debounce cooldown |
| Pinch Thumb + Middle | Right Click | Opens context menu |
| Pinch Thumb + Ring | Double Click | Executes double left-click |
| Closed Fist | Toggle Drag | Locks mouse button down for dragging; fist again to release |
| Peace Sign (Index + Middle Up) | Scroll | Vertical hand position controls scroll direction and speed |
| Pinky Finger Up | Volume Control | Hand height maps directly to system volume (0-100%) |
| Four Fingers + Horizontal Swipe | Switch Desktop | Sends Windows virtual desktop shortcuts (Win + Ctrl + Arrow) |
| Middle Finger Only (Hold 1s) | Sleep / Wake | Pauses all input until held again for 1 second |
| Keyboard 'Q' | Quit | Releases all held buttons and exits cleanly |

## Project Structure

```
Nexus Gesture Controller/
|-- install_dependencies.bat   # Automated dependency setup
|-- run.bat                    # Clean launcher (bytecode suppressed)
|-- README.md                  # Documentation
|-- LICENSE                    # MIT License
|-- .gitignore                 # Build and environment exclusions
|-- backend/
|   |-- config.py              # Central configuration and tuning constants
|   |-- main.py                # Application entry point
|   |-- requirements.txt       # Python package list
|   |-- hand_landmarker.task   # MediaPipe HandLandmarker model file
|   |-- control/
|   |   |-- mouse_physics.py   # Relative cursor physics and dead-zones
|   |   `-- system_control.py  # System volume and virtual desktop hotkeys
|   |-- core/
|   |   `-- system.py          # Main execution loop and camera processing
|   |-- intent/
|   |   `-- classifier.py      # Gesture detection and state classification
|   |-- perception/
|   |   |-- smoothing.py       # OneEuro adaptive low-pass filter
|   |   `-- tracker.py         # MediaPipe Tasks vision wrapper
|   |-- server/
|   |   `-- websocket.py       # Local WebSocket broadcaster (port 8765)
|   `-- ui/
|       `-- hud.py             # OpenCV camera overlay and joint renderer
`-- extension/                 # Chrome browser status overlay extension
    |-- manifest.json          # Extension configuration
    |-- background.js          # Service worker for WebSocket connection
    |-- content.js             # Injected status pill
    |-- popup.html             # Extension toolbar popup
    |-- popup.js               # Popup handler
    `-- icon.png               # Extension icon
```

## Setup and Installation

### Prerequisites
- Windows 10/11
- Python 3.10 to 3.12 (Python 3.12 recommended for MediaPipe wheel support)
- Standard USB or integrated webcam

### 1. Install Dependencies
Double-click `install_dependencies.bat` or run:
```bash
cd backend
pip install -r requirements.txt
```

### 2. Run the Application
Double-click `run.bat` or run:
```bash
cd backend
python -B main.py
```
*(The `-B` flag prevents Python from writing `__pycache__` directories to your folder).*

### 3. Load the Chrome Extension (Optional)
1. Open Google Chrome and go to `chrome://extensions/`
2. Toggle on **Developer mode** in the top-right corner.
3. Click **Load unpacked** and select the `extension` folder.
4. The extension will automatically connect to `ws://localhost:8765` when the backend is running.

## Configuration

All parameters can be tuned in `backend/config.py`:

- `CAMERA_ID`: Default is `0`. Set to `1` or `2` if using an external USB camera.
- `BASE_SENSITIVITY`: Base multiplier for cursor speed (default `3.0`).
- `ACCELERATION_FACTOR`: Non-linear speed gain for fast hand movements (default `20.0`).
- `DEAD_ZONE`: Anti-tremor threshold (default `0.002`). Movement below this is ignored.
- `SHOW_SKELETON`: Set to `True` or `False` to toggle joint line rendering on the camera feed.
- `FAILSAFE_FPS`: Minimum acceptable camera framerate before auto-pausing (default `15`).

## Safety Features

- **Auto-Drop**: If your hand leaves the camera frame while dragging a file or window, the system automatically releases the mouse button to avoid stuck clicks.
- **Low Framerate Guard**: If webcam FPS drops below the safety threshold, the system temporarily halts input to prevent erratic cursor jumps.
- **Clean Shutdown**: Pressing `Q` safely releases all mouse buttons and closes all OpenCV handles.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2026 Naman Pahariya.
