#!/usr/bin/env python3
"""
Generateur de G-code de calibration pour Voron 0.1
(volume 120 x 120, Y limite a position_min = 4)

Produit des fichiers autonomes : chauffe, homing, ligne de purge et
sequence de test. Aucun slicer necessaire.

Usage :
    python3 gen_calibration_gcode.py                 # tout, valeurs PLA
    python3 gen_calibration_gcode.py --nozzle 255 --bed 100   # ABS
    python3 gen_calibration_gcode.py --only first_layer_patch
"""

import argparse
import math
import os

FILAMENT_D = 1.75
FILAMENT_AREA = math.pi * (FILAMENT_D / 2) ** 2  # 2.4053 mm^2


def e_per_mm(width, height):
    """Longueur de filament (mm) a pousser par mm de deplacement."""
    return (width * height) / FILAMENT_AREA


class GcodeWriter:
    def __init__(self, title, cfg):
        self.lines = []
        self.cfg = cfg
        self.title = title

    def raw(self, txt):
        self.lines.append(txt)

    def comment(self, txt):
        self.lines.append("; " + txt)

    def header(self, extra_notes=()):
        c = self.cfg
        self.raw(f"; ==== {self.title} ====")
        self.raw("; Genere par gen_calibration_gcode.py")
        self.raw(f"; buse {c.nozzle} C / plateau {c.bed} C")
        self.raw(f"; couche {c.height} mm / largeur {c.width} mm")
        for n in extra_notes:
            self.raw("; " + n)
        self.raw("")
        self.raw("M104 S{} ; prechauffe buse (sans attendre)".format(c.nozzle - 40))
        self.raw(f"M190 S{c.bed} ; plateau et attente")
        self.raw("G28")
        self.raw(f"M109 S{c.nozzle} ; buse et attente")
        self.raw("G90 ; positions absolues")
        self.raw("M83 ; extrusion relative")
        self.raw("G92 E0")
        self.raw(f"M106 S{int(c.fan * 255 / 100)} ; ventilateur de couche {c.fan}%")
        self.raw("")

    def purge_line(self):
        """Ligne de purge le long du bord avant, au-dessus de Y_MIN."""
        c = self.cfg
        epm = e_per_mm(c.width * 1.4, c.height)
        y = c.y_min + 2
        self.comment("--- ligne de purge ---")
        self.raw(f"G1 Z{c.height + 2:.2f} F900")
        self.raw(f"G1 X{c.x_min + 5:.2f} Y{y:.2f} F6000")
        self.raw(f"G1 Z{c.height:.3f} F600")
        self.raw("G1 E4 F300 ; amorcage")
        length = 100
        self.raw(
            f"G1 X{c.x_min + 5 + length:.2f} Y{y:.2f} "
            f"E{epm * length:.4f} F1200"
        )
        self.raw(f"G1 Y{y + c.width:.2f} E{epm * c.width:.4f} F1200")
        self.raw(
            f"G1 X{c.x_min + 5:.2f} Y{y + c.width:.2f} "
            f"E{epm * length:.4f} F1500"
        )
        self.raw("G1 E-0.6 F2100 ; retract")
        self.raw(f"G1 Z{c.height + 3:.2f} F900")
        self.raw("G92 E0")
        self.raw("")

    def footer(self):
        self.comment("--- fin ---")
        self.raw("G1 E-2 F2100")
        self.raw("G1 Z40 F900 ; degage le plateau")
        self.raw("M104 S0")
        self.raw("M140 S0")
        self.raw("M107")
        self.raw("M84")
        self.raw("")

    def save(self, path):
        with open(path, "w") as f:
            f.write("\n".join(self.lines) + "\n")
        n = sum(1 for l in self.lines if l and not l.startswith(";"))
        print(f"  {os.path.basename(path):32s} {n:5d} lignes de mouvement")


