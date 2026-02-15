#!/usr/bin/env bash
# =============================================================================
# DwarfAlp – Raspberry Pi Zero W deployment script
#
# Prerequisites:
#   - Raspberry Pi OS Lite (Bookworm or later)
#   - Pi connected to a WiFi network that also has the DWARF 3 in STA mode
#   - Internet access (for package installation)
#
# Usage:
#   curl -sSL <repo-url>/deploy/pi/setup.sh | bash
#   # or clone the repo first:
#   cd dwarfAlp && bash deploy/pi/setup.sh
# =============================================================================
set -euo pipefail

APP_DIR="/opt/dwarfAlp"
VENV_DIR="$APP_DIR/.venv"
SERVICE_NAME="dwarfAlp"
USER="dwarfAlp"

echo "========================================"
echo "  DwarfAlp – Raspberry Pi Setup"
echo "========================================"

# ── 1. System packages ──────────────────────────────────────────────────────
echo "[1/6] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3 python3-venv python3-pip python3-dev \
    libffi-dev libssl-dev \
    libopenblas-dev \
    git

# ── 2. Create service user ──────────────────────────────────────────────────
if ! id "$USER" &>/dev/null; then
    echo "[2/6] Creating service user '$USER'..."
    sudo useradd --system --create-home --shell /usr/sbin/nologin "$USER"
else
    echo "[2/6] User '$USER' already exists."
fi

# ── 3. Install DwarfAlp ─────────────────────────────────────────────────────
echo "[3/6] Installing DwarfAlp into $APP_DIR..."
if [ -d "$APP_DIR/.git" ]; then
    sudo -u "$USER" git -C "$APP_DIR" pull --ff-only || true
elif [ -f "pyproject.toml" ]; then
    # Running from inside the repo
    sudo mkdir -p "$APP_DIR"
    sudo cp -r . "$APP_DIR/"
    sudo chown -R "$USER:$USER" "$APP_DIR"
else
    echo "ERROR: Run this script from inside the dwarfAlp repository."
    exit 1
fi

echo "[3/6] Creating virtual environment..."
sudo -u "$USER" python3 -m venv "$VENV_DIR"
sudo -u "$USER" "$VENV_DIR/bin/pip" install --upgrade pip wheel
sudo -u "$USER" "$VENV_DIR/bin/pip" install -e "$APP_DIR"

# ── 4. Generate TLS certificate ─────────────────────────────────────────────
echo "[4/6] Generating TLS certificate..."
HOSTNAME=$(hostname)
sudo -u "$USER" "$VENV_DIR/bin/python" -m dwarf_alpaca.cli generate-cert \
    --out-dir "$APP_DIR/var/tls" \
    --hostname "$HOSTNAME" 2>/dev/null || echo "  (skipped – cryptography not installed or cert already exists)"

# ── 5. Create default config ────────────────────────────────────────────────
echo "[5/6] Creating configuration..."
CONFIG_DIR="$APP_DIR/config"
sudo -u "$USER" mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/pi-remote.yaml" ]; then
    cat <<'YAML' | sudo -u "$USER" tee "$CONFIG_DIR/pi-remote.yaml" > /dev/null
# DwarfAlp – Raspberry Pi remote configuration
# Edit this file to match your setup.

latency_profile: "remote"

# Authentication – CHANGE THIS to a strong random string!
api_key: "CHANGE_ME_TO_A_STRONG_SECRET"

# TLS
enable_https: true
tls_certfile: "/opt/dwarfAlp/var/tls/cert.pem"
tls_keyfile: "/opt/dwarfAlp/var/tls/key.pem"

# Disable UDP discovery (useless over Tailscale)
discovery_enabled: false

# Reconnection – aggressive for unstable mobile links
ws_reconnect_enabled: true
ws_reconnect_max_retries: 30
ws_reconnect_max_delay: 60.0
YAML
    echo "  IMPORTANT: Edit $CONFIG_DIR/pi-remote.yaml and change api_key!"
fi

# ── 6. Install systemd service ──────────────────────────────────────────────
echo "[6/6] Installing systemd service..."
sudo cp "$APP_DIR/deploy/pi/dwarfAlp.service" /etc/systemd/system/ 2>/dev/null || \
cat <<EOF | sudo tee /etc/systemd/system/dwarfAlp.service > /dev/null
[Unit]
Description=DwarfAlp – DWARF 3 Alpaca Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$APP_DIR
ExecStart=$VENV_DIR/bin/dwarf-alpaca start --skip-provision --config $CONFIG_DIR/pi-remote.yaml
Restart=on-failure
RestartSec=10
Environment=DWARF_ALPACA_NETWORK_MODE=sta

# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=$APP_DIR/var
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo ""
echo "========================================"
echo "  Setup complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo ""
echo "  1. Edit the config file:"
echo "     sudo nano $CONFIG_DIR/pi-remote.yaml"
echo "     → Change api_key to a strong secret"
echo "     → Set dwarf_ap_ip if DWARF has a fixed STA IP"
echo ""
echo "  2. Provision DWARF 3 into STA mode (if not already done):"
echo "     sudo -u $USER $VENV_DIR/bin/dwarf-alpaca guide"
echo ""
echo "  3. Install Tailscale for remote access:"
echo "     curl -fsSL https://tailscale.com/install.sh | sh"
echo "     sudo tailscale up"
echo ""
echo "  4. Start the service:"
echo "     sudo systemctl start $SERVICE_NAME"
echo "     sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "  From your remote machine (also on Tailscale):"
echo "     NINA → Alpaca server: https://<pi-tailscale-ip>:11111"
echo "     Health check:  curl -k https://<pi-tailscale-ip>:11111/management/health"
echo ""
