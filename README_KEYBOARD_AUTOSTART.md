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

## 2) Preparar el repositorio

Desde la carpeta del proyecto:

```bash
cd /ruta/a/brich
python3 btfpymake.py build
```

Verifica que exista:

- `btfpy.so`

## 3) Configurar `keyboard.txt`

Archivo:

- `keyboard.txt`

Puntos clave:

- El dispositivo local debe ser `node=1`.
- La direccion puede quedar en `ADDRESS = LOCAL` en la primera ejecucion.
- Si el script reporta que debes fijar direccion, usa la direccion indicada por el propio log.

## 4) Prueba manual (antes de systemd)

```bash
cd /ruta/a/brich
sudo python3 keyboard_autostart.py
```

Resultado esperado:

- El proceso queda escuchando conexiones BLE HID.
- F10 envia `"Hello"` + Enter al cliente.
- Si el cliente se desconecta, el proceso sigue vivo esperando reconexion.

Detener prueba manual con `Ctrl+C`.

## 5) Instalar como servicio automatico

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

## 6) Operar el proceso

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

## 7) Estabilidad y troubleshooting

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
