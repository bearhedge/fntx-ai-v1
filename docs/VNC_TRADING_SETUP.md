# VNC Trading Desktop Setup

This guide explains how to connect to the VNC remote desktop for IB Gateway trading.

## Quick Connect

- **IP Address**: `35.194.231.94`
- **Port**: `5901`
- **Password**: `fntx2024`

## Connection Instructions

### From Windows/Mac/Linux:
1. Download a VNC viewer (RealVNC, TightVNC, or TigerVNC)
2. Connect to: `35.194.231.94:5901`
3. Enter password: `fntx2024`

### What You'll See:
- XFCE desktop environment
- IB Gateway application (auto-starts)
- Terminal for running commands

## IB Gateway Configuration

Once connected, configure IB Gateway:

1. **Login**: Use your IB credentials
2. **API Settings**:
   - Go to Configure → Settings → API → Settings
   - Enable "Enable ActiveX and Socket Clients"
   - Set Socket port: `4001`
   - Add trusted IP: `127.0.0.1`
   - Click Apply & OK

## Service Management

The VNC server runs as a systemd service and auto-starts on boot:

```bash
# Check status
sudo systemctl status vncserver@:1

# Restart if needed
sudo systemctl restart vncserver@:1

# View logs
sudo journalctl -u vncserver@:1 -f
```

## Troubleshooting

### Grey Screen
- Disconnect and reconnect
- Check if XFCE is running: `ps aux | grep xfce`

### Can't Connect
- Verify port 5901 is open: `sudo ss -tlnp | grep 5901`
- Check firewall: `gcloud compute firewall-rules list | grep vnc`

### IB Gateway Issues
- Ensure you're connected to VNC first
- Check IB Gateway logs in the application
- Verify API settings are correct

## Persistent Setup

This VNC server is configured to:
- Auto-start on VM boot
- Auto-restart if crashed
- Maintain IB Gateway settings between sessions

No need to reinstall anything - just connect and trade!