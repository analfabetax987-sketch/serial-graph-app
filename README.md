# Serial Port Data Grapher - 96 Byte Position Channels

A Python application that reads 96-byte messages from a serial port (COM5) and graphs how each byte position's value changes across messages.

## How It Works

Each message contains **96 integer values** (one per byte position). This application creates **96 separate line graphs**, where:

- **Graph for Byte Position 0**: Shows how the value at position 0 changes across successive messages
  - Message 1: value = X
  - Message 2: value = Y
  - Message 3: value = Z
  - (and so on...)

- **Graph for Byte Position 1**: Shows how the value at position 1 changes across successive messages
- **...continuing for all 96 byte positions**

## Features

- **96 Individual Graphs**: One graph per byte position
- **Growing Line Plots**: Each new message adds one point to all 96 graphs
- **Real-time Updates**: Graphs update as messages arrive from the serial port
- **Scrollable Interface**: Easily scroll through all 96 byte position channels
- **Message Detection**: Automatically detects complete 96-byte messages based on time pauses between bytes
- **GUI Controls**: Start/Stop buttons and message count display
- **Integer Values**: Each byte is an unsigned 8-bit integer (0-255)

## Requirements

- Python 3.7+
- pyserial
- matplotlib
- numpy
- tkinter (usually included with Python)

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Edit `serial_graph_app.py` to adjust:
- `PORT`: Serial port name (default: "COM5")
- `BAUD_RATE`: Serial communication speed (default: 9600)
- `EXPECTED_BYTES`: Message size in bytes (default: 96)
- `PAUSE_THRESHOLD`: Time pause between messages in seconds (default: 0.5)

## Usage

```bash
python serial_graph_app.py
```

1. Click "Start" to connect to the serial port
2. Scroll through the 96 graphs to see all byte positions
3. Each time a complete 96-byte message arrives, all 96 graphs add a new data point
4. X-axis shows message number, Y-axis shows the integer value (0-255)
5. Click "Stop" to disconnect

## Example

Suppose you receive 5 messages with the following byte values:

```
Message 1: [100, 150, 200, ...]  (96 values)
Message 2: [102, 148, 198, ...]  (96 values)
Message 3: [101, 152, 199, ...]  (96 values)
Message 4: [103, 151, 201, ...]  (96 values)
Message 5: [104, 149, 202, ...]  (96 values)
```

Then:
- **Byte Position 0 graph** will show: 100 → 102 → 101 → 103 → 104
- **Byte Position 1 graph** will show: 150 → 148 → 152 → 151 → 149
- **Byte Position 2 graph** will show: 200 → 198 → 199 → 201 → 202
- ... and so on for all 96 positions

## Troubleshooting

- **Connection Error**: Check that COM5 is available and the correct baud rate is set
- **No data**: Verify the serial device is sending data and the port settings match
- **Graph not updating**: Make sure complete 96-byte messages are being received (check pause timing)
