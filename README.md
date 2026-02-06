# STM32F407 Dual-Slot FOTA using ESP32 (SPI)

This project implements a **dual-slot (ping-pong) Firmware Over-The-Air (FOTA)** mechanism on the **STM32F407VGT6** microcontroller.  
An **ESP32** is used as an external controller to manage firmware updates and communicate with the STM32 via **SPI**.

The system ensures that a previously working firmware is preserved if an update fails.

---

## System Overview

The FOTA system consists of three main components:

### 1. STM32F407
- Runs a custom bootloader
- Contains two application slots in internal flash
- Boots Slot-A or Slot-B based on metadata
- Provides current running slot information to ESP32

### 2. ESP32
- Communicates with STM32 via SPI
- Queries STM32 to identify the currently running slot
- Receives update instructions from a local Python server
- Transfers firmware binaries to STM32
- Resets STM32 when required
- Prints update status on the serial monitor

### 3. Python Server (Local)
- Runs locally on a PC
- Connects to an AWS S3 bucket
- Manages firmware version comparison
- Decides whether an update is required
- Decides **which slot binary** should be sent

---

## Flash Memory Layout (STM32)

| Region        | Address       |
|--------------|--------------|
| Bootloader   | 0x08000000   |
| Slot A       | 0x08020000   |
| Slot B       | 0x08060000   |
| Metadata     | 0x080E0000   |

---

## Bootloader Operation

1. Bootloader is flashed once using **STM32CubeProgrammer**
2. On reset, the bootloader:
   - Reads metadata stored at `0x080E0000`
   - Determines the active slot
   - Jumps to:
     - **Slot A (0x08020000)** or
     - **Slot B (0x08060000)**

Initially, Slot-A is marked active.

---

## Application Design

- The **same application functionality** is built separately for both Slot-A and Slot-B  
  (for example, temperature sensor reading).
- The application behavior is identical in both slots.
- **LED blinking is used only for identification**:
  - Slot-A application → **Green LED blinks**
  - Slot-B application → **Orange LED blinks**

This helps visually identify which slot is currently running during testing.

---

## Initial Programming

- Bootloader is flashed to STM32
- `slot-a.bin` is flashed manually to Slot-A using STM32CubeProgrammer
- On reset, Slot-A application starts running

---

## Firmware Version Management

### AWS S3 Bucket Contents
- `slot-a.bin`
- `slot-b.bin`
- `version.txt` (latest firmware version)

### Local Server Firmware Folder
- `slot-a.bin`
- `slot-b.bin`
- `version.txt` (current version)

The firmware binaries are **manually generated** and uploaded to the AWS S3 bucket.

---

## Python Server Logic

1. The server compares:
   - AWS `version.txt`
   - Local `version.txt`
2. If the AWS version is higher:
   - Firmware files are downloaded from S3 to the local firmware folder
3. The server communicates with ESP32 to:
   - Check the currently running slot on STM32
   - Decide which slot should receive the update

---

## Slot Selection Logic

- ESP32 communicates with STM32 and determines:
  - Whether Slot-A or Slot-B is currently running
- This information is sent to the Python server
- The server decides:
  - If Slot-A is running → **Slot-B firmware is sent**
  - If Slot-B is running → **Slot-A firmware is sent**

This ensures the currently running firmware is preserved.

---

## Firmware Update Flow

1. STM32 runs the current application
2. ESP32 queries STM32 to identify the active slot
3. ESP32 sends this information to the Python server
4. Server checks for a newer firmware version
5. Server selects the inactive slot firmware
6. ESP32 transfers the selected `.bin` file to STM32 via SPI
7. STM32 flashes the firmware into the inactive slot
8. Metadata is updated after successful flashing
9. ESP32 resets the STM32
10. Bootloader jumps to the updated slot

---

## Failure Handling

- If the update fails:
  - Metadata is not updated
  - STM32 continues booting the previous working slot
- This prevents device bricking and ensures recovery

---

## Tools Used

- STM32CubeIDE
- STM32CubeProgrammer
- ESP32 (SPI communication)
- Python (local server)
- AWS S3 (firmware storage)

---

## Notes

- Slot-A and Slot-B run the same application logic
- Separate binaries are generated only for slot placement
- The system was tested using a local Python server connected to AWS S3
