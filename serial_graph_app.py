#!/usr/bin/env python3
"""
Serial Port Data Logger
Reads 96-byte messages from COM3. Each message contains 96 integer values.
Displays all values in a table/list format.
Message boundaries are detected by 5ms pauses between data streams.
Stops automatically after collecting 10 samples.
"""

import serial
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox


class SerialDataLogger:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Data Logger - COM3 (96 Channels)")
        self.root.geometry("1400x600")
        
        # Configuration
        self.PORT = "COM3"
        self.BAUD_RATE = 19200
        self.BYTESIZE = serial.EIGHTBITS      # 8 bits (Arduino default)
        self.PARITY = serial.PARITY_NONE      # No parity (Arduino default)
        self.STOPBITS = serial.STOPBITS_ONE   # 1 stop bit (Arduino default)
        self.EXPECTED_BYTES = 96
        self.PAUSE_THRESHOLD = 0.005  # 5 milliseconds
        self.TARGET_SAMPLES = 10  # Stop after collecting 10 samples
        
        # Data storage - each byte position gets its own list of values
        self.byte_values = [[] for _ in range(self.EXPECTED_BYTES)]
        
        self.current_message = bytearray()
        self.message_count = 0
        self.last_byte_time = None
        self.serial_port = None
        self.running = False
        
        # GUI Setup
        self.setup_gui()
        
    def setup_gui(self):
        """Create the GUI layout"""
        # Control Frame
        control_frame = ttk.Frame(self.root)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        ttk.Label(control_frame, text=f"Port: {self.PORT}", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        ttk.Label(control_frame, text=f"Baud: {self.BAUD_RATE} (8N1 - Arduino Default)", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        ttk.Label(control_frame, text=f"Message Size: {self.EXPECTED_BYTES} bytes", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        ttk.Label(control_frame, text=f"Target Samples: {self.TARGET_SAMPLES}", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(control_frame, text="Status: Disconnected", foreground="red", font=("Arial", 10, "bold"))
        self.status_label.pack(side=tk.LEFT, padx=20)
        
        self.start_btn = ttk.Button(control_frame, text="Start", command=self.start_connection)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="Stop", command=self.stop_connection, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Stats Frame
        stats_frame = ttk.Frame(self.root)
        stats_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        self.stats_label = ttk.Label(stats_frame, text="Samples collected: 0/10", font=("Arial", 10, "bold"))
        self.stats_label.pack(side=tk.LEFT)
        
        # Table Frame
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create treeview with scrollbars
        tree_scroll_y = ttk.Scrollbar(table_frame, orient="vertical")
        tree_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal")
        
        # Create columns (Byte 0, Byte 1, ... Byte 95)
        columns = [f"Byte {i:02d}" for i in range(self.EXPECTED_BYTES)]
        
        self.tree = ttk.Treeview(table_frame, columns=columns, height=15, 
                                yscrollcommand=tree_scroll_y.set, 
                                xscrollcommand=tree_scroll_x.set)
        
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)
        
        # Format columns
        self.tree.column("#0", width=0, stretch=tk.NO)
        
        for i, col in enumerate(columns):
            width = 60 if i < 10 else 55
            self.tree.column(col, anchor=tk.CENTER, width=width)
            self.tree.heading(col, text=col)
        
        # Pack treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky='nsew')
        tree_scroll_y.grid(row=0, column=1, sticky='ns')
        tree_scroll_x.grid(row=1, column=0, sticky='ew')
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
    
    def start_connection(self):
        """Start serial connection and reading thread"""
        try:
            self.serial_port = serial.Serial(
                port=self.PORT,
                baudrate=self.BAUD_RATE,
                bytesize=self.BYTESIZE,
                parity=self.PARITY,
                stopbits=self.STOPBITS,
                timeout=1
            )
            self.running = True
            self.message_count = 0
            self.byte_values = [[] for _ in range(self.EXPECTED_BYTES)]
            
            # Clear table
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            self.status_label.config(text="Status: Connected - Collecting samples...", foreground="green")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            
            # Start reading thread
            self.reader_thread = threading.Thread(target=self.read_serial, daemon=True)
            self.reader_thread.start()
            
        except serial.SerialException as e:
            messagebox.showerror("Connection Error", f"Failed to connect to {self.PORT}:\n{str(e)}")
            self.status_label.config(text="Status: Error", foreground="red")
    
    def stop_connection(self):
        """Stop serial connection"""
        self.running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.status_label.config(text="Status: Disconnected", foreground="red")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
    
    def read_serial(self):
        """Read from serial port in separate thread"""
        while self.running:
            try:
                if self.serial_port.in_waiting > 0:
                    byte = self.serial_port.read(1)
                    current_time = time.time()
                    
                    # Check for message boundary (pause detected)
                    if self.last_byte_time is not None:
                        pause = current_time - self.last_byte_time
                        
                        if pause > self.PAUSE_THRESHOLD and len(self.current_message) > 0:
                            # End of message detected - process it
                            self.process_complete_message()
                            self.current_message = bytearray()
                    
                    self.current_message.extend(byte)
                    self.last_byte_time = current_time
                    
                    # Check if we've reached expected size (96 bytes)
                    if len(self.current_message) >= self.EXPECTED_BYTES:
                        # Message is complete, process it
                        self.process_complete_message()
                        self.current_message = bytearray()
                        self.last_byte_time = None  # Reset to prevent pause detection
                
                time.sleep(0.001)  # Small delay to prevent CPU spinning
                
            except Exception as e:
                print(f"Serial read error: {e}")
                if self.running:
                    self.root.after(100, self.stop_connection)
                break
    
    def process_complete_message(self):
        """Process a complete 96-byte message"""
        message = self.current_message[:self.EXPECTED_BYTES]
        
        # Add each byte value to its corresponding byte position list
        for byte_position in range(len(message)):
            byte_value = message[byte_position]
            self.byte_values[byte_position].append(byte_value)
        
        self.message_count += 1
        
        # Update UI on main thread
        self.root.after(0, lambda: self.update_table_and_check_complete())
    
    def update_table_and_check_complete(self):
        """Update table and check if sampling is complete"""
        self.stats_label.config(text=f"Samples collected: {self.message_count}/{self.TARGET_SAMPLES}")
        
        # Update table with current data
        self.refresh_table()
        
        # Check if we've reached the target number of samples
        if self.message_count >= self.TARGET_SAMPLES:
            self.root.after(500, self.sampling_complete)
    
    def refresh_table(self):
        """Refresh the table with current byte values"""
        # Clear existing rows
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add rows for each sample
        for sample_num in range(self.message_count):
            row_values = []
            for byte_position in range(self.EXPECTED_BYTES):
                if sample_num < len(self.byte_values[byte_position]):
                    value = self.byte_values[byte_position][sample_num]
                    row_values.append(str(value))
                else:
                    row_values.append("")
            
            # Insert row with alternating background colors
            tags = ("oddrow",) if sample_num % 2 == 0 else ("evenrow",)
            self.tree.insert("", "end", values=row_values, tags=tags)
        
        # Configure tag colors
        self.tree.tag_configure("oddrow", background="#f0f0f0")
        self.tree.tag_configure("evenrow", background="white")
    
    def sampling_complete(self):
        """Called when sampling is complete"""
        self.running = False
        self.status_label.config(text="Status: Sampling Complete!", foreground="blue")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        messagebox.showinfo("Complete", f"Successfully collected {self.message_count} samples for all 96 bytes!")


def main():
    root = tk.Tk()
    app = SerialDataLogger(root)
    root.mainloop()


if __name__ == "__main__":
    main()
