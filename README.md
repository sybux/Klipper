# Voron 0.1 — Guide de recalibration

Procédures de réglage à appliquer **après un changement matériel** ou en entretien
périodique. Part du principe que la machine tourne déjà : `printer.cfg` existe,
la liaison est fonctionnelle, les axes homent.

---

## Fiche machine

| Élément | Valeur |
|---|---|
| Volume mécanique | X **0 → 120**, Y **4 → 120**, plateau 120×120 full size |
| **Surface utile réelle** | **120 × 116** (origine Y = 4) — à reporter dans OrcaSlicer |
| Centre de la surface | (60, 62) |
| Bloc chauffant | 12×12 pleine surface (remplace un 10×10) |
| Surface d'impression | PEI |
| Topologie | **tout USB**, pas de CAN |
| MCU | mainboard + Klipper Expander + EBB36 Gen2 — les 3 sous Katapult |

### EBB36 Gen2 — points spécifiques

- MCU **STM32G0B1CBT6** (pas RP2040) → cible `STM32 / STM32G0B1` dans `menuconfig`, DFU `0483:df11`
- Le port USB-C est sur la **carte de breakout** (EBB USB Adapter), pas sur la carte tête
- **Jumper USB/CAN retiré en permanence** = mode USB
- Accéléromètre **LIS2DW** (pas ADXL345)
- 3 ports ventilateur indépendants, cavaliers de tension tous sur **24 V**

### Brochage EBB36 Gen2

| Fonction | Pin |
|---|---|
| Thermistance (TH) | `PA3` |
| Chauffe hotend (HE) | `PB4` |
| Endstop | `PA15` |
| Capteur filament (FIL) | `PD0` |
| FAN0 | `PD3` |
| FAN1 | `PA5` |
| FAN2 (+ tachy DET) | `PD2` (+ `PA4`) |
| RGB | `PC7` |
| PROBE / SERVOS | `PB8` / `PB5` |
| I2C SCL / SDA | `PA7` / `PA6` |
| LIS2DW CS | `PB1` |
| LIS2DW SPI | `spi2_PB2_PB11_PB10` |

> ⚠️ L'interface SERVOS est reliée directement au MCU, **sans protection**.

---

## Contenu du dépôt

```
.
├── README.md
├── config/
│   └── calibration.cfg          # macros + [bed_screws] — [include calibration.cfg]
├── gcode/
│   ├── first_layer_squares.gcode   # 5 zones : plan du plateau        (~4 min)
│   ├── first_layer_patch.gcode     # patch plein 80×80 : Z offset     (~10 min)
│   ├── pa_line_test.gcode          # 20 lignes PA 0→0.095             (~5 min)
│   └── retraction_tower.gcode      # 2 tours : stringing              (~15 min)
├── scripts/
│   ├── gen_calibration_gcode.py    # régénère les .gcode
│   └── v0_klipper_update.sh        # met à jour Klipper + flashe les 3 MCU
└── docs/
    └── shaper/                     # archives des .csv d'input shaper
```

Les `.gcode` sont **autonomes** : chauffe, homing, purge et test inclus, aucun
slicer nécessaire. Ils respectent la limite Y ≥ 4 et s'envoient directement dans
Mainsail/Fluidd.

Générés pour **PLA 215/60 °C, couche 0.20, largeur 0.45, 25 mm/s**. Pour l'ABS :

```bash
cd scripts
python3 gen_calibration_gcode.py --nozzle 255 --bed 100 --fan 0
```

---

## Matrice : qu'est-ce qui a changé ?

