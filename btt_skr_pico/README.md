# Install Katapult and Klipper on BTT SKR Pico
Configuration / tips / howto

## Katapult setup on RP2040

To install Katapult / canbus on this board follow this little step-by :
1. go to katapult directory
2. `make menuconfig`
    <img width="632" height="220" alt="image" src="https://github.com/user-attachments/assets/b6985efe-b199-49a3-bb30-50eb816f5482" />
3. Press "Q" to quit and save
4. `make`
5. run command to flash firmware :
   `make flash FLASH_DEVICE=2e8a:0003`
6. remove jumper and reboot the device with the reset button
7. `ls /dev/serial/by-id/*` -> should list the board

## Install klipper firmware
1. download "mcu_update.sh" from scripts folder in ~/klipper
2. replace the ZZZZZZZZZZ in the device ID at line 7
3. Also change expander to the right name of your device (3 times)
4. `chmod +x ~/klipper/mcu_update.sh`
5. when the menuconfig display, set settings as bellow :
   <img width="656" height="196" alt="image" src="https://github.com/user-attachments/assets/bc618e48-d34b-4617-955d-ffbcec669699" />
7. Press "Q" to quit and save
8. `make flash FLASH_DEVICE=/dev/serial/by-id/usb-katapult_your_board_id`
9. katapult is called to upload firmware, and voilà...
