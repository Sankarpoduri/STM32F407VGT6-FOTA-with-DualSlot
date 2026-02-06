# STM32F407 Dual-Slot FOTA using ESP32 (SPI)

This project implements a **dual-slot (ping-pong) Firmware Over-The-Air (FOTA)** update system on the **STM32F407VGT6** microcontroller.  
An **ESP32** is used as a Wi-Fi enabled bridge to manage firmware updates and communicate with the STM32 via **SPI**.

The design ensures that a previously working firmware is always preserved if an update fails.

---

## System Architecture

The system consists of three main components:

### 1. STM32F407 (Target Device)
- Runs a custom bootloader
- Contains two application slots in internal flash
- Selects the application to boot based on metadata
- Communicates with ESP32 over SPI
- Provides the currently running slot (bank ID)

### 2. ESP32 (OTA Bridge)
- Acts as SPI **master**
- STM32 acts as SPI **slave**
- Connects to Wi-Fi
- Communicates with a local Python server using HTTP
- Queries STM32 to determine the active slot
- Downloads firmware and transfers it to STM32 via SPI
- Controls STM32 reset when required
- Stores firmware version using ESP32 Preferences
- Prints update logs on the serial monitor

### 3. Python Server (Local)
- Implemented using Flask
- Runs locally on a PC
- Periodically polls a public AWS S3 bucket
- Downloads firmware files when a newer version is available
- Decides whether to send an update
- Decides which slot firmware to send (ping-pong logic)

---

## Flash Memory Layout (STM32F407)

| Region      | Address       |
|------------|--------------|
| Bootloader | 0x08000000   |
| Slot A     | 0x08020000   |
| Slot B     | 0x08060000   |
| Metadata   | 0x080E0000   |

---

## Bootloader Operation

1. Bootloader is flashed once using **STM32CubeProgrammer**
2. On reset, the bootloader:
   - Reads metadata stored at `0x080E0000`
   - Determines the active slot
   - Jumps to:
     - Slot A (`0x08020000`) or
     - Slot B (`0x08060000`)

Initially, Slot A is marked as active.

---

## Application Design (Slot A & Slot B)

- The **same application functionality** is built separately for both slots  
  (example: reading temperature from a sensor).
- The binaries are generated independently only for slot placement.
- LED blinking is used **only for identification during testing**:
  - Slot A → Green LED blinks
  - Slot B → Orange LED blinks

---

## Initial Programming

- Bootloader is flashed to STM32
- `slot_a.bin` is flashed manually to Slot A using STM32CubeProgrammer
- After reset, Slot A application starts running

---

## Firmware Storage & Versioning

### AWS S3 Bucket (Public Access)
Contains:
- `slot_a.bin`
- `slot_b.bin`
- `version.txt` (latest firmware version)

### Local Server Firmware Folder
Contains:
- `slot_a.bin`
- `slot_b.bin`
- `version.txt` (current server version)

Firmware binaries and version files are **manually generated and uploaded** to the S3 bucket.

---

## Python Server Logic (Flask)

- A background thread periodically polls the S3 bucket
- The server:
  1. Downloads `version.txt` from S3
  2. Compares it with the local `version.txt`
  3. If the S3 version is higher:
     - Downloads `slot_a.bin` and `slot_b.bin`
     - Updates the local firmware folder
- The server exposes two HTTP endpoints:
  - `/version` → returns current server firmware version
  - `/firmware?current_bank=X` → sends firmware for the inactive slot

---

## Slot Selection (Ping-Pong Logic)

1. ESP32 communicates with STM32 over SPI
2. ESP32 requests the **current bank ID** (0 = Slot A, 1 = Slot B)
3. ESP32 sends this information to the server
4. The server selects:
   - If Slot A is running → send Slot B firmware
   - If Slot B is running → send Slot A firmware

This ensures the currently running firmware remains intact.

---

## Firmware Update Flow

1. ESP32 boots and connects to Wi-Fi
2. ESP32 reads the stored firmware version from Preferences
3. ESP32 checks `/version` endpoint on the server
4. If a newer version is available:
   - ESP32 resets STM32
5. ESP32 requests `/firmware` with the current bank ID
6. Server responds with the inactive slot firmware
7. ESP32 transfers firmware to STM32 via SPI:
   - START_OTA command
   - Chunked data transfer
   - END_OTA command
8. STM32 flashes firmware to inactive slot
9. Metadata is updated after successful flashing
10. ESP32 resets STM32
11. Bootloader jumps to the updated slot

---

## Failure Handling

- If firmware transfer or flashing fails:
  - Metadata is not updated
  - STM32 continues to boot the previous working slot
- This prevents device bricking and allows recovery

---

## SPI Communication Summary

- ESP32 → SPI Master
- STM32 → SPI Slave
- Custom SPI commands used:
  - Ping
  - Get Bank ID
  - Start OTA
  - Data Chunk Transfer
  - End OTA
  - Reboot

Firmware is sent in small chunks to ensure reliability.

---

## Tools Used

- STM32CubeIDE
- STM32CubeProgrammer
- ESP32 (Arduino)
- Python (Flask, Requests)
- AWS S3 (public firmware hosting)

---

## Notes

- Slot A and Slot B run the same application logic
- Separate binaries exist only for slot placement
- Firmware update decision is handled by the server
- Tested using a local Python server connected to AWS S3
