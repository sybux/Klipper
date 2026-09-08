# Voron 0.1 — Guide de recalibration

Procédures de réglage à appliquer **après un changement matériel** ou en entretien
périodique. Part du principe que la machine tourne déjà : `printer.cfg` existe,
le CAN est fonctionnel, les axes homent.

Volume utile de référence : **X 0→120**, **Y 4→120**, plateau 120×120 full size,
tête CAN avec ADXL345 embarqué.

---

## Contenu du dépôt

```
.
├── README.md
├── config/
│   └── calibration.cfg          # macros d'aide — [include calibration.cfg]
├── gcode/
│   ├── first_layer_squares.gcode   # 5 zones : plan du plateau        (~4 min)
│   ├── first_layer_patch.gcode     # patch plein 80×80 : Z offset     (~10 min)
│   ├── pa_line_test.gcode          # 20 lignes PA 0→0.095             (~5 min)
│   └── retraction_tower.gcode      # 2 tours : stringing              (~15 min)
├── scripts/
│   └── gen_calibration_gcode.py # régénère les .gcode (temps, buse, volume…)
└── docs/
    └── shaper/                  # archives des .csv d'input shaper
```

Les `.gcode` sont **autonomes** : chauffe, homing, purge et test inclus, aucun
slicer nécessaire. Ils s'envoient directement dans Mainsail/Fluidd.

Ils sont générés pour **PLA 215/60 °C, couche 0.20, largeur 0.45, 25 mm/s**.
Pour de l'ABS ou une autre buse :

```bash
cd scripts
python3 gen_calibration_gcode.py --nozzle 255 --bed 100 --fan 0
python3 gen_calibration_gcode.py --width 0.6 --height 0.3   # buse 0.6
```

Installation des macros :

```ini
# dans printer.cfg
[include calibration.cfg]
```

---

## Matrice : qu'est-ce qui a changé ?

Trouve la ligne correspondant à ton intervention, applique les procédures
indiquées **dans l'ordre des numéros**.

| Intervention | P1 Drivers | P2 Méca | P3 PID | P4 Extrudeur | P5 1ère couche | P6 Shaper | P7 PA | P8 Flow | P9 Débit |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Buse seule** (même Ø) | | | ● | | ● | | | | |
| **Buse Ø différent** | | | ● | | ● | | ● | ● | ● |
| **Hotend complet** | | | ● | ● | ● | | ● | ● | ● |
| **Extrudeur / galets** | | | | ● | ● | | ● | ● | |
| **Tête complète (CAN)** | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| **Courroies A/B** | | ● | | | | ● | | | |
| **Rail / chariot X ou Y** | | ● | | | | ● | | | |
| **Moteur ou driver** | ● | | | | | ● | | | |
| **Plateau / surface** | | ● | ● | | ● | | | | |
| **Thermistance** | | | ● | | | | | | |
| **Nouveau filament** | | | | | | | ● | ● | ● |
| **Nouvelle bobine, même réf.** | | | | | ● | | | ● | |
| **Mise à jour Klipper** | ● | | | | | | | | |
| **Entretien trimestriel** | ● | ● | | | ● | ● | | | |

Légende : ● = à refaire.

---

## P1 — Contrôle des drivers

**Quand :** après tout changement électrique, moteur, driver, ou mise à jour Klipper.

```gcode
TMC_STATUS
```

Points de contrôle sur chaque axe :

| Champ | Attendu | Si non conforme |
|---|---|---|
| lecture des registres | pas d'erreur `Unable to read` | mauvais `uart_pin` / `uart_address` |
| `GCONF` | `en_spreadcycle=1` sur X, Y, Z | voir encadré ci-dessous |
| `cs_actual` | 16 à 28 | ajuster `run_current` / vérifier `sense_resistor` |
| `GSTAT` | `00000000` | reset ou sous-tension → alim / câblage |
| `mres` | conforme à `microsteps` | — |

> ⚠️ **Piège `stealthchop_threshold`**
> `stealthchop_threshold: 0` **active** stealthChop en permanence, il ne le
> désactive pas. Pour du spreadCycle, la ligne doit être **absente ou commentée**.
> Les configs Voron d'origine embarquent `: 0` sur X, Y et Z — à corriger.

Vérification du courant réellement appliqué (TMC2209, `vsense=1`) :

```
Irms = (cs_actual + 1)/32 × 0.180 / (Rsense + 0.02) × 1/√2
```

**Contrôle du câblage moteur** — les drapeaux `ola`/`olb` ne sont exploitables
qu'avec le driver actif et en mouvement (`enn=0`, `stst` absent) :

```gcode
TMC_STATUS_MOVING AXIS=x
```

À l'arrêt ils sont systématiquement levés : c'est normal, pas un défaut.

**Bruit spreadCycle.** Sifflement continu à l'arrêt = comportement attendu.
Pour le réduire sans perdre le mode : `hold_current: 0.4` sur X et Y
(**pas sur Z** : risque de descente du plateau).

---