| Intervention | P1 Drivers | P2 Méca | P3 PID | P4 Extrudeur | P5 1ère couche | P6 Shaper | P7 PA | P8 Flow | P9 Débit |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Buse seule** (même Ø) | | | ● | | ● | | | | |
| **Buse Ø différent** | | | ● | | ● | | ● | ● | ● |
| **Hotend complet** | | | ● | ● | ● | | ● | ● | ● |
| **Extrudeur / galets** | | | | ● | ● | | ● | ● | |
| **Tête complète** | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| **Courroies A/B** | | ● | | | | ● | | | |
| **Rail / chariot X ou Y** | | ● | | | | ● | | | |
| **Moteur ou driver** | ● | | | | | ● | | | |
| **Plateau / bloc chauffant** | | ● | ● | | ● | | | | |
| **Thermistance** | | | ● | | | | | | |
| **Nouveau filament** | | | | | | | ● | ● | ● |
| **Nouvelle bobine, même réf.** | | | | | ● | | | ● | |
| **Mise à jour Klipper** | ● | | | | | | | | |
| **Entretien trimestriel** | ● | ● | | | ● | ● | | | |

---

## P1 — Contrôle des drivers

```gcode
TMC_STATUS
```

| Champ | Attendu | Si non conforme |
|---|---|---|
| lecture des registres | pas d'erreur `Unable to read` | mauvais `uart_pin` / `uart_address` |
| `GCONF` | `en_spreadcycle=1` sur X, Y | voir encadré |
| `cs_actual` | 16 à 28 | ajuster `run_current` / `sense_resistor` |
| `GSTAT` | `00000000` | reset ou sous-tension → alim / câblage |
| `version` | `0x21` | TMC2209 authentique |

> ⚠️ **Piège `stealthchop_threshold`**
> `stealthchop_threshold: 0` **active** stealthChop en permanence, il ne le
> désactive pas. Pour du spreadCycle pur, la ligne doit être **absente**.
> Une valeur basse (`1`) donne le meilleur compromis : silence à l'arrêt,
> spreadCycle dès 1 mm/s. C'est la config retenue sur X et Y (`tpwmthrs = 9375`).

Courant réel (TMC2209, `vsense=1`) :

```
Irms = (cs_actual + 1)/32 × 0.180 / (Rsense + 0.02) × 1/√2
```

**Contrôle du câblage moteur** — `ola`/`olb` ne sont exploitables qu'en mouvement
(`enn=0`, `stst` absent) :

```gcode
TMC_STATUS_MOVING AXIS=x
```

À l'arrêt ils sont systématiquement levés : normal, pas un défaut.

**Bruit spreadCycle** à l'arrêt = attendu. Pour l'atténuer : `hold_current: 0.4`
sur X et Y — **pas sur Z** (risque de descente du plateau).

---

## P2 — Mécanique

- [ ] Rails X/Y/Z : vis serrées en croix, aucun point dur
- [ ] Poulies folles libres ; poulies dentées serrées **sur le méplat**
- [ ] Tension A/B identique, ≈ **110 Hz**
- [ ] Deracking : desserrer les chariots A/B, portique en butée, resserrer
- [ ] Câble toolhead libre sur toute la course, aucune traction en butée

```gcode
AXES_LIMITS
G28
G1 Z30 F600
G1 X5 Y6 F1500
G1 X115 Y115 F1500
```

### Plan du plateau — 3 vis

La V0.1 est en montage **trois points** : un plan est défini par trois points,
une quatrième vis créerait une sur-contrainte qui voile le plateau.

Positions relevées (aplomb réel des vis) :

| Vis | Position |
|---|---|
| avant centre | 61, 6 |
| arrière gauche | 5, 116 |
| arrière droit | 115, 116 |

`calibration.cfg` utilise des points légèrement rentrés (61/8, 8/113, 112/113)
pour garder une marge de course. L'écart de 2–3 mm est sans conséquence sur la
mesure d'un plan.

```gcode
G28
BED_SCREWS_ADJUST
```

| Réponse | Effet |
|---|---|
| `ACCEPT` | vis correcte, passe à la suivante |
| `ADJUSTED` | vis tournée → Klipper refera un tour à la fin |
| `ABORT` | sort de la procédure |

> **Régler à température.** Un plateau réglé à froid se décale de plusieurs
> centièmes une fois chaud. Trempe de 15 min avant, buse également chaude
> (en essuyant la goutte avant chaque contact).

