# Voron 0.1 — Mise en service & calibration

Marche à suivre complète pour (re)configurer et calibrer une Voron 0.1 équipée de :

- tête **CAN bus** (EBB36 / EBB42 / SB2040 + ADXL345 embarqué)
- **plateau 120×120 full size** (chauffe pleine surface)
- Klipper + Mainsail/Fluidd, Katapult pour le flash

> ⚠️ Adapter les pins, UUID et valeurs aux cartes réellement montées.
> Chaque étape se termine par un `SAVE_CONFIG` ou un commit git.

---

## Sommaire

0. [Prérequis](#0-prérequis)
1. [Firmware & CAN bus](#1-firmware--can-bus)
2. [Config de base & sécurités](#2-config-de-base--sécurités)
3. [Vérifications mécaniques à froid](#3-vérifications-mécaniques-à-froid)
4. [Moteurs, sens & courants](#4-moteurs-sens--courants)
5. [Endstops & homing](#5-endstops--homing)
6. [Chauffes & PID](#6-chauffes--pid)
7. [Extrudeur (rotation_distance)](#7-extrudeur-rotation_distance)
8. [Z offset & première couche](#8-z-offset--première-couche)
9. [Input Shaper (ADXL345 sur CAN)](#9-input-shaper-adxl345-sur-can)
10. [Pressure Advance](#10-pressure-advance)
11. [Flow / débit volumétrique max](#11-flow--débit-volumétrique-max)
12. [Macros & finitions](#12-macros--finitions)
13. [Tests de validation](#13-tests-de-validation)
14. [Fiche de valeurs](#14-fiche-de-valeurs)

---

## 0. Prérequis

- [ ] Pi (ou host) à jour, KIAUH ou install manuelle : Klipper + Moonraker + Mainsail/Fluidd
- [ ] Repo git initialisé sur `~/printer_data/config`
- [ ] Alimentation vérifiée : 24 V stable, section suffisante pour le lit 120×120
- [ ] Câblage CAN vérifié **avant** mise sous tension (CANH/CANL non inversés, pas de 24 V sur le bus)
- [ ] Résistances de terminaison : **2 × 120 Ω** sur le bus (une à chaque extrémité, souvent un jumper sur la carte tête + un sur l'adaptateur)

```bash
cd ~/printer_data/config
git init && git add . && git commit -m "baseline"
```

---

## 1. Firmware & CAN bus

### 1.1 Choix de la topologie

| Option | Description |
|---|---|
| **A. USB→CAN bridge** | La carte mère (SKR Pico, Mini E3, Manta…) fait elle-même le pont USB↔CAN. Pas d'adaptateur externe. |
| **B. Adaptateur dédié** | U2C / CANable / Pi CAN hat. La carte mère reste en USB classique. |

> Bitrate : **1 000 000** si tout le câblage est propre et court (cas Voron 0), sinon **500 000** — la valeur doit être **identique** dans les 3 endroits : firmware MCU, firmware tête, `can0`.

### 1.2 Flash

```bash
# Katapult (bootloader) puis Klipper
cd ~/katapult && make menuconfig   # cible = RP2040 / STM32 selon carte
make flash FLASH_DEVICE=...
cd ~/klipper && make menuconfig    # Communication interface: CAN bus (ou USB-CAN bridge)
make
```

- [ ] MCU principal flashé
- [ ] Carte tête (EBB) flashée via Katapult
- [ ] Notées les commandes exactes de flash dans `docs/flash.md` (on les oublie toujours)

### 1.3 Interface `can0`

`/etc/network/interfaces.d/can0` :

```
allow-hotplug can0
iface can0 can static
    bitrate 1000000
    up ip link set can0 txqueuelen 128
```

Redémarrer, puis récupérer les UUID :

```bash
ip -details link show can0
~/klippy-env/bin/python ~/klipper/scripts/canbus_query.py can0
```

- [ ] 2 UUID visibles (ou 1 si USB-CAN bridge : le MCU principal n'apparaît pas en CAN)
- [ ] UUID reportés dans `printer.cfg`

```ini
[mcu]
serial: /dev/serial/by-id/usb-Klipper_rp2040_5044340410A1C31C-if00

[mcu expander]
serial: /dev/serial/by-id/usb-Klipper_stm32f042x6_1F0004000643305551363420-if00

[mcu EBBCan]
canbus_uuid: 5b05e772b541
```

---

## 2. Config de base & sécurités

Partir de la config officielle Voron 0.1 correspondant à la carte mère, puis :

- [ ] `[printer]` : `kinematics: corexy`, `max_velocity: 300`, `max_accel: 3000` (valeur de départ prudente), `max_z_velocity: 15`, `square_corner_velocity: 5`
- [ ] `position_max` X/Y/Z cohérents avec le **plateau full size** — vérifier physiquement que la buse ne tape ni les courroies, ni les vis du plateau, ni le passage de câble
- [ ] `[verify_heater]` actifs pour buse **et** lit (ne jamais désactiver)
- [ ] `[idle_timeout]` configuré
- [ ] `[temperature_sensor]` pour MCU, host et EBB (surveillance CAN)
- [ ] `[exclude_object]`, `[respond]`, `[gcode_arcs]` si utilisés par OrcaSlicer

⚠️ **Spécifique plateau 120×120 full size** : le Z endstop d'origine (buse sur microswitch, coin arrière-droit) peut être masqué ou décalé par le plateau pleine surface. Vérifier :
- [ ] dégagement mécanique du switch,
- [ ] que le point de palpage est bien **hors** de la surface d'impression ou compensé par `position_endstop`,
- [ ] sinon passer à un palpeur type sonde/nozzle-probe et adapter `[homing_override]`.

Commit : `git commit -m "config de base + UUID CAN"`

---

## 3. Vérifications mécaniques à froid

À faire **avant** toute calibration logicielle — c'est là que se gagnent 80 % des résultats.

- [ ] Cadre équerré, extrusions bien en appui
- [ ] Rails X/Y/Z : vis serrées en croix, chariots sans point dur sur toute la course
- [ ] Poulies folles libres, sans jeu axial ; vis de poulies dentées serrées **sur le méplat**
- [ ] Tension des courroies A/B **identique** — cible ≈ **110 Hz** sur la portion libre (app Gates Carbon Drive / Spectroid). Toujours retendre les deux ensemble.
- [ ] Courroie Z (si Voron 0 avec courroie) ou vis T8 : pas de jeu, accouplement serré
- [ ] Deracking : desserrer les vis des chariots A/B, envoyer le portique en butée, resserrer
- [ ] Plateau : plan réglé au réglet/feeler, vis à ressort ou fixe selon montage
- [ ] Tête CAN : hotend bien enfoncé, ventilo de dissipation câblé et **testé**
- [ ] Câble CAN de la tête : chaîne/toron libre sur toute la course, pas de traction

---

## 4. Moteurs, sens & courants

- [ ] Courant TMC : ~0.5–0.8 A RMS pour NEMA14/17 pancake de V0 — ne pas surchauffer
- [ ] `stealthchop_threshold: 0` (spreadCycle) sur X/Y pour la précision
- [ ] Sens de rotation : `FORCE_MOVE` avant tout homing

```gcode
FORCE_MOVE STEPPER=stepper_x DISTANCE=10 VELOCITY=20
FORCE_MOVE STEPPER=stepper_y DISTANCE=10 VELOCITY=20
FORCE_MOVE STEPPER=stepper_z DISTANCE=5 VELOCITY=5
```

CoreXY : `stepper_x` seul → tête en diagonale **avant-droit** ; `stepper_y` seul → diagonale **arrière-droit** (inverser `dir_pin` avec `!` si besoin).

- [ ] `rotation_distance: 40` (poulie 20T GT2) pour X/Y
- [ ] Z : `rotation_distance` = pas de la vis (T8×8 → `8`) ou périmètre poulie si Z par courroie
- [ ] `microsteps: 32` (bon compromis charge CPU / lissage)

Diagnostic drivers :

```gcode
DUMP_TMC STEPPER=stepper_x
```

---

## 5. Endstops & homing

```gcode
QUERY_ENDSTOPS
```

- [ ] Chaque endstop passe `open` → `TRIGGERED` quand on l'actionne à la main
- [ ] X puis Y puis Z homés séparément, main sur l'interrupteur d'urgence au premier essai
- [ ] `homing_speed` réduit (25 mm/s) pour le premier test
- [ ] `position_endstop` Z réglé grossièrement (voir §8)
- [ ] `[safe_z_home]` / `[homing_override]` : position de palpage correcte pour le plateau full size

```gcode
G28
G0 X60 Y60 Z10 F3000   # doit finir au centre, sans collision
```

Test des limites, doucement :

```gcode
G0 X0 Y0 F3000
G0 X120 Y120 F3000
```

- [ ] Aucun contact en butée logicielle → ajuster `position_max` si nécessaire

---

## 6. Chauffes & PID

Avec le **plateau 120×120 full size**, la masse thermique est plus élevée : PID à la température réellement utilisée (ABL/ABS ≈ 100–110 °C), pas à 60 °C.

```gcode
PID_CALIBRATE HEATER=extruder TARGET=245
PID_CALIBRATE HEATER=heater_bed TARGET=100
SAVE_CONFIG
```

- [ ] PID buse fait (avec le ventilo de couche **coupé**, puis vérifier à 100 % si dérive)
- [ ] PID lit fait à la température de travail
- [ ] `max_power` du lit ajusté si l'alim tire trop (`max_power: 0.8` par ex.)
- [ ] Temps de montée à 100 °C noté (référence pour détecter une dégradation future)
- [ ] Thermistances : bon `sensor_type` (Generic 3950 vs ATC Semitec 104NT/104GT) — une erreur ici fausse tout
- [ ] Test de chauffe chambre : température atteinte en 15 min à noter (V0 monte vite, attention aux pièces ABS/PC)

---

## 7. Extrudeur (rotation_distance)

Buse à température, filament chargé :

```gcode
G91
G1 E100 F60   # extrusion lente de 100 mm
```

Mesurer la longueur réellement consommée (repère à 120 mm de l'entrée de l'extrudeur) :

```
nouvelle_rotation_distance = ancienne × (mesuré_consommé / 100)
```

- [ ] Écart final < 1 %
- [ ] Refaire si changement de galets ou de tension du levier
- [ ] `max_extrude_only_distance` adapté (150 pour les macros de purge)

---

## 8. Z offset & première couche

- [ ] Palpage/homing Z répétable : `PROBE_ACCURACY` (si sonde) ou 5 × `G28 Z` + `GET_POSITION` → dispersion < 0.01 mm
- [ ] Réglage grossier avec une feuille de papier
- [ ] Affinage en impression :

```gcode
Z_OFFSET_APPLY_ENDSTOP   # ou _PROBE selon montage
SAVE_CONFIG
```

- [ ] Impression d'un patch 1 couche pleine surface → aspect homogène, coins identiques au centre
- [ ] Si écart coins/centre : reprendre le plan du plateau (§3), **pas** le Z offset

---

## 9. Input Shaper (ADXL345 sur CAN)

Config type (accéléro sur la carte tête) :

```ini
[adxl345]
cs_pin: EBBCan: gpio1
spi_software_sclk_pin: EBBCan: gpio2
spi_software_mosi_pin: EBBCan: gpio0
spi_software_miso_pin: EBBCan: gpio3
axes_map: x,y,z          # à vérifier selon orientation de la carte

[resonance_tester]
probe_points: 60, 60, 30
accel_chip: adxl345
```

```gcode
ACCELEROMETER_QUERY      # doit renvoyer ~ (0,0,9800) au repos
SHAPER_CALIBRATE
SAVE_CONFIG
```

- [ ] `axes_map` validé (secouer la tête à la main axe par axe)
- [ ] Courbes exportées et archivées dans `docs/shaper/`
- [ ] Fréquences X et Y notées ; si < 40 Hz sur un axe → **retourner au §3**, c'est mécanique
- [ ] `max_accel` fixé à la valeur recommandée, pas au-delà
- [ ] Refaire après toute modif de masse sur la tête

---

## 10. Pressure Advance

Méthode Klipper (tour de test) ou OrcaSlicer (PA pattern / line method).

```gcode
SET_PRESSURE_ADVANCE ADVANCE=0.04
TUNING_TOWER COMMAND=SET_PRESSURE_ADVANCE PARAMETER=ADVANCE START=0 FACTOR=.005
```

Valeurs de départ indicatives (direct drive court, type Mini SB / LGX Lite) :

| Matière | PA de départ |
|---|---|
| PLA | 0.03 – 0.05 |
| PETG | 0.05 – 0.08 |
| ABS/ASA | 0.03 – 0.05 |

- [ ] Une valeur **par filament**, stockée côté Klipper (`[extruder] pressure_advance`) ou en macro `SET_PRESSURE_ADVANCE` par matière
- [ ] PA laissé à **0** dans le slicer si géré par Klipper (ne pas cumuler)

---

## 11. Flow / débit volumétrique max

- [ ] Flow ratio : cube 30 mm mono-paroi (vase), mesurer l'épaisseur → `flow = largeur_théorique / mesurée`
- [ ] Test de débit max : extrusion en l'air à débit croissant jusqu'au décrochage / sous-extrusion
  - hotend V6 clone : ~8–11 mm³/s
  - Dragon/Rapido UHF : au-delà, mais la V0 est souvent limitée par l'accélération, pas par le débit
- [ ] `max_volumetric_speed` renseigné dans le profil filament OrcaSlicer
- [ ] Vitesse d'impression réaliste = `débit_max / (hauteur_couche × largeur)`

---

## 12. Macros & finitions

- [ ] `PRINT_START` : chauffe lit → attente chambre → chauffe buse → G28 → purge line
- [ ] `PRINT_END` : rétraction, dégagement, coupure chauffes, ventilo chambre
- [ ] `CANCEL_PRINT`, `PAUSE`, `RESUME` (Voron standard)
- [ ] `[firmware_retraction]` si le slicer l'utilise
- [ ] Capteur de filament : `SFS_ENABLE` / `SFS_DISABLE` dans PRINT_START / PRINT_END / CANCEL_PRINT
- [ ] LED / neopixel tête sur CAN
- [ ] Ventilo chambre / filtre piloté par `[fan_generic]`
- [ ] Sauvegarde Moonraker → git automatisée (`moonraker-timelapse` / `git-backup`)

---

## 13. Tests de validation

Dans l'ordre :

1. [ ] **Cube de calibration 30 mm** — dimensions ±0.1 mm
2. [ ] **Voron Design Cube** — qualité générale, ghosting
3. [ ] **Test de tolérance** / pion-trou
4. [ ] **Benchy** à vitesse nominale puis à 1.5×
5. [ ] **Impression longue (> 2 h)** — vérifier dérive thermique, tenue du CAN (`Timer too close` / `Lost communication with MCU` = problème de bus)
6. [ ] Contrôle après 24 h d'impression : tension courroies, vis, température drivers

---

## 14. Fiche de valeurs

À remplir et versionner — c'est la référence en cas de régression.

| Paramètre | Valeur | Date |
|---|---|---|
| Bitrate CAN | | |
| UUID MCU | | |
| UUID tête | | |
| rotation_distance X/Y | 40 | |
| rotation_distance Z | | |
| rotation_distance extrudeur | | |
| Tension courroies A/B (Hz) | | |
| PID buse (Kp/Ki/Kd) | | |
| PID lit (Kp/Ki/Kd) | | |
| Z endstop / offset | | |
| Shaper X (type / Hz) | | |
| Shaper Y (type / Hz) | | |
| max_accel retenu | | |
| PA PLA / PETG / ABS | | |
| Flow ratio par matière | | |
| Débit max (mm³/s) | | |

---

## Journal

| Date | Modification | Résultat |
|---|---|---|
| | | |