## P2 — Mécanique

**Quand :** courroies, rails, chariots, plateau, entretien.

C'est ici que se joue l'essentiel du résultat. Aucune calibration logicielle ne
rattrape une mécanique approximative.

- [ ] Rails X/Y/Z : vis serrées en croix, aucun point dur sur toute la course
- [ ] Poulies folles libres, sans jeu axial ; poulies dentées serrées **sur le méplat**
- [ ] Tension A/B **identique**, cible ≈ **110 Hz** (app Gates Carbon Drive ou Spectroid)
- [ ] Deracking : desserrer les vis des chariots A/B, envoyer le portique en butée, resserrer
- [ ] Vis Z / accouplement sans jeu
- [ ] Chaîne ou toron CAN libre sur toute la course, aucune traction en butée

Contrôle des dégagements après remontage :

```gcode
AXES_LIMITS
G28
G1 Z30 F600
G1 X5 Y6 F1500
G1 X115 Y115 F1500
```

Réglage du plan du plateau (pas de sonde sur V0.1) — la commande enchaîne les
vis une par une et attend ta réponse à chaque étape :

```gcode
G28
BED_SCREWS_ADJUST
```

La buse descend à l'aplomb de la première vis. Test de la feuille, puis :

| Réponse | Effet |
|---|---|
| `ACCEPT` | vis correcte, passe à la suivante |
| `ADJUSTED` | tu as tourné la vis → Klipper refera un tour complet à la fin |
| `ABORT` | sort de la procédure |

Répéter jusqu'à ce qu'un tour entier se termine sans un seul `ADJUSTED`.

> Les positions des vis sont dans la section `[bed_screws]` de `calibration.cfg`
> — à adapter à ton montage de plateau full size. Ce sont les coordonnées où la
> **buse** doit se placer, pas celles des vis vues de dessous.

---

## P3 — PID

**Quand :** hotend, buse, thermistance, plateau, ou dérive constatée.

```gcode
PID_ALL HOTEND=245 BED=100
SAVE_CONFIG
```

- PID buse **avec le ventilateur de couche coupé**, puis vérifier la stabilité à 100 %
- PID plateau **à la température de travail réelle** (100–110 °C en ABS) : avec un
  120×120 full size, l'inertie thermique est trop différente pour extrapoler depuis 60 °C
- Noter le temps de montée à 100 °C dans la fiche §Valeurs — c'est ta référence
  pour détecter plus tard une résistance qui faiblit ou un MOSFET qui chauffe

Si l'alimentation tire trop : `max_power: 0.8` sur `[heater_bed]`.

---

## P4 — Extrudeur (`rotation_distance`)

**Quand :** extrudeur, galets, tension du levier, hotend.

```gcode
E_TEST TEMP=215
```

Repère le filament à 120 mm de l'entrée de l'extrudeur, laisse extruder 100 mm,
mesure ce qui reste **au pied à coulisse**, puis :

```gcode
E_CALC LEFT=19
```

La macro lit la `rotation_distance` courante et affiche la nouvelle valeur.

- Critère : écart final **< 1 %**
- Un écart < 0.5 % est dans le bruit de mesure d'un réglet — ne corrige que si
  la mesure est répétable deux fois
- Reporter la valeur dans `[extruder]`, puis `FIRMWARE_RESTART`

> Après cette correction, **remettre le flow ratio à 1.0 dans OrcaSlicer** avant
> de passer en P8. Sinon la même erreur est compensée deux fois.

---

## P5 — Z offset et première couche

**Quand :** buse, hotend, plateau, surface d'impression, nouvelle bobine.

### 5.1 Répétabilité du homing Z

```gcode
Z_REPEATABILITY
```

Dispersion attendue **< 0.01 mm**. Au-delà, c'est mécanique (switch mal fixé,
jeu dans le chariot Z) — inutile d'aller plus loin.

### 5.2 Plan du plateau

Fichier : **`gcode/first_layer_squares.gcode`** (~4 min, 0.8 g)

Cinq carrés de 25 mm : quatre coins + centre. Ils doivent avoir le **même aspect
et la même épaisseur**. Un carré translucide ou décollé face aux autres = défaut
de planéité → retour en P2, pas d'ajustement du Z offset.

### 5.3 Z offset fin

Fichier : **`gcode/first_layer_patch.gcode`** (~10 min, 1.6 g)

Patch plein de 80×80 mm en une couche. Ajuster **en cours d'impression** :

```gcode
SET_GCODE_OFFSET Z_ADJUST=-0.01 MOVE=1
```

| Aspect du patch | Correction |
|---|---|
| Sillons visibles entre les lignes | descendre (Z_ADJUST négatif) |
| Surface lisse, uniforme, mate | correct |
| Aspect translucide, bourrelets, buse qui racle | remonter |

Enregistrement une fois la valeur trouvée :

```gcode
Z_OFFSET_APPLY_ENDSTOP
SAVE_CONFIG
```

---

## P6 — Input shaper

