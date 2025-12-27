# Klipper – Calibration complète (CoreXY)

BLTouch • Bed Mesh • ADXL345 • Input Shaper • Pressure Advance

Ce document regroupe toutes les commandes nécessaires à la calibration complète
d’une imprimante CoreXY sous Klipper. La configuration est supposée déjà fonctionnelle.

---

## Étape 1 – Homing
```gcode
G28
```

---

## Étape 2 – Calibration Z (BLTouch)
```gcode
PROBE_CALIBRATE
TESTZ Z=-0.1
TESTZ Z=+0.1
ACCEPT
SAVE_CONFIG
```

---

## Étape 3 – Bed Mesh (nivellement plateau)
```gcode
BED_MESH_CALIBRATE
BED_MESH_PROFILE LOAD=default
SAVE_CONFIG
```

---

## Étape 4 – PID Tuning
### Hotend
```gcode
PID_CALIBRATE HEATER=extruder TARGET=210
```

### Plateau
```gcode
PID_CALIBRATE HEATER=heater_bed TARGET=60
SAVE_CONFIG
```

---

## Étape 5 – Mesure des résonances (ADXL345)
### Axe X
```gcode
TEST_RESONANCES AXIS=X
```

### Axe Y
```gcode
TEST_RESONANCES AXIS=Y
```

---

## Étape 6 – Input Shaper
```gcode
SHAPER_CALIBRATE
SAVE_CONFIG
```

---

## Étape 7 – Pressure Advance
```gcode
TUNING_TOWER COMMAND=SET_PRESSURE_ADVANCE PARAMETER=ADVANCE START=0 FACTOR=.005
SET_PRESSURE_ADVANCE ADVANCE=0.0XX
SAVE_CONFIG
```

---

## Étape 8 – Vérification finale
```gcode
STATUS
```

---

Notes CoreXY :
- Toujours mesurer X et Y séparément
- Refaire l’input shaper après toute modification mécanique
- Documenter les valeurs finales dans le dépôt Git
