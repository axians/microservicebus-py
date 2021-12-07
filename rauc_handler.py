import signal
import os
from pydbus import SystemBus


class RaucHandler():
    def __init__(self):
        self.bus = SystemBus()
        # the service we request
        self.service_name = 'de.pengutronix.rauc'
        # The interface we request of the service
        self.interface_name = 'de.pengutronix.rauc.Installer'
        # The object we request
        self.object_path = '/'
        remote_object = self.bus.get(self.service_name, '/')

        # help(remote_object)
        self.iface = remote_object['de.pengutronix.rauc.Installer']
        #slot_status = iface.GetSlotStatus()
        # print(slot_status)

    def get_slot_status(self):
        slot_status = self.iface.GetSlotStatus()
        return slot_status

    def mark_partition(self, state, partition):
        return self.iface.Mark(state, partition)

    def install(self, path):
        self.iface.Install(path)
        self.iface.on('Completed', lambda nb: self.reboot_after_install(nb))
    
    def reboot_after_install(self, nb):
        print("Received completed from RAUC interface")
        os.system("sudo /sbin/reboot") 
