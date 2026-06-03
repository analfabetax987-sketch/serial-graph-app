#!/usr/bin/env python3
"""
Serial Port Graphing Application
Reads 96-byte messages from COM3. Each message contains 96 integer values.
Each byte position gets its own line graph that grows with each new message.
Message boundaries are detected by 5ms pauses between data streams.
Stops automatically after collecting 10 samples.
"""

import serial
import threading
import time
from collections import deque
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np


class SerialGraphApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Port Data Grapher - COM3 (96 Channels)")
        self.root.geometry("1400x900")
        
        # Configuration
        self.PORT = "COM3"
        self.BAUD_RATE = 19200
        self.BYTESIZE = serial.EIGHTBITS
        self.PARITY = serial.PARITY_ODD
        self.STOPBITS = serial.STOPBITS_ONE
        self.EXPECTED_BYTES = 96
        self.PAUSE_THRESHOLD = 0.005  # 5 milliseconds - pause longer than this marks end of message
        self.TARGET_SAMPLES = 10  # Stop after collecting 10 samples
        
        # Data storage - each byte position gets its own history list
        # byte_histories[0] = [value_from_msg1, value_from_msg2, value_from_msg3, ...]
        # byte_histories[1] = [value_from_msg1, value_from_msg2, value_from_msg3, ...]
        # etc. for all 96 byte positions
        self.byte_histories = [[] for _ in range(self.EXPECTED_BYTES)]
        
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
        ttk.Label(control_frame, text=f"Baud: {self.BAUD_RATE} (8O1)", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        ttk.Label(control_frame, text=f"Message Size: {self.EXPECTED_BYTES} bytes/values", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        ttk.Label(control_frame, text=f"Target Samples: {self.TARGET_SAMPLES}", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        ttk.Label(control_frame, text=f"Pause Threshold: {self.PAUSE_THRESHOLD*1000:.1f}ms", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(control_frame, text="Status: Disconnected", foreground="red", font=("Arial", 10, "bold"))
        self.status_label.pack(side=tk.LEFT, padx=20)
        
        self.start_btn = ttk.Button(control_frame, text="Start", command=self.start_connection)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="Stop", command=self.stop_connection, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Stats Frame
        stats_frame = ttk.Frame(self.root)
        stats_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        self.stats_label = ttk.Label(stats_frame, text="Messages received: 0/10", font=("Arial", 10, "bold"))
        self.stats_label.pack(side=tk.LEFT)
        
        # Graph Frame with scrollbar
        graph_frame = ttk.Frame(self.root)
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create canvas with scrollbar for scrolling through all 96 graphs
        canvas = tk.Canvas(graph_frame, bg="white")
        scrollbar = ttk.Scrollbar(graph_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create figures for each byte position (96 graphs)
        self.figures = []
        self.canvases = []
        self.axes = []
        
        for i in range(self.EXPECTED_BYTES):
            fig = Figure(figsize=(12, 1.0), dpi=100)
            ax = fig.add_subplot(111)
            ax.set_title(f"Byte Position {i:02d}", fontsize=9, fontweight='bold')
            ax.set_ylabel("Value", fontsize=8)
            ax.set_ylim(0, 255)
            ax.tick_params(labelsize=7)
            
            canvas_widget = FigureCanvasTkAgg(fig, master=scrollable_frame)
            canvas_widget.get_tk_widget().pack(fill=tk.X, padx=2, pady=1)
            
            self.figures.append(fig)
            self.canvases.append(canvas_widget)
            self.axes.append(ax)
    
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
            self.byte_histories = [[] for _ in range(self.EXPECTED_BYTES)]
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
                        self.last_byte_time = None  # Reset to prevent pause detection on next byte
                
                time.sleep(0.001)  # Small delay to prevent CPU spinning
                
            except Exception as e:
                print(f"Serial read error: {e}")
                if self.running:
                    self.root.after(100, self.stop_connection)
                break
    
    def process_complete_message(self):
        """Process a complete 96-byte message"""
        message = self.current_message[:self.EXPECTED_BYTES]
        
        # Add each byte value to its corresponding byte position history
        for byte_position in range(len(message)):
            byte_value = message[byte_position]
            self.byte_histories[byte_position].append(byte_value)
        
        self.message_count += 1
        
        # Update UI on main thread
        self.root.after(0, lambda: self.update_stats_and_check_complete())
    
    def update_stats_and_check_complete(self):
        """Update stats and check if sampling is complete"""
        self.stats_label.config(text=f"Messages received: {self.message_count}/{self.TARGET_SAMPLES}")
        
        # Check if we've reached the target number of samples
        if self.message_count >= self.TARGET_SAMPLES:
            # Render all graphs at once when complete
            self.root.after(100, self.render_all_graphs)
            self.root.after(200, self.sampling_complete)
        else:
            # Render graphs incrementally during sampling
            self.root.after(0, self.render_all_graphs)
    
    def render_all_graphs(self):
        """Render all 96 graphs efficiently"""
        for byte_position in range(self.EXPECTED_BYTES):
            ax = self.axes[byte_position]
            ax.clear()
            
            values = self.byte_histories[byte_position]
            
            if values:  # Only plot if we have data
                message_numbers = list(range(1, len(values) + 1))
                
                # Plot line graph - X axis is message number, Y axis is the byte value
                ax.plot(message_numbers, values, marker='o', linestyle='-', 
                       linewidth=1.5, markersize=5, color='blue', markeredgecolor='darkblue')
                
                ax.set_title(f"Byte Position {byte_position:02d}", fontsize=9, fontweight='bold')
                ax.set_ylabel("Value (0-255)", fontsize=8)
                ax.set_ylim(0, 255)
                ax.set_xlabel("Sample #", fontsize=8)
                ax.grid(True, alpha=0.3)
                ax.tick_params(labelsize=7)
            
            self.figures[byte_position].tight_layout()
            self.canvases[byte_position].draw_idle()  # Use draw_idle for better performance
    
    def sampling_complete(self):
        """Called when sampling is complete"""
        self.running = False
        self.status_label.config(text="Status: Sampling Complete!", foreground="blue")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        messagebox.showinfo("Complete", f"Successfully collected {self.message_count} samples for all 96 byte positions!")


def main():
    root = tk.Tk()
    app = SerialGraphApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
