import time
import logging
from datetime import timedelta
from homeassistant.helpers.entity import Entity
from .virsh import get_vm_info, get_vm_ip, get_vm_interfaces, list_snapshots, get_all_vms, normalize_key

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=30)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    uri = config.get("uri", "qemu://system")
    ssh_host = config.get("ssh_host", "root@localhost")
    include_interfaces = config.get("include_interfaces", False)

    vms = await hass.async_add_executor_job(get_all_vms, ssh_host, uri)
    sensors = [LibvirtVMSensor(vm_name, ssh_host, uri,include_interfaces) for vm_name in vms]
    async_add_entities(sensors, True)

class LibvirtVMSensor(Entity):
    def __init__(self, name, ssh_host, uri,include_interfaces):
        self._name = name
        self._state = None
        self._attributes = {}
        self._ssh_host = ssh_host
        self._uri = uri
        self._include_interfaces = include_interfaces
        self._last_cpu_time = None
        self._last_timestamp = None

    @property
    def name(self):
        return f"libvirt_{self._name.lower()}"

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    def update(self):
        try:
            info = get_vm_info(self._name, self._ssh_host, self._uri)
            ip = get_vm_ip(self._name, self._ssh_host, self._uri)
            if (self._include_interfaces):
               interfaces = get_vm_interfaces(self._name, self._ssh_host, self._uri)
            else:
               interfaces = []
            snapshots = list_snapshots(self._name, self._ssh_host, self._uri)

            self._state = info.get("state", "unknown")
            self._attributes = {
                **info,
                "ip": ip,
                "interfaces": interfaces,
                "snapshots": snapshots,
                "ssh_host":  self._ssh_host,
                "uri" : self._url,
            }

        except Exception as e:
            _LOGGER.warning(f"Failed to update VM {self._name}: {e}")
            self._state = "unavailable"
            self._attributes = {"error": str(e)}


