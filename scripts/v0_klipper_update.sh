#!/usr/bin/env bash
#
# Script global de mise à jour Klipper — Voron 0.1
# ------------------------------------------------
# Met à jour le dépôt klipper (git pull), puis reflashe successivement
# les trois MCU de la machine :
#   - EBB36 Gen2  (toolhead, USB)
#   - Klipper Expander
#   - Mainboard
#
# Lancement :
#   ~/scripts/v0_klipper_update.sh
#
# Contrairement à la 2.4, la V0.1 est entièrement en USB : il n'y a plus
# de pont CAN, donc plus de contrainte d'ordre entre les cartes.
# L'ordre retenu est simplement toolhead -> expander -> mainboard.

#==============================================================
# CONFIGURATION DES CARTES
#==============================================================
# ⚠ Renseigner les 3 identifiants série avant la première utilisation.
#   Les récupérer avec :  ls /dev/serial/by-id/
#   Ne mettre QUE le nom du fichier, pas le chemin complet.

# EBB36 Gen2 — toolhead, mode USB
EBB_NAME='EBB36 Gen2'
EBB_SERIAL='usb-Klipper_stm32g0b1xx_XXXXXXXXXXXXXXXXXXXXXXXX-if00'
EBB_CONFIG="$HOME/scripts/v0_ebb36.mcu"

# Klipper Expander
EXPANDER_NAME='Klipper Expander'
EXPANDER_SERIAL='usb-Klipper_XXXXXXXX-if00'
EXPANDER_CONFIG="$HOME/scripts/v0_expander.mcu"

# Mainboard
MAINBOARD_NAME='Mainboard V0.1'
MAINBOARD_SERIAL='usb-Klipper_XXXXXXXX-if00'
MAINBOARD_CONFIG="$HOME/scripts/v0_mainboard.mcu"

KLIPPER_DIR="$HOME/klipper"
KATAPULT_FLASHTOOL="$HOME/katapult/scripts/flashtool.py"
SERIAL_DIR='/dev/serial/by-id'

# Mettre à 1 pour sauter les 'make menuconfig' (une fois les .mcu stables)
SKIP_MENUCONFIG=0

#==============================================================
# COULEURS
#==============================================================
MAGENTA=$'\e[35m\n'
YELLOW=$'\e[33m\n'
RED=$'\e[31m\n'
GREEN=$'\e[32m\n'
CYAN=$'\e[36m\n'
NC=$'\e[0m\n'
NC0=$'\e'

# Variantes SANS saut de ligne, pour la couleur en milieu de phrase
RED_I=$'\e[31m'
CYAN_I=$'\e[36m'
NC_I=$'\e[0m'

#==============================================================
# FONCTIONS
#==============================================================
cd "$KLIPPER_DIR"

list_devices(){
    echo -e "${CYAN}Périphériques série actuellement détectés :${NC}"
    ls -1 "$SERIAL_DIR" 2>/dev/null || echo "  (aucun)"
}

check_devices(){
    echo -e "${MAGENTA}===== Étape 0/4 : Vérification des cartes =====${NC}"
    list_devices
    local missing=0
    for entry in "$EBB_NAME|$EBB_SERIAL" \
                 "$EXPANDER_NAME|$EXPANDER_SERIAL" \
                 "$MAINBOARD_NAME|$MAINBOARD_SERIAL"; do
        local name="${entry%%|*}"
        local serial="${entry##*|}"
        if [ -e "$SERIAL_DIR/$serial" ]; then
            echo -e "${GREEN}  OK   $name${NC}"
        else
            echo -e "${RED}  MANQUANT   $name  ->  $serial${NC}"
            missing=$((missing + 1))
        fi
    done
    if [ "$missing" -ne 0 ]; then
        echo -e "${RED}$missing carte(s) introuvable(s). Corriger les identifiants en tête de script.${NC}"
        read -p "${CYAN}Continuer quand même ? [Enter] pour poursuivre, [Ctrl+C] pour annuler.${NC}"
    fi
}

stop_klipper(){
    echo -e "${YELLOW}Arrêt du service Klipper.${NC}"
    sudo service klipper stop
}

start_klipper(){
    echo -e "${YELLOW}Démarrage du service Klipper.${NC}"
    sudo service klipper start
}

