#    Command to launch th script:
#    cd "$HOME/klipper" && ./update_klipper_expander.sh
#!/usr/bin/env bash

#Replace ZZZZZZZ with your Expander's serial number
MCU_SERIAL='ZZZZZZZ'


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

flash_display(){
cd "$HOME/klipper"
echo -e "${YELLOW}Step 1/2: Cleaning and building Klipper firmware for BTT Expander MCU.${NC}"
make clean KCONFIG_CONFIG=cheetah.mcu
read -p "${CYAN}Check on the following screen that the parameters are correct for the ${RED}Cheetah 2.0${NC0}${CYAN}firmware. Press [Enter] to continue, or [Ctrl+C] to abo
rt.${NC}"
make menuconfig KCONFIG_CONFIG=cheetah.mcu
make KCONFIG_CONFIG=cheetah.mcu -j4
mv ~/klipper/out/klipper.bin cheetah_mcu_klipper.bin
read -p "${CYAN}Display MCU firmware building complete. Please check above for any errors. Press [Enter] to continue, or [Ctrl+C] to abort.${NC}"
echo -e "${YELLOW}Step 2/2: Flashing Klipper to the Display MCU.${NC}"
echo -e "${YELLOW}Entering boot loader${NC}"
cd ~/klipper/scripts/ && python3 -c 'import flash_usb as u; u.enter_bootloader("/dev/serial/by-id/usb-Klipper_stm32f401xc_'$MCU_SERIAL'")'
sleep 3
echo -e "${YELLOW}Flashing${NC}"
~/katapult/scripts/flashtool.py -f ~/klipper/cheetah_mcu_klipper.bin -d/dev/serial/by-id/usb-katapult_stm32f401xc_$MCU_SERIAL
echo -e "${YELLOW}Special command for cheetah 2.0 to exit flash mode${NC}"
sleep 5
dfu-util  -a 0 -s 0x08000000:leave -U exit.bin
rm exit.bin
}

#SCRIPT EXECUTION
stop_klipper

flash_display

read -p "${CYAN}Display MCU firmwares flashed, please check above for any errors. Press [Enter] to continue, or [Ctrl+C] to abort.${NC}"

start_klipper
cd "$HOME/klipper"