```gcode
HEAT_SOAK BED=60 MINUTES=15
```

En trois points, un seul tour propre suffit normalement. Trois `ADJUSTED`
consécutifs sans converger = quelque chose bouge ailleurs.

---

## P3 — PID

```gcode
PID_ALL HOTEND=245 BED=100
SAVE_CONFIG
```

- PID buse **ventilateur de couche coupé**, puis vérifier la stabilité à 100 %
- PID plateau **à la température de travail réelle** — avec le bloc 12×12
  pleine surface, l'inertie ne s'extrapole pas depuis 60 °C
- Noter le temps de montée à 100 °C : référence pour détecter une résistance
  qui faiblit

Si l'alimentation tire trop : `max_power: 0.8` sur `[heater_bed]`.

---

## P4 — Extrudeur (`rotation_distance`)

```gcode
E_TEST TEMP=215
```

Repère à 120 mm de l'entrée, 100 mm extrudés, mesure **au pied à coulisse** :

```gcode
E_CALC LEFT=19
```

- Critère : écart final **< 1 %**
- Un écart < 0.5 % est dans le bruit d'un réglet — ne corriger que si répétable

> Après correction, **remettre le flow ratio à 1.0 dans OrcaSlicer** avant P8,
> sinon la même erreur est compensée deux fois.

---

## P5 — Z offset et première couche

### 5.0 Nettoyer le PEI

Traces de doigts invisibles = adhérence détruite localement. Eau chaude +
liquide vaisselle, rinçage, puis IPA. **À faire avant toute conclusion sur
un défaut d'adhérence** — c'est la cause n°1 des faux diagnostics de Z offset.

### 5.1 Répétabilité du homing Z

```gcode
Z_REPEATABILITY
```

Dispersion attendue **< 0.01 mm**. Au-delà, c'est mécanique.

### 5.2 Plan du plateau

Fichier : **`gcode/first_layer_squares.gcode`** (~4 min, 0.8 g)

Cinq carrés de 25 mm. Ils doivent avoir le même aspect et la même épaisseur.

> **Un seul carré qui décolle n'est pas un problème de Z offset.** Un offset trop
> haut donne un résultat uniformément médiocre. Un défaut localisé = planéité
> (retour P2) ou plateau sale (5.0).

### 5.3 Z offset fin

Fichier : **`gcode/first_layer_patch.gcode`** (~10 min, 1.6 g)

Ajuster **en cours d'impression**, par pas de 0.02 mm :

```gcode
SET_GCODE_OFFSET Z_ADJUST=-0.02 MOVE=1
```

| Aspect | Correction |
|---|---|
| Sillons visibles, translucide à la lumière rasante | descendre (négatif) |
| Surface mate, uniforme, lignes fusionnées | correct |
| Bourrelets, aspect verni, buse qui racle | remonter (positif) |

Repère fiable : passer l'ongle en travers des lignes une fois refroidi — les
crêtes individuelles ne doivent pas se sentir.

```gcode
Z_OFFSET_APPLY_ENDSTOP
SAVE_CONFIG
```

> `Z_OFFSET_APPLY_ENDSTOP` (pas `_PROBE`) : la V0.1 n'a pas de sonde.

---

## P6 — Input shaper (LIS2DW)

```ini
[lis2dw]
cs_pin: EBB: PB1
spi_bus: spi2_PB2_PB11_PB10
axes_map: x,z,y

[resonance_tester]
accel_chip: lis2dw
probe_points: 60, 62, 30
```

### Vérification préalable

```gcode
ACCELEROMETER_QUERY
```

La **troisième** valeur doit être proche de **+9800**.

> **La carte est inclinée d'environ 30° dans son plan** sur la tête de la V0.1.
> La gravité se répartit donc entre le 1er et le 3e axe (typiquement ~5150 et
> ~8710) : c'est **normal et non corrigible** par `axes_map`, qui ne permute que
> par multiples de 90°. Sans incidence : Klipper somme les densités spectrales
> des trois axes, les pics restent détectés au bon endroit. Seule la lecture des
> graphes par axe devient moins directe.

