import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import Entity
from .virsh import get_all_vms, is_vm_running, run_virsh,get_vm_state,unpause_vm,start_vm

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    uri = config.get("uri", "qemu://system")
    ssh_host = config.get("ssh_host", "root@localhost")


    try:
        domains = await hass.async_add_executor_job(get_all_vms, ssh_host, uri)
    except Exception as e:
        _LOGGER.error("Failed to get VMs from %s: %s", ssh_host, e)
        return

    switches = [LibvirtVMSwitch(name, ssh_host, uri, hass) for name in domains]
    for switch in switches:
       await switch.async_update()
    async_add_entities(switches)

class LibvirtVMSwitch(SwitchEntity):
    def __init__(self, name, ssh_host, uri, hass):
        self._name = name
        self._ssh_host = ssh_host
        self._uri = uri
        self.hass = hass
        self._state = False 

    @property
    def should_poll(self):
        return True

  
    @property
    def name(self):
        return f"libvirt_{self._name.lower()}"


    @property
    def is_on(self):
        return self._state

    async def async_update(self):
        self._state = await self.hass.async_add_executor_job(
            is_vm_running, self._name, self._ssh_host, self._uri
        )

    async def async_turn_on(self, **kwargs):
        state = get_vm_state(self._name, self._ssh_host,self._uri)
        if state == "paused":
            unpause_vm(self._name, self._ssh_host,self._uri)
        elif state == "shut off":
            start_vm(self._name, self._ssh_host,self._uri)
        self._state = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(
            run_virsh, ["shutdown", self._name], self._ssh_host, self._uri
        )
