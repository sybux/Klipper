# 🟦 Installation et intégration du Luxafor Flag avec Klipper via API HTTP

Ce guide permet d'utiliser un Luxafor Flag comme indicateur lumineux pour une imprimante 3D sous Klipper. Il inclut un serveur API local, un script systemd, et des macros Klipper personnalisées.

---

## ✅ Matériel requis

- Luxafor Flag USB
- Raspberry Pi ou serveur Linux avec Klipper + Moonraker (Mainsail/Fluidd/OctoPrint)

---

## 🔌 1. Connexion du Luxafor Flag avec accès non-root

### 1.1. Identifier le périphérique

Branche le Luxafor Flag puis exécute :

```bash
lsusb
```

Repère une ligne comme :

```
ID 04d8:f372 Microchip Technology, Inc.
```

### 1.2. Créer une règle `udev`

Crée le fichier suivant :

```bash
sudo nano /etc/udev/rules.d/99-luxafor.rules
```

Et ajoute :

```text
SUBSYSTEM=="usb", ATTR{idVendor}=="04d8", ATTR{idProduct}=="f372", MODE="0666", GROUP="plugdev"
```

Recharge les règles :

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Débranche et rebranche le Luxafor.

### 1.3. Vérifier les droits

Assure-toi que l'utilisateur courant est dans le groupe `plugdev` :

```bash
groups
```

Sinon, ajoute-le :

```bash
sudo usermod -aG plugdev $USER
```

---

##⚙️ 2. API HTTP pour piloter le Flag

### 2.1. Installer les dépendances

```bash
pip install flask hid
```

### 2.2. Créer le dossier et script

```bash
mkdir -p /home/pi/luxafor
nano /home/pi/luxafor/luxafor_api.py
```

Colle le contenu du script `luxafor_api.py`.

Rends-le exécutable :

```bash
chmod +x /home/pi/luxafor/luxafor_api.py
```

---

## 🚀 3. Service systemd

### 3.1. Créer le fichier `systemd`

```bash
sudo nano /etc/systemd/system/luxafor.service
```

Colle :

```ini
[Unit]
Description=Luxafor API Server
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/luxafor/luxafor_api.py
WorkingDirectory=/home/pi/luxafor
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

### 3.2. Activer et démarrer

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable luxafor.service
sudo systemctl start luxafor.service
```

---

## 🧩 4. Macros Klipper (exemple)

Ajoute dans `printer.cfg` :

```ini
[gcode_macro LUXAFOR_DISPO]
gcode:
    {% shell "curl -s -X POST http://localhost:5000/set_color -d 'color=green&mode=static'" %}

[gcode_macro LUXAFOR_PRINTING]
gcode:
    {% shell "curl -s -X POST http://localhost:5000/set_color -d 'color=purple&mode=static'" %}

[gcode_macro LUXAFOR_EXCLUDED]
gcode:
    {% shell "curl -s -X POST http://localhost:5000/set_color -d 'color=orange&mode=static'" %}

[gcode_macro LUXAFOR_ERROR]
gcode:
    {% shell "curl -s -X POST http://localhost:5000/set_color -d 'color=red&mode=blink'" %}
```

---

## ✅ Exemples d’utilisation

```bash
curl -X POST http://localhost:5000/set_color -d "color=blue&mode=blink"
curl -X POST http://localhost:5000/set_color -d "color=off"
```

---

## 📌 Remarques

- Le clignotement s’arrête dès qu’un nouvel ordre est envoyé.
- Tu peux adapter les couleurs, vitesses, etc. dans le script Python.
