import signal, os, dbus

class RaucHandler():
    def __init__(self):
        self.bus = dbus.SessionBus()
        # the service we request
        self.service_name = 'de.pengutronix.rauc'
        # The interface we request of the service
        self.interface_name = 'de.pengutronix.rauc.Installer'
        # The object we request
        self.object_path = '/'
        remote_object = self.bus.get_object(self.service_name,self.object_path)

        self.iface = dbus.Interface(remote_object, self.interface_name)
    

    