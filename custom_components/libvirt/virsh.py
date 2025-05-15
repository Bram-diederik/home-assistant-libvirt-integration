import os
import subprocess
import logging
import re
import time


__all__ = ["get_vm_info", "get_all_vms", "run_virsh", "get_vm_ip", "get_vm_interfaces", "list_snapshots","get_vm_state","start_vm","shutdown_vm","unpause_vm","update_vm_cpu_load"]

_LOGGER = logging.getLogger(__name__)
SSH_WRAPPER = "/share/libvirt/ssh-wrapper"
SSH_WRAPPER_PATH = "/share/libvirt/"
DEFAULT_SSH_HOST = "root@localhost"
DEFAULT_URI = "qemu:///system"


def is_vm_running(vm_name, ssh_host=None, uri=None):
    output = run_virsh(["dominfo", vm_name], ssh_host=ssh_host, uri=uri)
    for line in output.splitlines():
        if line.startswith("State:"):
            return "running" in line.lower()
    return False

def get_vm_state(vm_name, ssh_host, uri):
    output = run_virsh(["domstate", vm_name], ssh_host, uri)
    return output.strip()

def start_vm(vm_name, ssh_host, uri):
    run_virsh(["start", vm_name], ssh_host, uri)

def shutdown_vm(vm_name, ssh_host, uri):
    run_virsh(["shutdown", vm_name], ssh_host, uri)

def unpause_vm(vm_name, ssh_host, uri):
    run_virsh(["resume", vm_name], ssh_host, uri)


def normalize_key(key):
    return key.lower().replace(" ", "_")

def ensure_ssh_wrapper():
    os.makedirs(os.path.dirname(SSH_WRAPPER_PATH), exist_ok=True)
    if not os.path.exists(SSH_WRAPPER):
        with open(SSH_WRAPPER, "w") as f:
            f.write("#!/bin/sh\n")
            f.write("exec /usr/bin/ssh -o StrictHostKeyChecking=accept-new -i /share/libvirt/ssh_key \"$@\"\n")
        os.chmod(SSH_WRAPPER, 0o755)

def run_virsh(args, ssh_host=DEFAULT_SSH_HOST, uri=DEFAULT_URI):
    ensure_ssh_wrapper()

    # Sanity fallback if ssh_host is accidentally empty or unset
    if not ssh_host or ssh_host == "root@localhost":
        _LOGGER.warning("Invalid or fallback ssh_host detected, skipping virsh command to avoid using root@localhost.")
        raise RuntimeError("Invalid SSH host. Expected something like 'daft@192.168.5.253'.")

    try:
        cmd = [SSH_WRAPPER, ssh_host, "virsh", "-c", "qemu:///system"] + args

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            _LOGGER.error(f"virsh error ({args}): {result.stderr.strip()}")
            raise subprocess.CalledProcessError(result.returncode, result.args, output=result.stdout, stderr=result.stderr)

        return result.stdout.strip()

    except Exception as e:
        _LOGGER.error(f"virsh command failed: {args}: {e}")
        raise

def get_all_vms(ssh_host=DEFAULT_SSH_HOST, uri=DEFAULT_URI):
    output = run_virsh(["list", "--all", "--name"], ssh_host, uri)
    return [line.strip() for line in output.splitlines() if line.strip()]



def get_vm_info(name, ssh_host=DEFAULT_SSH_HOST, uri=DEFAULT_URI):
    output = run_virsh(["dominfo", name], ssh_host, uri)
    data = {}
    for line in output.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            data[normalize_key(key.strip())] = val.strip()
    return data


def get_vm_interfaces(vm_name, ssh_host=DEFAULT_SSH_HOST, uri=DEFAULT_URI):
    try:
        output = run_virsh(["domifaddr", vm_name, "--source", "agent"], ssh_host, uri)
    except subprocess.CalledProcessError as e:
        # Exit code 1 means VM is likely off — this is expected, so ignore it
        if e.returncode == 1:
            return []
        else:
            raise  # re-raise unexpected errors
    except subprocess.CalledProcessError:
        # VM probably not running or no agent — ignore
        return []
    interfaces = []

    if not output:
        return interfaces

    lines = output.splitlines()
    header_found = False
    for line in lines:
        if re.match(r"^\s*-+\s*$", line):
            header_found = True
            continue
        if not header_found or not line.strip():
            continue

        parts = line.split()
        if len(parts) < 4:
            continue
        iface, mac, proto, addr = parts[:4]
        interfaces.append({
            "name": iface,
            "mac": mac,
            "protocol": proto,
            "address": addr,
        })

    return interfaces

def get_vm_ip(vm_name, ssh_host=DEFAULT_SSH_HOST, uri=DEFAULT_URI):
    interfaces = get_vm_interfaces(vm_name, ssh_host, uri)
    for iface in interfaces:
        if iface["protocol"] == "ipv4" and not iface["address"].startswith("127."):
            return iface["address"].split("/")[0]
    return None

def list_snapshots(vm_name, ssh_host=DEFAULT_SSH_HOST, uri=DEFAULT_URI):
    try:
        output = run_virsh(["snapshot-list", "--domain", vm_name], ssh_host, uri)
        lines = output.splitlines()[2:]  # Skip headers
        snapshots = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 1:
                snapshots.append({
                    "name": parts[0],
                    "created": parts[1] if len(parts) > 1 else None,
                    "state": parts[2] if len(parts) > 2 else None
                })
        return snapshots
    except Exception as e:
        print(f"⚠ Failed to list snapshots for {vm_name}: {e}")
        return []
