import sys
import time
import queue
import tkinter as tk
from tkinter import ttk, filedialog, Button
from threading import Thread
from pathlib import Path
import can
import ctypes




def get_base_assets_path() -> Path:
    """
    Returns the base path for assets:
    - Uses `sys._MEIPASS` when running in a PyInstaller-built executable.
    - Falls back to the script's directory during development (e.g., PyCharm).
    """
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent))


def relative_to_assets5(path: str) -> str:
    """Resolve a file path inside the asset's folder."""
    base_path = get_base_assets_path() / "assetsCANRecording/frame0"
    asset_path = base_path / path
    if not asset_path.exists():
        raise FileNotFoundError(f"Asset file not found: {asset_path}")
    return str(asset_path)



class CANRecorderApp(tk.Frame):
    """
    Application for recording CAN bus messages.
    Provides functionality to connect to a CAN interface, record messages,
    display them in real-time, and save the recorded data to a trace file.
    """

    def __init__(self, parent=None, *args, **kwargs):
        """
        Initialize the CANRecorderApp with parent widget and set up UI components.

        :param parent: The parent widget. If None, a standalone root window will be created.
        :param args: Additional positional arguments for tk.Frame
        :param kwargs: Additional keyword arguments for tk.Frame
        """
        # Standalone support: create our own root if no parent provided
        self._owns_root = False
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        if parent is None:
            parent = tk.Tk()
            self._owns_root = True
            parent.title("CAN Bus Logger")
            parent.geometry("1570x945")
            parent.minsize(1570, 945)
            parent.resizable(False, False)

        super().__init__(parent, *args, **kwargs)
        self.on_hover_3 = None
        self.on_hover_2 = None
        self.on_hover_1 = None
        self.image4 = None
        self.image3 = None
        self.image2 = None
        self.image1 = None
        self.message_count_label = None
        self.message_count = 0
        self.reader = None
        self.notifier = None
        self.bus = None
        self.save_btn = None
        self.stop_btn = None
        self.bitrate_combo = None
        self.start_btn = None
        self.interface_channel_combo = None
        self.parent = parent

        # GUI components
        self.tree = ttk.Treeview(self.parent, columns=("ID", "DLC", "Data", "Cycle Count"), show="headings")

        # Enable CAN configuration
        self.is_recording = False
        self.channel = None  # Default channel
        self.interface = None  # Default CAN interface
        self.bitrate = None  # Default bitrate
        self.msg_dict = {}  # LIVE summary by message ID
        self.msg_list = []  # ALL messages recorded
        self.msg_queue = queue.Queue()  # Queue for UI processing
        self.worker_thread = None
        # Bitrate and Interface map and staus label
        self.interface_channel_map = {
            "Peak CAN": ["pcan", "PCAN_USBBUS1"],
            "Kvaser CAN": ["kvaser", "0"],
            "Chuangxin USBCAN": ["canalystii", "0"],
            "Virtual CAN": ["virtual", "vcan0"]
        }

        self.bitrate_map = {
            "125 kbps": 125000,
            "250 kbps": 250000,
            "500 kbps": 500000,
            "1 Mbps": 1000000,
        }
        self.status_label = tk.Label(
            self.parent,
            text="Status: Ready!",
            bg="white",
            fg="black",
            font=("Arial", 12, "bold"),
            bd=2,  # Add border width
            relief="ridge",  # Add visible border style (ridge, groove, solid, etc.)
            anchor="center",  # Center-align text in the label
            padx=10,  # Add padding (horizontally)
            pady=5  # Add padding (vertically)
        )

        self.status_label.place(relx=0.5, rely=0.95, anchor="center")
        # Load Images for the GUI
        self.load_images()
        # Set up the GUI
        self.setup_ui()


        if self._owns_root:
            self.pack(fill=tk.BOTH, expand=True)
            try:
                self.parent.protocol("WM_DELETE_WINDOW", self.on_close)
            except Exception:
                pass

    def setup_ui(self):
        """Sets up the GUI components."""
        # Title label
        title_label = tk.Label(self.parent, image=self.image4, highlightthickness=0, borderwidth=0)
        title_label.pack(side="top", anchor="nw")

        # Bitrate and Baud Rate dropdowns
        tk.Label(self.parent, text="Select Interface", bg="#F0F0F0").pack(padx=5)
        self.interface_channel_combo = ttk.Combobox(self.parent, state="readonly")
        self.interface_channel_combo.pack(padx=5)
        self.interface_channel_combo.configure(width=10)
        self.interface_channel_combo.bind("<<ComboboxSelected>>", self.update_interface_channel)
        # Populate Interface/Channel combo box
        self.interface_channel_combo['values'] = list(self.interface_channel_map.keys())

        tk.Label(self.parent, text="Select Bitrate", bg="#F0F0F0").pack(padx=5)
        self.bitrate_combo = ttk.Combobox(self.parent, state="readonly")
        self.bitrate_combo.pack(pady=5)
        self.bitrate_combo.bind("<<ComboboxSelected>>", self.update_bitrate)
        self.bitrate_combo.configure(width=10)
        # Populate Bitrate combo box
        self.bitrate_combo['values'] = list(self.bitrate_map.keys())

        # Control buttons
        button_frame = ttk.Frame(self.parent)
        button_frame.pack(pady=10)

        self.start_btn = Button(
            button_frame,
            image=self.image1,  # Default image
            borderwidth=0,
            highlightthickness=0,
            width=142,
            height=68,
            command=self.start_recording
        )
        self.start_btn.grid(row=0, column=0, padx=10)

        # Bind hover events for Start Button
        self.start_btn.bind('<Enter>', lambda event: self.on_hover(self.start_btn, self.on_hover_1))
        self.start_btn.bind('<Leave>', lambda event: self.on_hover(self.start_btn, self.image1))

        self.stop_btn = Button(
            button_frame,
            image=self.image2,  # Default image
            borderwidth=0,
            highlightthickness=0,
            state=tk.DISABLED,  # Initially disabled
            width=142,
            height=68,
            command=self.stop_recording
        )
        self.stop_btn.grid(row=0, column=1, padx=10)

        # Bind hover events for Stop Button
        self.stop_btn.bind('<Enter>', lambda event: self.on_hover(self.stop_btn, self.on_hover_2))
        self.stop_btn.bind('<Leave>', lambda event: self.on_hover(self.stop_btn, self.image2))

        self.save_btn = Button(
            button_frame,
            image=self.image3,  # Default image
            borderwidth=0,
            highlightthickness=0,
            width=142,
            height=68,
            command=self.save_trace,
            state=tk.DISABLED  # Initially disabled
        )
        self.save_btn.grid(row=0, column=2, padx=10)

        # Bind hover events for Save Button
        self.save_btn.bind('<Enter>', lambda event: self.on_hover(self.save_btn, self.on_hover_3))
        self.save_btn.bind('<Leave>', lambda event: self.on_hover(self.save_btn, self.image3))

        # Configure Treeview style
        style = ttk.Style(self.parent)
        style.configure("Custom.Treeview",
                        font=("Arial", 12),  # Increase font size for data payload
                        rowheight=25,  # Adjust row height for better appearance
                        highlightthickness=1,  # Simulate gridlines
                        bd=1)
        style.configure("Custom.Treeview.Heading",
                        font=("Arial", 12, "bold"),  # Bold for headers
                        anchor="center")  # Middle-align headers
        style.map("Custom.Treeview", background=[("selected", "#BFBFFF")])

        # Treeview for CAN messages
        self.tree = ttk.Treeview(self.parent,
                                 columns=("ID", "DLC", "Data", "Cycle Count", "Cycle Time"),  # New column added
                                 show="headings", style="Custom.Treeview")

        # Configure Treeview columns and headings
        self.tree.heading("ID", text="CAN ID", anchor="center")
        self.tree.column("ID", minwidth=80, width=100, anchor="center")

        self.tree.heading("DLC", text="DLC", anchor="center")
        self.tree.column("DLC", minwidth=50, width=80, anchor="center")

        self.tree.heading("Data", text="Data", anchor="center")
        self.tree.column("Data", minwidth=300, width=400, anchor="center")

        self.tree.heading("Cycle Count", text="Cycle Count", anchor="center")
        self.tree.column("Cycle Count", minwidth=100, width=120, anchor="center")

        self.tree.heading("Cycle Time", text="Cycle Time (ms)", anchor="center")  # New column heading
        self.tree.column("Cycle Time", minwidth=100, width=150, anchor="center")  # New column config

        # Scrollbar for the TreeView
        scrollbar = ttk.Scrollbar(self.parent, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.pack(pady=10, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Setup of Message Counter:
        # Add a label to display the total message count
        self.message_count_label = tk.Label(
            self.parent,
            text="Messages: 0",
            bg="#05140E",
            fg="#188D63",
            font=("Arial", 12, "bold"),
            anchor="e"  # Align text to the right
        )
        self.message_count_label.place(relx=0.98, rely=0.01, anchor="ne")  # Top-right corner of the window

    @staticmethod
    def on_hover(button, image):
        """
        Change the button image on hover only if the button is enabled.
        """
        if button['state'] == 'normal':  # Check if the button is enabled
            button.config(image=image)
            button.image = image  # Prevent garbage collection

    def load_images(self):
        """
        Load all image assets required for the GUI.
        Initializes PhotoImage objects for buttons, hover animations, and other UI elements.
        """
        # Default button images
        self.image1 = tk.PhotoImage(file=relative_to_assets5("button_1.png"))
        self.image2 = tk.PhotoImage(file=relative_to_assets5("button_2.png"))
        self.image3 = tk.PhotoImage(file=relative_to_assets5("button_3.png"))
        self.image4 = tk.PhotoImage(file=relative_to_assets5("image_1.png"))

        # Hover images for buttons
        self.on_hover_1 = tk.PhotoImage(file=relative_to_assets5("on_hover1.png"))
        self.on_hover_2 = tk.PhotoImage(file=relative_to_assets5("on_hover2.png"))
        self.on_hover_3 = tk.PhotoImage(file=relative_to_assets5("on_hover3.png"))
    # noinspection PyUnusedLocal
    def update_interface_channel(self, event):
        """
        Update the CAN interface and channel based on the combo box selection.

        :param event: The event that triggered this method
        """
        # Get the new channel and interface values from the dropdown
        selected_channel = self.interface_channel_combo.get()

        # Update the attributes
        self.channel = self.interface_channel_map.get(selected_channel)[1]
        self.interface = self.interface_channel_map.get(selected_channel)[0]



    def update_bitrate(self, event):
        """
        Update the CAN bus bitrate based on the combo box selection.

        :param event: The event that triggered this method
        """
        # Get the new bitrate value from the dropdown
        selected_bitrate = self.bitrate_combo.get()

        # Update the attribute
        self.bitrate = self.bitrate_map.get(selected_bitrate, None)


        self.update_status(
            f"Interface Selected : {self.interface_channel_combo.get()} , Bitrate Selected : {self.bitrate_combo.get()}")

    def update_status(self, message):
        """
        Updates the status label with the current interface, channel, and bitrate values.
        If any value is missing, it reflects 'Not set' in the status message.
        """

        # Update the status label in the GUI
        if self.status_label:
            self.status_label.config(text=message)

    def start_recording(self):
        """Start recording CAN messages."""
        self.is_recording = False  # Ensure the recording state starts as False

        try:
            # Attempt to initialize the CAN bus
            self.bus = can.interface.Bus(interface=self.interface, channel=self.channel, bitrate=self.bitrate)
            self.reader = can.BufferedReader()
            self.notifier = can.Notifier(self.bus, [self.reader])

            # Initialization successful
            self.is_recording = True
            self.start_btn.config(state=tk.DISABLED)  # Disable Start button
            self.stop_btn.config(state=tk.NORMAL)  # Enable Stop button
            self.save_btn.config(state=tk.DISABLED)  # Disable Save button

            # Clear data for new recording session
            self.tree.delete(*self.tree.get_children())  # Clear TreeView content
            self.msg_dict = {}
            self.msg_list = []
            self.msg_queue = queue.Queue()

            # Start background thread for recording messages
            self.worker_thread = Thread(target=self.record_messages, daemon=True)
            self.worker_thread.start()

            # Periodically update TreeView
            self.update_treeview()

            # Update status
            self.update_status("CAN initialization successful. Recording started.")

        except Exception as e:
            # Handle errors during CAN initialization
            self.update_status(f"Error initializing CAN interface: {e}")


            # If initialization fails, ensure notifier or bus resources are stopped
            if hasattr(self, "notifier") and self.notifier:
                self.notifier.stop()
            if hasattr(self, "bus") and self.bus:
                self.bus.shutdown()

    def stop_recording(self):
        """Stops recording CAN messages."""
        if not self.is_recording:

            return

        # Stop recording by setting the flag
        self.is_recording = False

        try:
            # Stop the notifier and clean up the CAN bus
            if hasattr(self, "notifier") and self.notifier:
                self.notifier.stop()

            if hasattr(self, "bus") and self.bus:
                self.bus.shutdown()

        except Exception as e:

            self.update_status(f"Error while stopping CAN resources: {e}")

        # Reset UI state
        self.start_btn.config(state=tk.NORMAL)  # Re-enable Start button
        self.stop_btn.config(state=tk.DISABLED)  # Disable Stop button
        self.save_btn.config(state=tk.NORMAL)  # Enable Save button
        self.message_count = 0

        # Update status to notify the user
        self.update_status("Recording stopped.")


    def record_messages(self):
        """Reads CAN messages into the message queue and the full log."""
        if not self.is_recording:
            return  # Exit immediately if recording is not active

        try:
            # Use the CAN bus initialized in start_recording
            with self.bus:
                while self.is_recording:
                    try:
                        # Poll messages (timeout=0.1s)
                        msg = self.reader.get_message(0.1)
                        if msg:
                            timestamp = time.time()
                            can_id = format(msg.arbitration_id, 'X')  # CAN ID in hex

                            # Format data payload with spaces between bytes
                            data = ' '.join(f"{byte:02X}" for byte in msg.data)
                            dlc = msg.dlc

                            # Append to full message log
                            self.msg_list.append({
                                "timestamp": timestamp,
                                "id": can_id,
                                "dlc": dlc,
                                "data": data,
                            })

                            # Add to the live processing queue (include timestamp for accurate cycle time)
                            self.msg_queue.put({
                                "id": can_id,
                                "dlc": dlc,
                                "data": data,
                                "timestamp": timestamp,
                            })

                            # Update the message counter
                            self.message_count += 1
                            self.update_message_count_label()

                    except can.CanError as e:

                        self.update_status(f"CAN bus error: {e}")
                        break
        except Exception as e:

            self.update_status(f"Recording stopped due to error: {e}")
        finally:
            # Ensure notifier stops when the thread ends
            if hasattr(self, "notifier"):
                self.notifier.stop()

    def update_message_count_label(self):
        """Updates the message count label in the top-right corner."""
        self.message_count_label.config(text=f"Messages: {self.message_count}")

    def save_trace(self):
        """Saves the trace of all observed CAN messages with timestamps."""
        file_path = filedialog.asksaveasfilename(defaultextension=".trc",
                                                 filetypes=[("TRC Files", "*.trc"), ("All Files", "*.*")])
        if file_path:
            try:
                if not self.msg_list:

                    self.update_status("No messages to save!")
                    return

                # Calculate the start time and format it for headers
                start_time = self.msg_list[0]["timestamp"]
                start_time_str = time.strftime("%d-%m-%Y %H:%M:%S", time.localtime(start_time))
                start_time_decimal = start_time / (24 * 60 * 60)  # Convert to fractional days since epoch

                with open(file_path, "w") as f:
                    # Write the headers
                    f.write(f";$FILEVERSION=1.1\n")
                    f.write(f";$STARTTIME={start_time_decimal}\n")
                    f.write(";\n")
                    f.write(f";   Start time: {start_time_str}.{str(start_time % 1)[2:5]} 0\n")
                    f.write(f";   Generated by KG-UDS v1.1\n")
                    f.write(";\n")
                    f.write(";   Message Number\n")
                    f.write(";   |         Time Offset (ms)\n")
                    f.write(";   |         |        Type\n")
                    f.write(";   |         |        |        ID (hex)\n")
                    f.write(";   |         |        |        |     Data Length\n")
                    f.write(";   |         |        |        |     |   Data Bytes (hex) ...\n")
                    f.write(";   |         |        |        |     |   |\n")
                    f.write(";---+--   ----+----  --+--  ----+---  +  -+ -- -- -- -- -- -- --\n")

                    # Write each message in the specified format
                    for idx, msg in enumerate(self.msg_list, start=1):
                        time_offset = (msg["timestamp"] - start_time) * 1000  # Convert seconds to ms
                        message_number = f"{idx})"
                        message_type = "Rx"
                        data_bytes = msg["data"].split()  # Assuming 'data' is written as hex-spaced bytes
                        formatted_data = " ".join(data_bytes)  # Reformat if necessary

                        f.write(
                            f"  {message_number:>5}  "  # Right-align message number with 5 spaces
                            f"{time_offset:>10.1f}  "  # Align time offset (ms) with one decimal point
                            f"{message_type:<6} "  # Left-align message type (Tx/Rx) with 6 spaces
                            f"{msg['id']:<10}"  # Left-align ID (hex) with 10 spaces
                            f"{msg['dlc']:<2} "  # Left-align Data Length (DLC) with 2 spaces
                            f"{formatted_data}\n"  # Append formatted data and newline
                        )


                self.update_status(f"Trace saved successfully: {file_path}")

            except Exception as e:

                self.update_status(f"Error saving trace: {e}")

    def update_treeview(self):
        """Updates the TreeView in batches from the message queue, including cycle count and cycle time."""
        if not self.is_recording:
            return  # Stop updates if recording is not active

        batch_size = 50  # Number of messages per update to keep UI responsive

        try:
            for _ in range(min(batch_size, self.msg_queue.qsize())):
                msg = self.msg_queue.get()

                # Extract fields from the message
                can_id = msg["id"]  # Assume CAN ID is already formatted (e.g., hex ID without 0x)
                dlc = msg["dlc"]
                data = msg["data"]  # Assume data is already formatted as space-separated bytes
                msg_timestamp = msg.get("timestamp", time.time())  # Use message's real timestamp if available

                cycle_time = "--"  # Default value for the first appearance of CAN ID

                if can_id in self.msg_dict:
                    # Calculate the accurate cycle time using the message's timestamp
                    last_time = self.msg_dict[can_id]["last_timestamp"]
                    cycle_time = round((msg_timestamp - last_time) * 1000, 1)  # Convert to ms, rounded to 1 decimal

                    # Update the last timestamp for the CAN ID
                    self.msg_dict[can_id]["last_timestamp"] = msg_timestamp
                    # Increment the cycle count for this CAN ID
                    self.msg_dict[can_id]["count"] += 1
                else:
                    # First message for this CAN ID; initialize the dictionary for it
                    self.msg_dict[can_id] = {
                        "dlc": dlc,
                        "data": data,
                        "count": 1,  # First message received
                        "last_timestamp": msg_timestamp,  # Set the first timestamp
                    }

                if "tree_id" in self.msg_dict[can_id]:
                    # Update the existing entry in the TreeView
                    self.tree.item(
                        self.msg_dict[can_id]["tree_id"],
                        values=(
                            can_id,
                            dlc,
                            data,
                            self.msg_dict[can_id]["count"],  # Update the cycle count
                            cycle_time,  # Update the accurate cycle time
                        )
                    )
                else:
                    # Create a new entry in the TreeView
                    tree_id = self.tree.insert(
                        "",
                        tk.END,
                        values=(
                            can_id,
                            dlc,
                            data,
                            1,  # Cycle count starts at 1
                            "--",  # No cycle time for the first message
                        )
                    )
                    self.msg_dict[can_id]["tree_id"] = tree_id

        except Exception as e:
            pass

        # Schedule the next batch update to keep the TreeView responsive
        if self.is_recording:
            self.parent.after(500, self.update_treeview)

    def on_close(self):
        """Gracefully stop recording and close the window if we own it."""
        try:
            if self.is_recording:
                self.stop_recording()
        except Exception:
            pass
        try:
            # Destroy the root we own; if embedded, leave destruction to parent
            if self._owns_root and self.parent:
                self.parent.destroy()
        except Exception:
            pass

if __name__ == "__main__":
    # Standalone launch: no parent passed, the component will create and own its root window
    app = CANRecorderApp()
    app.parent.mainloop()