### Mesure

```gcode
SHAPER_BOTH BED=100
SAVE_CONFIG
```

- Fréquence **< 40 Hz** sur un axe → problème mécanique, retour P2
- Un pic identique sur les deux axes = couplage géométrique, pas un défaut
- Archiver les `.csv` de `/tmp/` dans `docs/shaper/`

### max_accel

Les valeurs suggérées par Klipper (15000 / 17700) indiquent seulement jusqu'où
le shaper reste efficace — **pas** ce que la machine encaisse. Retenir **8000**,
déjà agressif pour une V0.1, qui sera de toute façon limitée par le débit
volumétrique avant l'accélération.

---

## P7 — Pressure Advance

Fichier : **`gcode/pa_line_test.gcode`** (~5 min, 0.2 g)

20 lignes, PA de 0 à 0.095. Chaque ligne : 20 → 80 → 20 mm/s.
**La ligne 1 est la plus proche du bord avant.**

```
PA = 0.005 × (numéro_de_ligne − 1)
```

Renflement en sortie de zone rapide = PA trop faible. Creux = PA trop fort.

Méthode fine :

```gcode
PA_TOWER START=0 FACTOR=0.005
PA_FROM_HEIGHT HEIGHT=12.4
```

| Matière | PA de départ |
|---|---|
| PLA | 0.03 – 0.05 |
| PETG | 0.05 – 0.08 |
| ABS / ASA | 0.03 – 0.05 |

> PA géré côté Klipper → laisser PA à **0 dans OrcaSlicer**.

---

## P8 — Flow ratio

Prérequis : P4 fait, flow remis à 1.0 dans le slicer.

OrcaSlicer *Calibration → Flow rate*, deux passes. Ou cube 30 mm mono-paroi en
mode vase, mesure au pied à coulisse sur les quatre faces.

```
flow = largeur_théorique / largeur_mesurée
```

Une bobine de même référence peut demander ±0.02 — normal, surtout sur les
bioplastiques (Polymaker Panchroma / PolyTerra : ~0.93–0.95).

---

## P9 — Débit volumétrique maximal

OrcaSlicer *Calibration → Max volumetric speed*, ou extrusion en l'air
à débit croissant.

| Hotend (buse 0.4) | mm³/s |
|---|---|
| V6 / clone | 8 – 11 |
| Dragon SF | 10 – 13 |
| Rapido UHF | 20+ |

```
vitesse_max = débit_max / (hauteur_couche × largeur_ligne)
```

---

## Validation

1. **Cube 30 mm** — ±0.1 mm
2. **Voron Design Cube** — ghosting, coins
3. **Benchy** nominal puis 1.5×
4. **Impression > 2 h** — dérive thermique, stabilité de la liaison USB
   (`Timer too close`, `Lost communication with MCU`)

Stringing : **`gcode/retraction_tower.gcode`**, en modifiant
`[firmware_retraction]` entre deux essais.

---

## Sections `printer.cfg` indispensables

Sans elles, le bouton Stop de Mainsail/Fluidd ne fait rien :

```ini
[virtual_sdcard]
path: ~/printer_data/gcodes

[pause_resume]
[display_status]
[respond]
[exclude_object]
```

`CANCEL_PRINT` doit **appeler** `PRINT_END`, jamais la remplacer :

```ini
[gcode_macro CANCEL_PRINT]
rename_existing: BASE_CANCEL_PRINT
gcode:
    TURN_OFF_HEATERS
    CLEAR_PAUSE
    SDCARD_RESET_FILE
    PRINT_END
    BASE_CANCEL_PRINT
```

Deux pièges dans `PRINT_END` :

- **Rétraction sur buse froide** → `Extrude below minimum temp`, la macro
  s'arrête net en laissant les chauffes allumées. Protéger par
  `{% if printer.extruder.can_extrude %}`.
- **Parking à `Y{max_y}`** = butée exacte → `Move out of range`.
  Utiliser `Y{max_y - 2}`.

