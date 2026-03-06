# Install Katapult and Klipper on BTT SKR Pico
Configuration / tips / howto

## Katapult setup on RP2040

To install Katapult / canbus on this board follow this little step-by :
1. go to katapult directory
2. make menuconfig
   <img width="632" height="220" alt="image" src="https://github.com/user-attachments/assets/b6985efe-b199-49a3-bb30-50eb816f5482" />

4. make
5. run command to flash firmware :
   `sudo dfu-util -a 0 -d 0483:df11 -s 0x08000000:mass-erase:force -D ~/klipper/canboot-stm32f042-usb-pa9-pa10.bin`
6. remove jumper and reboot the device (reset button is ok)
7. now check the device is ready to receive klipper. Command ls /dev/serial/by-id, should look like this output
   ![image](https://github.com/user-attachments/assets/df7b7081-4174-49f2-825e-2d5dfad15976)
8. make flash FLASH_DEVICE=2e8a:0003
9. remove boot jumper and double click on reset button on the board
10. ls /dev/serial/by-id/* -> should list the board

## Install klipper firmware
1. download "mcu_update.sh" from scripts folder in ~/klipper
2. replace the ZZZZZZZZZZ in the device ID at line 7
3. Also change expander to the right name of your device (3 times)
4. `chmod +x ~/klipper/mcu_update.sh`
5. when the menuconfig display, set settings as bellow :
   <img width="656" height="196" alt="image" src="https://github.com/user-attachments/assets/bc618e48-d34b-4617-955d-ffbcec669699" />

6. Go to the optional features and keep only the first 3 one and last one
7. Press "Q" to quit and save
8. klipper compile and if all is ok, hit enter to start flashing
9. katapult is called to upload firmware, and voilà...
