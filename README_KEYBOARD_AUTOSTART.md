# Keyboard HID autostart (Raspberry Pi Zero 2W)

Esta guia despliega un proceso BLE HID keyboard que:

- arranca automaticamente al encender la Raspberry Pi,
- se reinicia solo si el proceso cae,
- mantiene reconexion estable sin salir en cada desconexion del cliente.

## 1) Requisitos

En la Raspberry Pi (Raspberry Pi OS):

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-dev python3-setuptools
```

Si usas teclado local fisico, configura layout GB (requisito del ejemplo de btferret):

```bash
sudo sed -i 's/^XKBLAYOUT=.*/XKBLAYOUT="gb"/' /etc/default/keyboard
sudo setupcon -k || true
```

## 2) Actualizar repositorio desde GitHub (en la Raspberry)

Esta guia asume que ya tienes el repo clonado en la Pi.

Ruta recomendada:

- `/home/pi/brich`

Actualizar a la ultima version del branch actual:

```bash
cd /home/pi/brich
git branch --show-current
git fetch origin
git pull --ff-only origin "$(git branch --show-current)"
```

Verificar estado limpio despues del pull:

```bash
git status
```

Si `git pull` falla por cambios locales, usa este flujo:

```bash
cd /home/pi/brich
git stash push -m "wip-before-keyboard-update"
git pull --ff-only origin "$(git branch --show-current)"
git stash pop
```

## 3) Preparar el repositorio

Desde la carpeta del proyecto:

```bash
cd /ruta/a/brich
python3 btfpymake.py build
```

Verifica que exista:

- `btfpy.so`

## 4) Configurar `keyboard.txt`

Archivo:

- `keyboard.txt`

Puntos clave:

- El dispositivo local debe ser `node=1`.
- La direccion puede quedar en `ADDRESS = LOCAL` en la primera ejecucion.
- Si el script reporta que debes fijar direccion, usa la direccion indicada por el propio log.

## 5) Prueba manual (antes de systemd)

```bash
cd /ruta/a/brich
sudo python3 keyboard_autostart.py
```

Resultado esperado:

- El proceso queda escuchando conexiones BLE HID.
- F10 envia `"Hello"` + Enter al cliente.
- Si el cliente se desconecta, el proceso sigue vivo esperando reconexion.

Detener prueba manual con `Ctrl+C`.

## 6) Instalar como servicio automatico

Archivo instalador:

- `deploy/install_keyboard_service.sh`

Ejecuta:

```bash
cd /ruta/a/brich
chmod +x deploy/install_keyboard_service.sh
sudo ./deploy/install_keyboard_service.sh
```

Esto crea e inicia:

- `/etc/systemd/system/brich-keyboard.service`

## 7) Operar el proceso

Estado:

```bash
sudo systemctl status brich-keyboard.service
```

Logs en vivo:

```bash
sudo journalctl -u brich-keyboard.service -f
```

Reiniciar:

```bash
sudo systemctl restart brich-keyboard.service
```

Detener:

```bash
sudo systemctl stop brich-keyboard.service
```

Deshabilitar arranque automatico:

```bash
sudo systemctl disable --now brich-keyboard.service
```

## 8) Operacion remota desde consola (SSH)

Puedes enviar teclas al cliente BLE conectado sin teclado fisico local.

Archivo de control:

- `keyboard_ctl.py`

Ejemplos:

```bash
cd /ruta/a/brich
python3 keyboard_ctl.py text "hola mundo"
python3 keyboard_ctl.py key ENTER
python3 keyboard_ctl.py combo "CTRL+ALT+T"
python3 keyboard_ctl.py combo "GUI+R"
```

Notas:

- `combo` soporta modificadores: `CTRL`, `SHIFT`, `ALT`, `ALTGR`, `GUI` (`WIN`/`CMD`).
- `key` soporta teclas como `ENTER`, `TAB`, `ESC`, `F1..F12`, flechas, etc.
- Si no hay cliente BLE conectado, los comandos quedan en cola y se ejecutan al conectar.

## 9) Macros personalizadas (automatizaciones)

Archivo:

- `keyboard_macros.json`

Listar macros:

```bash
python3 keyboard_ctl.py list-macros
```

Ejecutar macro:

```bash
python3 keyboard_ctl.py macro open_terminal_linux
python3 keyboard_ctl.py macro open_browser_example
```

Formato de macro:

```json
{
  "mi_macro": [
    "COMBO CTRL+L",
    "TEXT https://mi-sitio.com",
    "KEY ENTER",
    "DELAY 300",
    "COMBO CTRL+TAB"
  ]
}
```

## 10) Estabilidad y troubleshooting

1. Si ves errores tipo "Attempting Classic connection" o "MIC failure":
- elimina el emparejamiento HID viejo en el telefono/PC.
- vuelve a emparejar.
- si persiste, cambia la direccion aleatoria fija en `keyboard_autostart.py` (variable `RANDADD`) para forzar nueva identidad BLE.

2. Si el enlace tarda en completar:
- sube `BTF_LE_WAIT_MS` en el servicio (`/etc/systemd/system/brich-keyboard.service`), por ejemplo `40000`.
- aplica cambios:

```bash
sudo systemctl daemon-reload
sudo systemctl restart brich-keyboard.service
```

3. Si quieres modo dedicado BLE (sin otros dispositivos Bluetooth locales):
- opcionalmente deten `bluetooth.service`:

```bash
sudo systemctl stop bluetooth
```

Nota: al monopolizar el adaptador BLE para HID, otros usos Bluetooth locales pueden dejar de funcionar.