## Ventilateurs — 3 ports séparés

Les deux latéraux sont sur des ports distincts (contacts JST SH trop petits pour
sertir deux fils). `M106` ne piloterait qu'un seul → override nécessaire :

```ini
[gcode_macro M106]
rename_existing: M106.1
gcode:
    {% set s = params.S|default(255)|float %}
    M106.1 S{s}
    SET_FAN_SPEED FAN=layer_right SPEED={(s / 255.0)|round(3)}

[gcode_macro M107]
rename_existing: M107.1
gcode:
    M107.1
    SET_FAN_SPEED FAN=layer_right SPEED=0
```

---

## Mise à jour du firmware

```bash
~/scripts/v0_klipper_update.sh
```

Met à jour le dépôt Klipper puis reflashe les trois MCU via Katapult (USB).
Renseigner les trois identifiants `/dev/serial/by-id/` en tête de script.
Tout étant en USB, il n'y a **pas de contrainte d'ordre** entre les cartes.

---

## Fiche de valeurs

| Paramètre | Valeur | Contexte | Date |
|---|---|---|---|
| `run_current` extrudeur | **0.650 A** | | 2026-09 |
| `microsteps` extrudeur | **16** | | |
| `rotation_distance` extrudeur | **4.637** | mesuré ; 4.683 si correction 1 % appliquée | |
| `stealthchop_threshold` X / Y | **1** | `tpwmthrs = 9375` | |
| `position_endstop` Z | **0.540** | PLA, plateau 60 °C, PEI propre | 2026-09-10 |
| Shaper X | **mzv @ 71.4 Hz** | 0.0 % vibrations — cage ouverte, PLA | 2026-09-10 |
| Shaper Y | **mzv @ 77.6 Hz** | 1.3 % vibrations — cage ouverte, PLA | 2026-09-10 |
| `max_accel` retenu | **8000** | | 2026-09-10 |
| `axes_map` LIS2DW | **x,z,y** | carte inclinée ~30° | 2026-09-10 |
| `run_current` X / Y / Z | | | |
| Tension courroies (Hz) | | | |
| PID buse | | | |
| PID plateau | | | à refaire (bloc 12×12) |
| Montée plateau → 100 °C | | | |
| PA — PLA | | | à faire (P7) |
| PA — ABS | | | |
| Flow — PLA | | | |
| Débit max (mm³/s) | | | |
| Shaper X / Y en ABS chaud | | chambre 50 °C | à faire |

---

## Journal

| Date | Intervention | Procédures | Résultat |
|---|---|---|---|
| 2026-09 | Bloc chauffant 10×10 → **12×12 pleine surface** (warping ABS sur grandes pièces) | P2, P3, P5 | PID plateau à refaire |
| 2026-09 | **Incident** : 24 V injecté sur CAN_H/CAN_L — câble toolhead non symétrique, inversé bout pour bout. EBB36 Gen1 **et** U2C détruits | — | remplacement complet |
| 2026-09 | Passage **EBB36 Gen2 + EBB USB Adapter**, abandon du CAN au profit de l'USB. U2C conservé en réserve | P1→P9 | topologie simplifiée |
| 2026-09-10 | `axes_map` LIS2DW déterminé par analyse du CSV (`x,z,y`) | P6 | validé |
| 2026-09-10 | Z offset | P5 | `position_endstop: 0.540` |
| 2026-09-10 | Input shaper | P6 | X mzv 71.4 Hz / Y mzv 77.6 Hz |

### Leçons

- **Câble toolhead non symétrique** : marquer les deux extrémités au ruban dès
  la réception. Une inversion sur un bus CAN détruit **tous** les nœuds.
- Le câble fourni avec la Gen2 est détrompé — la classe de panne disparaît.
- **PEI sale** = adhérence détruite localement, symptôme trompeur qui imite un
  défaut de Z offset ou de planéité.
- **Régler le plateau à froid puis imprimer à chaud** ne fonctionne pas.
- Le Klipper Expander **a bien un MCU** et se flashe comme les autres.
