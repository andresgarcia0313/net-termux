#!/data/data/com.termux/files/usr/bin/bash
# Instala net-termux: `net status` y `tailscale status` en Termux, sin root.
#   curl -fsSL https://raw.githubusercontent.com/andresgarcia0313/net-termux/main/install.sh | bash
#   ... | bash -s -- --uninstall      (para quitarlo)
set -euo pipefail

REPO="${NET_TERMUX_REPO:-https://github.com/andresgarcia0313/net-termux.git}"
DIR="${NET_TERMUX_DIR:-$HOME/.local/share/net-termux}"
BIN="$HOME/.local/bin"
CONF="$HOME/.config/net-termux/tailscale-hosts"

say()  { printf '\033[36m●\033[0m %s\n' "$*"; }
ok()   { printf '\033[32m●\033[0m %s\n' "$*"; }
fail() { printf '\033[31m✕\033[0m %s\n' "$*" >&2; exit 1; }

[ -n "${PREFIX:-}" ] && [ -d "$PREFIX" ] && case "$PREFIX" in *com.termux*) true ;; *) false ;; esac \
  || fail "Esto es para Termux en Android. En Linux usa net-status: github.com/andresgarcia0313/net-status"

uninstall() {
  for cmd in net tailscale; do
    target="$(readlink "$BIN/$cmd" 2>/dev/null || true)"
    case "$target" in "$DIR"/*) rm -f "$BIN/$cmd" && ok "Quitado $BIN/$cmd" ;; esac
  done
  case "$DIR" in "$HOME"/?*) [ -d "$DIR/.git" ] && rm -rf -- "$DIR" && ok "Quitado $DIR" ;; esac
  ok "net-termux desinstalado. La configuración sigue en ${CONF%/*} por si vuelves."
  exit 0
}
[ "${1:-}" = "--uninstall" ] && uninstall

need=()
command -v python3 >/dev/null || need+=(python)
command -v git >/dev/null || need+=(git)
command -v ssh >/dev/null || need+=(openssh)
command -v termux-wifi-connectioninfo >/dev/null || need+=(termux-api)
if [ ${#need[@]} -gt 0 ]; then
  say "Instalando paquetes: ${need[*]}"
  pkg install -y "${need[@]}" >/dev/null
fi

if [ -d "$DIR/.git" ]; then
  say "Actualizando $DIR"
  git -C "$DIR" pull --ff-only --quiet
else
  say "Descargando en $DIR"
  mkdir -p "${DIR%/*}"
  git clone --quiet --depth 1 "$REPO" "$DIR"
fi

mkdir -p "$BIN"
for cmd in net tailscale; do
  if [ -e "$BIN/$cmd" ] && [ ! -L "$BIN/$cmd" ]; then
    fail "$BIN/$cmd ya existe y no es de net-termux. Muévelo y vuelve a correr el instalador."
  fi
  ln -sf "$DIR/bin/$cmd" "$BIN/$cmd"
done

case ":$PATH:" in
  *":$BIN:"*) ;;
  *) for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
       [ -f "$rc" ] || [ "$rc" = "$HOME/.bashrc" ] || continue
       grep -qs 'net-termux' "$rc" || printf '\nexport PATH="$HOME/.local/bin:$PATH"  # net-termux\n' >> "$rc"
     done
     say "Abre una sesión nueva de Termux (o corre: export PATH=\"\$HOME/.local/bin:\$PATH\")" ;;
esac

"$DIR/bin/net" --help >/dev/null || fail "La instalación no arranca: revisa que python3 funcione."
ok "Listo. Prueba:  net status"
[ -f "$CONF" ] || say "Para 'tailscale status' escribe en $CONF el nombre SSH de un equipo con el CLI de Tailscale."
command -v termux-wifi-connectioninfo >/dev/null && say "Para ver la señal Wi-Fi instala también la app Termux:API (F-Droid o Google Play)."
exit 0
