# Update Klipper with Katapult
Configuration / tips / howto

## Katapult setup on STM32F042

To install Katapult / canbus on this board follow this little step-by :
1. download binary from https://github.com/Arksine/katapult/releases/tag/v0.0.1/canboot-stm32f042-usb-pa9-pa10.bin (or from repo here)
   `wget https://github.com/Arksine/katapult/releases/tag/v0.0.1/canboot-stm32f042-usb-pa9-pa10.bin -o ~/klipper/canboot-stm32f042-usb-pa9-pa10.bin`
2. boot the device you wanna install katapult in DFU mode with the jumper
3. run command to flash firmware :
   `sudo dfu-util -a 0 -d 0483:df11 -s 0x08000000:mass-erase:force -D ~/klipper/canboot-stm32f042-usb-pa9-pa10.bin`
4. remove jumper and reboot the device (reset button is ok)
5. now check the device is ready to receive klipper. Command ls /dev/serial/by-id, should look like this output
   ![image](https://github.com/user-attachments/assets/df7b7081-4174-49f2-825e-2d5dfad15976)

## Install klipper firmware
1. download "mcu_update.sh" from scripts folder in ~/klipper
2. replace the ZZZZZZZZZZ in the device ID at line 7
3. Also change expander to the right name of you device (3 times)
4. `chmod +x ~/klipper/mcu_update.sh`
5. when the menuconfig display, set settings as bellow :
   ![image](https://github.com/user-attachments/assets/d52d0706-2fa4-460a-8dce-045c26612cf4)
6. Go to the optional features and keep only the first 3 one and last one
7. Press "Q" to quit and save
8. klipper compile and if all is ok, hit enter to start flashing
9. katapult is called to upload firmware, and voilà...