def rect_outline(g, x0, y0, x1, y1, epm, feed):
    """Contour rectangulaire ferme, extrusion relative."""
    pts = [(x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    cx, cy = x0, y0
    for (px, py) in pts:
        d = math.hypot(px - cx, py - cy)
        g.raw(f"G1 X{px:.3f} Y{py:.3f} E{epm * d:.4f} F{feed}")
        cx, cy = px, py


def fill_rect(g, x0, y0, x1, y1, epm, feed, spacing, inset=0.0):
    """Remplissage serpentin selon X, lignes espacees de `spacing`."""
    x0 += inset
    x1 -= inset
    y0 += inset
    y1 -= inset
    n = max(1, int(round((y1 - y0) / spacing)))
    step = (y1 - y0) / n
    y = y0
    left = True
    for i in range(n + 1):
        xa, xb = (x0, x1) if left else (x1, x0)
        if i == 0:
            g.raw(f"G1 X{xa:.3f} Y{y:.3f} F6000")
        else:
            g.raw(f"G1 Y{y:.3f} E{epm * step:.4f} F{feed}")
        g.raw(f"G1 X{xb:.3f} E{epm * abs(xb - xa):.4f} F{feed}")
        left = not left
        y += step


# ---------------------------------------------------------------- tests


def gen_first_layer_squares(cfg):
    """5 carres (4 coins + centre) : controle du plan du plateau."""
    g = GcodeWriter("TEST PREMIERE COUCHE - 5 zones", cfg)
    g.header(
        [
            "Objectif : verifier le Z offset ET le plan du plateau.",
            "Les 5 carres doivent avoir le meme aspect et la meme epaisseur.",
        ]
    )
    g.raw("SET_PRESSURE_ADVANCE ADVANCE=0 ; PA neutralise pour ce test")
    g.raw("")
    g.purge_line()

    epm = e_per_mm(cfg.width, cfg.height)
    feed = int(cfg.speed * 60)
    feed_peri = int(cfg.speed * 0.8 * 60)
    size = 25.0
    margin = 6.0

    x0, x1 = cfg.x_min + margin, cfg.x_max - margin
    y0, y1 = cfg.y_min + margin, cfg.y_max - margin
    cx = (cfg.x_min + cfg.x_max) / 2
    cy = (cfg.y_min + cfg.y_max) / 2

    zones = [
        ("avant gauche", x0, y0),
        ("avant droit", x1 - size, y0),
        ("arriere droit", x1 - size, y1 - size),
        ("arriere gauche", x0, y1 - size),
        ("centre", cx - size / 2, cy - size / 2),
    ]

    g.raw(f"G1 Z{cfg.height:.3f} F600")
    for name, sx, sy in zones:
        g.comment(f"--- carre {name} ---")
        g.raw(f"G1 X{sx:.3f} Y{sy:.3f} F6000")
        g.raw("G1 E0.6 F300")
        rect_outline(g, sx, sy, sx + size, sy + size, epm, feed_peri)
        fill_rect(
            g,
            sx,
            sy,
            sx + size,
            sy + size,
            epm,
            feed,
            cfg.width,
            inset=cfg.width,
        )
        g.raw("G1 E-0.6 F2100")
        g.raw(f"G1 Z{cfg.height + 1:.2f} F900")
        g.raw(f"G1 Z{cfg.height:.3f} F900")
        g.raw("")

    g.footer()
    return g


def gen_first_layer_patch(cfg):
    """Patch plein : qualite de surface de la premiere couche."""
    g = GcodeWriter("TEST PREMIERE COUCHE - patch plein", cfg)
    size = cfg.patch
    g.header(
        [
            f"Patch plein {size:.0f} x {size:.0f} mm, une seule couche.",
            "Surface lisse et sans creux entre les lignes = Z offset correct.",
            "Duree indicative : 8-12 min.",
        ]
    )
    g.raw("SET_PRESSURE_ADVANCE ADVANCE=0")
    g.raw("")
    g.purge_line()

    epm = e_per_mm(cfg.width, cfg.height)
    feed = int(cfg.speed * 60)
    feed_peri = int(cfg.speed * 0.8 * 60)

    cx = (cfg.x_min + cfg.x_max) / 2
    cy = (cfg.y_min + cfg.y_max) / 2
    x0, y0 = cx - size / 2, cy - size / 2
    x1, y1 = cx + size / 2, cy + size / 2

    g.comment("--- patch ---")
    g.raw(f"G1 X{x0:.3f} Y{y0:.3f} F6000")
    g.raw(f"G1 Z{cfg.height:.3f} F600")
    g.raw("G1 E0.8 F300")
    rect_outline(g, x0, y0, x1, y1, epm, feed_peri)
    rect_outline(
        g,
        x0 + cfg.width,
        y0 + cfg.width,
        x1 - cfg.width,
        y1 - cfg.width,
        epm,
        feed_peri,
    )
    fill_rect(g, x0, y0, x1, y1, epm, feed, cfg.width, inset=cfg.width * 2)
    g.footer()
    return g


def gen_pa_line_test(cfg):
    """Lignes lent-rapide-lent a PA croissant (methode ligne)."""
    g = GcodeWriter("TEST PRESSURE ADVANCE - lignes", cfg)
    pa_start, pa_step = cfg.pa_start, cfg.pa_step
    slow, fast = cfg.pa_slow, cfg.pa_fast

    n_lines = 20
    spacing = 4.0
    seg_slow, seg_fast = 20.0, 40.0
    total = seg_slow * 2 + seg_fast

    g.header(
        [
            f"PA de {pa_start:.3f} a {pa_start + pa_step * (n_lines - 1):.3f}"
            f" (pas {pa_step:.3f})",
            f"Chaque ligne : {slow} mm/s -> {fast} mm/s -> {slow} mm/s",
            "Ligne 1 = la plus proche de l'AVANT du plateau.",
            "Choisir la ligne dont la largeur est la plus constante",
            "aux deux transitions de vitesse.",
        ]
    )
    g.purge_line()

    epm = e_per_mm(cfg.width, cfg.height)
    cx = (cfg.x_min + cfg.x_max) / 2
    x_start = cx - total / 2
    y_first = cfg.y_min + 12

    g.raw(f"G1 Z{cfg.height:.3f} F600")
    for i in range(n_lines):
        pa = pa_start + i * pa_step
        y = y_first + i * spacing
        g.comment(f"--- ligne {i + 1:02d} : PA = {pa:.4f} ---")
        g.raw(f"SET_PRESSURE_ADVANCE ADVANCE={pa:.4f}")
        g.raw(f"G1 X{x_start:.3f} Y{y:.3f} F6000")
        g.raw("G1 E0.7 F300 ; amorcage")
        x = x_start
        for length, spd in (
            (seg_slow, slow),
            (seg_fast, fast),
            (seg_slow, slow),
        ):
            x += length
            g.raw(f"G1 X{x:.3f} E{epm * length:.4f} F{int(spd * 60)}")
        g.raw("G1 E-0.7 F2100")
        g.raw(f"G1 Z{cfg.height + 2:.2f} F900")
        g.raw(f"G1 Z{cfg.height:.3f} F900")

    g.raw("")
    g.comment("PA remis a 0 : relancer un FIRMWARE_RESTART ou")
    g.comment("appliquer la valeur retenue dans printer.cfg")
    g.raw("SET_PRESSURE_ADVANCE ADVANCE=0")
    g.footer()
    return g


def gen_retraction_tower(cfg):
    """Deux tours fines : mise en evidence du stringing."""
    g = GcodeWriter("TEST RETRACTION - 2 tours", cfg)
    height_mm = cfg.retract_height
    layers = int(height_mm / cfg.height)
    gap = 30.0
    side = 8.0

    g.header(
        [
            f"Deux tours de {side:.0f} mm espacees de {gap:.0f} mm,"
            f" hauteur {height_mm:.0f} mm.",
            "Le fil entre les tours revele le stringing.",
            "Modifier retract_length / retract_speed dans"
            " [firmware_retraction] entre deux essais.",
        ]
    )
    g.purge_line()

    cx = (cfg.x_min + cfg.x_max) / 2
    cy = (cfg.y_min + cfg.y_max) / 2
    towers = [
        (cx - gap / 2 - side / 2, cy - side / 2),
        (cx + gap / 2 - side / 2, cy - side / 2),
    ]
    feed = int(cfg.speed * 60)

    for layer in range(layers):
        z = cfg.height * (layer + 1)
        h = cfg.height
        epm = e_per_mm(cfg.width, h)
        g.comment(f"--- couche {layer + 1} / {layers} (Z={z:.2f}) ---")
        g.raw(f"G1 Z{z:.3f} F900")
        for (sx, sy) in towers:
            g.raw("G10 ; unretract gere par firmware_retraction")
            g.raw(f"G1 X{sx:.3f} Y{sy:.3f} F9000")
            g.raw("G11")
            for k in range(2):
                o = k * cfg.width
                rect_outline(
                    g, sx + o, sy + o, sx + side - o, sy + side - o, epm, feed
                )
            g.raw("G10")
    g.footer()
    return g


TESTS = {
    "first_layer_squares": gen_first_layer_squares,
    "first_layer_patch": gen_first_layer_patch,
    "pa_line_test": gen_pa_line_test,
    "retraction_tower": gen_retraction_tower,
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--nozzle", type=int, default=215, help="temp buse (C)")
    p.add_argument("--bed", type=int, default=60, help="temp plateau (C)")
    p.add_argument("--fan", type=int, default=40, help="ventilo couche (%%)")
    p.add_argument("--height", type=float, default=0.20, help="hauteur couche")
    p.add_argument("--width", type=float, default=0.45, help="largeur ligne")
    p.add_argument("--speed", type=float, default=25.0, help="vitesse (mm/s)")
    p.add_argument("--patch", type=float, default=80.0, help="cote du patch")
    p.add_argument("--x-min", type=float, default=0.0)
    p.add_argument("--x-max", type=float, default=120.0)
    p.add_argument("--y-min", type=float, default=4.0)
    p.add_argument("--y-max", type=float, default=120.0)
    p.add_argument("--pa-start", type=float, default=0.0)
    p.add_argument("--pa-step", type=float, default=0.005)
    p.add_argument("--pa-slow", type=float, default=20.0)
    p.add_argument("--pa-fast", type=float, default=80.0)
    p.add_argument("--retract-height", type=float, default=25.0)
    p.add_argument("--outdir", default="../gcode")
    p.add_argument("--only", default=None, choices=list(TESTS))
    cfg = p.parse_args()

    outdir = os.path.abspath(cfg.outdir)
    os.makedirs(outdir, exist_ok=True)
    names = [cfg.only] if cfg.only else list(TESTS)
    print(f"Generation dans {outdir}")
    for name in names:
        g = TESTS[name](cfg)
        g.save(os.path.join(outdir, name + ".gcode"))


if __name__ == "__main__":
    main()
