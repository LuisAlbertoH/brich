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

### Flujo recomendado si hay un dispositivo conectado durante pruebas

No actualices con una instancia activa del teclado BLE. Primero desconecta y libera el adaptador.

Opcion A (manual):

```bash
cd /home/pi/brich
sudo systemctl stop brich-keyboard.service
sudo pkill -f "python3 .*keyboard_autostart.py" || true
sudo rfkill unblock bluetooth || true
sudo hciconfig hci0 down || true
sudo hciconfig hci0 up || true
git fetch origin
git pull --ff-only origin "$(git branch --show-current)"
python3 btfpymake.py build
sudo systemctl start brich-keyboard.service
```

Opcion B (automatizada, recomendada):

```bash
cd /home/pi/brich
chmod +x deploy/update_keyboard_from_github.sh
sudo ./deploy/update_keyboard_from_github.sh
```

Ese script:
- detiene `brich-keyboard.service` (esto desconecta el cliente BLE),
- detiene `brich-keyboard-web.service` si esta instalado,
- mata procesos manuales colgados,
- reinicia el adaptador Bluetooth,
- actualiza el branch actual,
- recompila `btfpy.so`,
- vuelve a iniciar los servicios.

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

Importante:
- No ejecutes `sudo python3 keyboard_autostart.py` si el servicio ya esta activo.
- El script ahora usa un lock de instancia para evitar doble ejecucion.

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

## 10) Interfaz web local para celular

La interfaz web corre como un cliente separado. No usa Bluetooth directo: solo escribe comandos a la misma cola que usa `keyboard_ctl.py`.

Archivos:

- `keyboard_web.py`
- `webui/index.html`
- `webui/style.css`
- `webui/app.js`
- `deploy/install_keyboard_web_service.sh`

Instalacion:

```bash
cd /home/pi/brich
chmod +x deploy/install_keyboard_web_service.sh
sudo ./deploy/install_keyboard_web_service.sh
```

Ver estado:

```bash
sudo systemctl status brich-keyboard-web.service
sudo journalctl -u brich-keyboard-web.service -f
```

Acceso desde el celular:

1. Conecta el celular a la misma red local que la Raspberry.
2. Obten la IP de la Pi:

```bash
hostname -I
```

3. Abre en el navegador del celular:

```text
http://IP_DE_LA_RASPBERRY:8080
```

Ejemplo:

```text
http://192.168.1.35:8080
```

La UI incluye:

- envio de texto,
- flechas y teclas basicas,
- atajos frecuentes,
- combos personalizados,
- botones de macros definidos en `keyboard_macros.json`.

Importante:

- La web UI y `keyboard_ctl.py` pueden coexistir.
- El backend BLE sigue siendo `brich-keyboard.service`.
- Si el teclado BLE no esta conectado, la web sigue aceptando comandos y los deja en cola.

## 11) Estabilidad y troubleshooting

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

4. Si la interfaz web no abre en el celular:
- confirma que el servicio web este activo:

```bash
sudo systemctl status brich-keyboard-web.service
```

- revisa el puerto:

```bash
sudo ss -ltnp | grep 8080
```

- verifica firewall o aislamiento Wi-Fi en tu red local.
