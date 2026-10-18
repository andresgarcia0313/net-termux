# net-termux

Mira desde el teléfono cómo está tu red: la señal Wi-Fi, si hay Internet, qué equipos
están conectados y cómo va tu red de Tailscale. Corre en **Termux para Android, sin root**.

```text
$ net status

Red
● Wi-Fi · 5 GHz · señal excelente (-39 dBm) · 433 Mbps
  Este teléfono 192.168.1.108 · router .1 · 9 ms
● Internet · 31 ms · DNS 87 ms
  Mi Proveedor · Bogotá · 203.0.113.45
● Tailscale · 100.64.0.10

Equipos · 6 en 192.168.1.0/24
● router         .1    Router           9 ms  web https
● nas            .20   Linux            7 ms  ssh web smb
● portatil       .31   Windows         14 ms  ssh smb
● tele-sala      .42   TV/Chromecast   22 ms  cast
● sin nombre     .57   Linux/Android   69 ms
◆ este teléfono  .108  Android

Medido en 4,7 s
```

```text
$ tailscale status

Tailscale · ejemplo.ts.net
◆ Este teléfono · mi-telefono · 100.64.0.10

Equipos · 3 de 4 en línea
● nas         100.64.0.20   Linux    16 ms
● portatil    100.64.0.31   Windows   8 ms
◐ servidor    100.64.0.40   Linux    22 ms
  la clave vence en 12 días
○ tablet      100.64.0.55   Android  desconectado hace 2 meses

Datos vistos desde nas (ahora) · latencia medida desde aquí
```

## Instalar

En Termux, un solo comando:

```bash
curl -fsSL https://raw.githubusercontent.com/andresgarcia0313/net-termux/main/install.sh | bash
```

Instala lo que falte (`python`, `git`, `openssh`, `termux-api`), descarga el proyecto en
`~/.local/share/net-termux` y deja los comandos en `~/.local/bin`. Para ver la señal Wi-Fi
instala también la app **Termux:API** (F-Droid o Google Play), de la misma tienda que Termux.

Volver a correr el comando **actualiza**. Para **quitarlo**:

```bash
curl -fsSL https://raw.githubusercontent.com/andresgarcia0313/net-termux/main/install.sh | bash -s -- --uninstall
```

## Comandos

| Comando | Qué hace |
|---|---|
| `net status` | Wi-Fi, router, Internet (latencia, DNS, proveedor, IP pública), Tailscale y equipos de la red |
| `net status --json` | Lo mismo en JSON, para otros programas |
| `tailscale status` | Equipos de tu tailnet, en línea o no, con latencia medida desde el teléfono |
| `tailscale status -v` | Además, el tráfico de cada equipo con el equipo que respondió |
| `tailscale status --json` | El JSON original de `tailscale status --json` |
| `tailscale ip` | La IP de Tailscale del teléfono |
| `net tailscale` | Igual que `tailscale status` |
| `net <otra cosa>` | Pasa al `net` de Samba si lo tienes instalado |

### Cómo leer los símbolos

El estado nunca va solo en color: cada símbolo tiene forma propia y va con una palabra.

| Símbolo | Significa |
|---|---|
| ● | Responde bien |
| ◐ | Responde, pero pide atención (lento o clave por vencer) |
| ✕ | Falla o clave vencida |
| ○ | Apagado, desconectado o sin respuesta al ping |
| ◆ | Este teléfono |

## Configurar `tailscale status`

La app de Tailscale para Android no trae línea de comandos. Por eso `tailscale status`
le pide el estado, por SSH, a un equipo tuyo que sí tenga el CLI (un servidor, un
portátil, una Raspberry Pi) y mide la latencia desde el teléfono.

1. Asegúrate de entrar sin contraseña: `ssh mi-servidor tailscale status` debe funcionar
   (con clave SSH, `ssh-copy-id mi-servidor`).
2. Escribe el nombre en la configuración, uno por línea, en orden de preferencia:

```bash
mkdir -p ~/.config/net-termux
printf 'mi-servidor\nmi-portatil\n' > ~/.config/net-termux/tailscale-hosts
```

Si ninguno contesta, se muestra la última copia guardada (`~/.cache/net-termux/`) con su
antigüedad. También puedes usar la variable `NET_TERMUX_TS_HOSTS="mi-servidor mi-portatil"`.

## Cómo funciona sin root

Android no deja leer la tabla ARP ni la de rutas, así que no hay MAC ni fabricante. En su lugar:

- **Equipos:** ping ICMP por socket de datagrama (Android lo permite sin root) leyendo el TTL,
  y conexión TCP a 7 puertos (22, 80, 443, 445, 554, 8009, 62078): un rechazo también prueba
  que el equipo existe. La latencia se vuelve a medir en calma para que sea real.
- **Nombres:** Tailscale, mDNS (Avahi, Bonjour), DNS del router y NetBIOS (Windows, Samba).
- **Tipo de equipo:** por Tailscale, por los puertos abiertos y por el TTL.
- **Router:** el `.1` o el `.254` que responde DNS.
- **Proveedor e IP pública:** una consulta a `ipinfo.io`. Es la única salida a Internet.
- **Sin procesos en lote:** todo corre en hilos de un solo proceso; Android cierra Termux
  cuando una app crea demasiados procesos.

Solo barre la red `/24` del Wi-Fi: no escanea redes ajenas ni equipos fuera de tu LAN.
Úsalo en redes tuyas o donde tengas permiso.

## Diseño

Sigue las pautas de interfaz de Apple llevadas a la terminal: lo importante primero
(la red y luego los equipos), jerarquía por peso del texto y no por más columnas, estado
por forma, color y palabra, ancho que se adapta a la pantalla del teléfono, algo visible
mientras mide y sin color cuando la salida no es una terminal o existe `NO_COLOR`.

## Desarrollo

```bash
git clone https://github.com/andresgarcia0313/net-termux && cd net-termux
pkg install python-pip && pip install pytest
python3 -m pytest -q tests
```

Módulos en `lib/netkit/`: `probe` (ICMP y TCP), `mdns`, `names`, `link` (Wi-Fi, router,
Internet), `tsdata` (estado de Tailscale), `gather`, `netstatus`, `tsstatus`, `ui` y `fmt`.

Hermano para Linux: [net-status](https://github.com/andresgarcia0313/net-status).

## In English

`net status` and `tailscale status` for Termux on Android, no root required. Install with
the one-liner above, then run `net status`. Output is in Spanish.

## Control de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 2026-10-18 | Primera versión pública |

## Licencia

MIT. Ver [LICENSE](LICENSE).
