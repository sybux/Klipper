#    Command to launch th script:
#    cd "$HOME/klipper" && ./update_klipper_expander.sh
#!/usr/bin/env bash

#Replace ZZZZZZZ with your Expander's serial number - ls -al /dev/serial/by-id
EXPANDERSERIAL='ZZZZZZZZZZZZZZZZZ'

#COLORS
MAGENTA=$'\e[35m\n'
YELLOW=$'\e[33m\n'
RED=$'\e[31m\n'
CYAN=$'\e[36m\n'
NC=$'\e[0m\n'
NC0=$'\e'

#SCRIPT COMMAND DEFINITION
cd "$HOME/klipper"

stop_klipper(){
echo -e "${YELLOW}Stopping Klipper service.${NC}"
sudo service klipper stop
}

start_klipper(){
echo -e "${YELLOW}Starting Klipper service.${NC}"
sudo service klipper start
}

flash_expander(){
cd "$HOME/klipper"
echo -e "${YELLOW}Step 1/2: Cleaning and building Klipper firmware for BTT Expander MCU.${NC}"
make clean KCONFIG_CONFIG=expander.mcu
read -p "${CYAN}Check on the following screen that the parameters are correct for the ${RED}Expander${NC0}${CYAN}firmware. Press [Enter] to continue, or [Ctrl+C] to abort.
${NC}"
make menuconfig KCONFIG_CONFIG=expander.mcu
make KCONFIG_CONFIG=expander.mcu -j4
mv ~/klipper/out/klipper.bin Expander_mcu_klipper.bin
read -p "${CYAN}Expander MCU firmware building complete. Please check above for any errors. Press [Enter] to continue, or [Ctrl+C] to abort.${NC}"
echo -e "${YELLOW}Step 2/2: Flashing Klipper to the Expander MCU.${NC}"
cd ~/klipper/scripts/ && python3 -c 'import flash_usb as u; u.enter_bootloader("/dev/serial/by-id/usb-Klipper_stm32f042x6_'$EXPANDERSERIAL'")'
sleep 3
~/katapult/scripts/flashtool.py -f ~/klipper/Expander_mcu_klipper.bin -d/dev/serial/by-id/usb-CanBoot_stm32f042x6_$EXPANDERSERIAL
}

#SCRIPT EXECUTION
stop_klipper

flash_expander

read -p "${CYAN}Epander MCU firmwares flashed, please check above for any errors. Press [Enter] to continue, or [Ctrl+C] to abort.${NC}"

start_klipper
cd "$HOME/klipper"
