# STM32F407VGT6-FOTA-with-DualSlot
Firmware Over-The-Air (FOTA) update system for STM32 using an ESP32 as a gateway over SPI. Implements a dual-slot (ping-pong) bootloader architecture to ensure safe firmware updates with rollback support. The ESP32 fetches firmware from a remote server and transfers it to the STM32 via SPI.
