# CAN-Trace-Recording-Application
This application utilizes, python-CAN and tkinter to offer a GUI solution utilizing multiple VCI. It allows a user to record PCAN style traces of any CAN bus utilizing all of the tools supported by Python-CAN

## Prerequisites

### Supported Hardware and Drivers
To use this application, ensure that the necessary hardware and drivers for your CAN adapter are installed and configured:
1. **Peak CAN (PCAN)**
   - Driver: PCAN-Basic API (Download from [PEAK website](https://www.peak-system.com)).
2. **Kvaser CAN**
   - Driver: Kvaser CANlib Driver (Download from [Kvaser website](https://www.kvaser.com/downloads/)).
3. **Chuangxin USBCAN (Canalyst-II)**
   - Driver: Obtain from the vendor or installation CD.
4. **Virtual CAN (Linux)**
   - Load the `vcan` kernel module and configure with `ip link` commands.
## Features
- **Multi-Interface Support:**
  - Compatible with hardware supported by python-CAN, including:
    - **Peak CAN (PCAN)**: Supports `pcan_basic`.
    - **Kvaser CAN:** Supports `canlib` from Kvaser.
    - **Chuangxin USBCAN (Canalyst-II)**
    - **Virtual CAN adapters** (for testing on Linux via `vcan`).
- **Real-Time Data Visualization:** Dynamically displays CAN message data, including:
  - **CAN ID** in hexadecimal.
  - **DLC (Data Length Code)**.
  - **Data Bytes** in a human-readable format.
  - **Cycle Count** and **Cycle Time (ms)** for recurring messages.
- **Configurable Settings:**
  - Bitrate selection: `125 kbps`, `250 kbps`, `500 kbps`, and `1 Mbps`.
  - Ability to select a CAN adapter and communication channel.
- **Trace Logging to `.TRC`:**
  - Save recorded messages to `.trc` files for offline diagnostics.
  - Includes timestamps and formatted message data.
- **Cross-Platform Design:** Built using Python and Tkinter, works on Windows, macOS, and Linux.
- **Error Handling and Status Updates:** Displays clear error messages during initialization or hardware connection issues.

### Notes:
- Windows users can skip installation if they’re using the executable.
- Linux/macOS users can optionally create a **virtual environment** to avoid conflicts:
  ```bash
  python -m venv venv
  source venv/bin/activate  # On Linux/macOS
  venv\Scripts\activate    # On Windows
  pip install -r requirements.txt
  ```
- If using virtual CAN (`vcan`) on Linux, ensure it is properly configured (see `Notes on Supported Interfaces`).


