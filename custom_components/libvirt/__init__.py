from .virsh import ensure_ssh_wrapper, SSH_WRAPPER, run_virsh, is_vm_running, DEFAULT_URI
import os
import subprocess
import logging
import base64

DOMAIN = "libvirt_vms"
_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    ensure_ssh_wrapper()
    ssh_map = {}

    # Get ssh_host values from switch/sensor platform config
    for platform in ("switch", "sensor"):
        for entry in config.get(platform, []):
            if isinstance(entry, dict) and entry.get("platform") == DOMAIN:
                ssh_host = entry.get("ssh_host")
                if not ssh_host:
                    continue
                try:
                    output = run_virsh(["list", "--all", "--name"], ssh_host=ssh_host, uri=DEFAULT_URI)
                    vm_names = [line.strip() for line in output.splitlines() if line.strip()]
                    for vm_name in vm_names:
                        ssh_map[vm_name] = ssh_host
                except Exception as e:
                    _LOGGER.error(f"Failed to get VMs from {ssh_host}: {e}")

    hass.data[DOMAIN] = {
        name: {"ssh_host": ssh_host} for name, ssh_host in ssh_map.items()
    }

    def get_ssh_host(vm_name):
        vm_data = hass.data.get(DOMAIN, {}).get(vm_name)
        if not vm_data:
            _LOGGER.error(f"No SSH host configured for VM: {vm_name}")
            raise RuntimeError(f"No SSH host configured for VM: {vm_name}")
        return vm_data["ssh_host"]

    # Service handlers
    async def handle_vm_screenshot(call):
        name = call.data["name"]
        try:
            ssh_host = get_ssh_host(name)
        except RuntimeError:
            return

        remote_ppm = f"/tmp/{name}.ppm"
        remote_png = f"/tmp/{name}.png"
        local_path = f"/config/www/libvirt/{name}.png"
        os.makedirs("/config/www/libvirt", exist_ok=True)

        # Take screenshot in PPM format
        run_virsh(["screenshot", name, remote_ppm, "--screen", "0"], ssh_host=ssh_host)

        # Convert to PNG on the remote server
        try:
            convert_cmd = f"convert {remote_ppm} {remote_png}"
            subprocess.run([SSH_WRAPPER, ssh_host, convert_cmd], check=True)
        except subprocess.CalledProcessError as e:
            _LOGGER.error(f"Failed to convert screenshot to PNG: {e.stderr}")
            return
        except Exception as e:
            _LOGGER.error(f"Unexpected error during conversion: {e}")
            return

        # Fetch and decode the PNG
        try:
            cmd = [SSH_WRAPPER, ssh_host, f"base64 {remote_png}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            result.check_returncode()
        except subprocess.CalledProcessError as e:
            _LOGGER.error(f"Failed to base64 encode screenshot: {e.stderr}")
            return
        except Exception as e:
            _LOGGER.error(f"Unexpected error: {e}")
            return

        b64_data = result.stdout
        try:
            with open(local_path, "wb") as f:
                f.write(base64.b64decode(b64_data))
        except Exception as e:
            _LOGGER.error(f"Failed to write screenshot to {local_path}: {e}")
            return

        _LOGGER.info(f"Saved screenshot to {local_path}")


    async def handle_start_vm(call):
        name = call.data["name"]
        ssh_host = get_ssh_host(name)
        run_virsh(["start", name], ssh_host=ssh_host)

    async def handle_shutdown_vm(call):
        name = call.data["name"]
        ssh_host = get_ssh_host(name)
        run_virsh(["shutdown", name], ssh_host=ssh_host)

    async def handle_suspend_vm(call):
        name = call.data["name"]
        ssh_host = get_ssh_host(name)
        run_virsh(["suspend", name], ssh_host=ssh_host)

    async def handle_resume_vm(call):
        name = call.data["name"]
        ssh_host = get_ssh_host(name)
        run_virsh(["resume", name], ssh_host=ssh_host)

    async def handle_create_snapshot(call):
        name = call.data["name"]
        ssh_host = get_ssh_host(name)
        snapshot = call.data.get("snapshot", f"{name}_snap")
        run_virsh(["snapshot-create-as", name, snapshot], ssh_host=ssh_host)

    async def handle_revert_snapshot(call):
        name = call.data["name"]
        ssh_host = get_ssh_host(name)
        snapshot = call.data["snapshot"]
        run_virsh(["snapshot-revert", name, snapshot], ssh_host=ssh_host)

    async def handle_delete_snapshot(call):
        name = call.data["name"]
        ssh_host = get_ssh_host(name)
        snapshot = call.data["snapshot"]
        run_virsh(["snapshot-delete", name, snapshot], ssh_host=ssh_host)

    # Register services
    hass.services.async_register(DOMAIN, "start_vm", handle_start_vm)
    hass.services.async_register(DOMAIN, "shutdown_vm", handle_shutdown_vm)
    hass.services.async_register(DOMAIN, "suspend_vm", handle_suspend_vm)
    hass.services.async_register(DOMAIN, "resume_vm", handle_resume_vm)

    hass.services.async_register(DOMAIN, "create_snapshot", handle_create_snapshot)
    hass.services.async_register(DOMAIN, "revert_snapshot", handle_revert_snapshot)
    hass.services.async_register(DOMAIN, "delete_snapshot", handle_delete_snapshot)

    hass.services.async_register(DOMAIN, "take_screenshot", handle_vm_screenshot)

    return True
