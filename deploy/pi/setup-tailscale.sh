#!/usr/bin/env bash
# =============================================================================
# DwarfAlp – Tailscale setup helper for Raspberry Pi
#
# Installs Tailscale and configures it for remote DwarfAlp access.
# Run after setup.sh has completed.
# =============================================================================
set -euo pipefail

echo "========================================"
echo "  Tailscale Setup for DwarfAlp"
echo "========================================"

# ── 1. Install Tailscale ────────────────────────────────────────────────────
if command -v tailscale &>/dev/null; then
    echo "[1/3] Tailscale already installed: $(tailscale version)"
else
    echo "[1/3] Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
fi

# ── 2. Authenticate ─────────────────────────────────────────────────────────
echo "[2/3] Starting Tailscale..."
echo "  A browser URL will appear – open it on another device to authenticate."
echo ""
sudo tailscale up --hostname="dwarfAlp-pi"

# ── 3. Show connection info ─────────────────────────────────────────────────
echo ""
echo "[3/3] Tailscale is connected!"
echo ""

TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "unknown")
echo "========================================"
echo "  Tailscale IP: $TAILSCALE_IP"
echo "========================================"
echo ""
echo "From your remote machine (with Tailscale installed and logged in):"
echo ""
echo "  Health check:"
echo "    curl -k https://$TAILSCALE_IP:11111/management/health"
echo ""
echo "  NINA / Voyager Alpaca configuration:"
echo "    Host: $TAILSCALE_IP"
echo "    Port: 11111"
echo "    (Add X-API-Key header in custom settings if your client supports it)"
echo ""
echo "  Monitor logs:"
echo "    ssh pi@$TAILSCALE_IP"
echo "    sudo journalctl -u dwarfAlp -f"
echo ""
echo "Remember to also install Tailscale on your remote computer:"
echo "  https://tailscale.com/download"
echo ""