**Quand :** courroies, rails, tête, moteurs, masse embarquée modifiée.

Prérequis : P2 validé, et **spreadCycle actif** (P1). Une mesure faite en
stealthChop est à jeter.

```gcode
ACCELEROMETER_QUERY
```

Doit renvoyer ≈ `(0, 0, 9800)` au repos. Sinon, corriger `axes_map` avant tout.

```gcode
SHAPER_BOTH BED=100
SAVE_CONFIG
```

> Sur une V0.1 destinée à l'ABS, mesurer **chambre chaude** : la dilatation des
> courroies décale les fréquences de plusieurs Hz.

Lecture des résultats :

- Fréquence **< 40 Hz** sur un axe → problème mécanique, retour en P2
- Pic large ou pics secondaires → jeu dans la transmission
- Archiver les `.csv` dans `docs/shaper/` avec la date, pour comparer dans le temps

Prendre le `max_accel` **recommandé par Klipper**, pas au-delà.

---

## P7 — Pressure Advance

**Quand :** hotend, extrudeur, changement de filament.

### Méthode rapide — lignes

Fichier : **`gcode/pa_line_test.gcode`** (~5 min, 0.2 g)

20 lignes à PA croissant de 0 à 0.095. Chaque ligne enchaîne 20 mm/s → 80 mm/s →
20 mm/s. **La ligne 1 est la plus proche du bord avant.**

Retenir la ligne dont la largeur reste la plus constante aux deux transitions de
vitesse : renflement en sortie de zone rapide = PA trop faible, creux = PA trop fort.

```
PA = 0.005 × (numéro_de_ligne − 1)
```

### Méthode fine — tour

```gcode
PA_TOWER START=0 FACTOR=0.005
PA_FROM_HEIGHT HEIGHT=12.4
```

### Valeurs de départ (direct drive court, type Mini SB / LGX Lite)

| Matière | PA |
|---|---|
| PLA | 0.03 – 0.05 |
| PETG | 0.05 – 0.08 |
| ABS / ASA | 0.03 – 0.05 |

> PA géré **côté Klipper** (`[extruder] pressure_advance` ou macro par matière).
> Laisser PA à **0 dans OrcaSlicer** pour ne pas cumuler les deux.

---

## P8 — Flow ratio

**Quand :** extrudeur, hotend, buse, nouveau filament ou nouvelle bobine.

Prérequis : P4 fait et flow remis à 1.0 dans le slicer.

Utiliser la calibration intégrée d'OrcaSlicer (*Calibration → Flow rate*), en deux
passes : grossière puis fine. Alternative manuelle : cube 30 mm mono-paroi en mode
vase, mesurer l'épaisseur au pied à coulisse sur les quatre faces.

```
flow = largeur_théorique / largeur_mesurée
```

Une bobine de la même référence peut demander un ajustement de ±0.02 — c'est
normal, surtout sur les bioplastiques.

---

## P9 — Débit volumétrique maximal

**Quand :** hotend, buse, nouveau filament.

OrcaSlicer *Calibration → Max volumetric speed*, ou extrusion en l'air à débit
croissant jusqu'au décrochage.

Ordres de grandeur en buse 0.4 :

| Hotend | mm³/s |
|---|---|
| V6 / clone | 8 – 11 |
| Dragon SF | 10 – 13 |
| Rapido UHF | 20+ |

Sur une V0.1, la limite pratique est le plus souvent l'**accélération**, pas le
débit. Reporter la valeur dans le profil filament OrcaSlicer.

```
vitesse_max = débit_max / (hauteur_couche × largeur_ligne)
```

---

## Validation

Après toute intervention notée ● en P5 ou plus :

1. **Cube 30 mm** — dimensions ±0.1 mm
2. **Voron Design Cube** — ghosting, qualité de coins
3. **Benchy** à vitesse nominale, puis à 1.5×
4. **Impression > 2 h** — dérive thermique, stabilité du bus CAN
   (`Timer too close`, `Lost communication with MCU`)

Test de stringing si besoin : **`gcode/retraction_tower.gcode`**, en modifiant
`[firmware_retraction]` entre deux essais.

---

## Fiche de valeurs

| Paramètre | Valeur | Date | Suite à |
|---|---|---|---|
| `run_current` X / Y / Z | | | |
| `hold_current` X / Y | | | |
| Tension courroies (Hz) | | | |
| PID buse (Kp/Ki/Kd) | | | |
| PID plateau (Kp/Ki/Kd) | | | |
| Montée plateau → 100 °C | | | |
| `rotation_distance` extrudeur | | | |
| Z offset | | | |
| Shaper X (type / Hz) | | | |
| Shaper Y (type / Hz) | | | |
| `max_accel` retenu | | | |
| PA — PLA | | | |
| PA — ABS | | | |
| Flow — PLA | | | |
| Flow — ABS | | | |
| Débit max (mm³/s) | | | |

---

## Journal

| Date | Intervention | Procédures refaites | Résultat |
|---|---|---|---|
| | | | |