update_klipper_repo(){
    cd "$KLIPPER_DIR"
    echo -e "${MAGENTA}===== Étape 1/4 : Mise à jour du dépôt Klipper =====${NC}"
    echo -e "${CYAN}Version locale actuelle :${NC}"
    git log --oneline -1
    echo -e "${YELLOW}Récupération des nouveautés (git fetch)...${NC}"
    git fetch
    echo -e "${CYAN}Dernière version disponible (origin/master) :${NC}"
    git log --oneline -1 origin/master
    echo -e "${CYAN}Commits qui seraient appliqués :${NC}"
    git log --oneline HEAD..origin/master | head -20
    read -p "${CYAN}Lancer le 'git pull' ? Press [Enter] pour continuer, ou [Ctrl+C] pour annuler.${NC}"
    git pull
    echo -e "${GREEN}Dépôt Klipper à jour.${NC}"
}

# flash_board <numero_etape> <nom> <serial> <fichier_config>
flash_board(){
    local step="$1"
    local name="$2"
    local serial="$3"
    local config="$4"

    cd "$KLIPPER_DIR"
    echo -e "${MAGENTA}===== Étape $step/4 : Reflashage de la ${name} =====${NC}"

    if [ ! -f "$config" ]; then
        echo -e "${RED}Fichier de configuration introuvable : $config${NC}"
        read -p "${CYAN}[Enter] pour continuer malgré tout, [Ctrl+C] pour annuler.${NC}"
    fi

    echo -e "${YELLOW}Nettoyage et construction du firmware ${name}.${NC}"
    make clean KCONFIG_CONFIG="$config"

    if [ "$SKIP_MENUCONFIG" -eq 0 ]; then
        read -p "${CYAN}Vérifier sur l'écran suivant que les paramètres sont corrects pour la ${RED_I}${name}${CYAN_I}. Press [Enter] pour continuer, ou [Ctrl+C] pour annuler.${NC}"
        make menuconfig KCONFIG_CONFIG="$config"
    fi

    make KCONFIG_CONFIG="$config" -j4
    read -p "${CYAN}Build ${name} terminé. Vérifier les erreurs ci-dessus. Press [Enter] pour flasher, ou [Ctrl+C] pour annuler.${NC}"

    echo -e "${YELLOW}Flashage de la ${name} via Katapult (USB).${NC}"
    python3 "$KATAPULT_FLASHTOOL" -f "$KLIPPER_DIR/out/klipper.bin" -d "$SERIAL_DIR/$serial"

    echo -e "${YELLOW}Attente du retour de la carte...${NC}"
    local i=0
    while [ ! -e "$SERIAL_DIR/$serial" ] && [ "$i" -lt 15 ]; do
        sleep 1
        i=$((i + 1))
    done
    if [ -e "$SERIAL_DIR/$serial" ]; then
        echo -e "${GREEN}${name} flashée et de nouveau détectée.${NC}"
    else
        echo -e "${RED}${name} flashée mais non détectée après 15 s — vérifier avant de continuer.${NC}"
        read -p "${CYAN}[Enter] pour poursuivre, [Ctrl+C] pour annuler.${NC}"
    fi
}

#==============================================================
# EXÉCUTION
#==============================================================
check_devices

stop_klipper

update_klipper_repo

flash_board 2 "$EBB_NAME"       "$EBB_SERIAL"       "$EBB_CONFIG"
read -p "${CYAN}${EBB_NAME} OK. Press [Enter] pour passer à la ${EXPANDER_NAME}, ou [Ctrl+C] pour annuler.${NC}"

flash_board 3 "$EXPANDER_NAME"  "$EXPANDER_SERIAL"  "$EXPANDER_CONFIG"
read -p "${CYAN}${EXPANDER_NAME} OK. Press [Enter] pour passer à la ${MAINBOARD_NAME}, ou [Ctrl+C] pour annuler.${NC}"

flash_board 4 "$MAINBOARD_NAME" "$MAINBOARD_SERIAL" "$MAINBOARD_CONFIG"

echo -e "${MAGENTA}===== Contrôle final =====${NC}"
list_devices

read -p "${CYAN}Toutes les cartes ont été flashées. Press [Enter] pour relancer Klipper.${NC}"

start_klipper
cd "$KLIPPER_DIR"

echo -e "${GREEN}Mise à jour Klipper terminée avec succès !${NC}"
