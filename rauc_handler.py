import signal
import os
from gi.repository import GLib
from gi.repository import Gio


class RaucHandler():
    def __init__(self):


        self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        self.dbus_proxy = Gio.DBusProxy.new_sync(bus,
                                            Gio.DBusProxyFlags.NONE,
                                            None,
                                            'de.pengutronix.rauc',
                                            '/',
                                            'de.pengutronix.rauc.Installer',
                                            None)
        

    def get_slot_status(self):
        slot_status = self.dbus_proxy.call_sync('GetSlotStatus',
                                                GLib.Variant('(s)', (state,partition)),
                                        Gio.DBusCallFlags.NO_AUTO_START, 500, None)
        return slot_status

    def mark_partition(self, state, partition):
        mark_result = self.dbus_proxy.call_sync('Mark',
                                                GLib.Variant('(s)', (state,partition)),
                                        Gio.DBusCallFlags.NO_AUTO_START, 500, None)
        return mark_result

    def install(self, path):
        try:
            self.dbus_proxy.call_sync('Install',
                                        GLib.Variant('(s)', (path,)),
                                        Gio.DBusCallFlags.NO_AUTO_START, 500, None)
            self.reboot_after_install()
        except Exception as e:
            print(f"Error in rauc_handler.install: {e}")
        
    
    def reboot_after_install(self, nb):
        print("Received completed from RAUC interface")
        os.system("/sbin/reboot") 
