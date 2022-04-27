import signal
import os
import subprocess
import json
from functools import reduce
from gi.repository import GLib
from gi.repository import Gio


class RaucHandler():
    def __init__(self):
        self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        self.dbus_proxy = Gio.DBusProxy.new_sync(
            self.bus, Gio.DBusProxyFlags.NONE, None, 'de.pengutronix.rauc', '/', 'de.pengutronix.rauc.Installer', None)

    def get_slot_status(self):
        response = subprocess.run("rauc status --detailed --output-format=json",
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
        if response.returncode != 0:
            return None

        result = json.loads(response.stdout)
        rootfs0 = next(item for item in result["slots"] if "rootfs.0" in item)[
            "rootfs.0"]
        self.printf(rootfs0)
        rootfs1 = next(item for item in result["slots"] if "rootfs.1" in item)[
            "rootfs.1"]
        slot_status = {
            "rootfs0": {
                "installed.count": self.deep_get(rootfs0, "slot_status.installed.count"),
                "status": self.deep_get(rootfs0, "slot_status.status"),
                "type": rootfs0["type"],
                "sha256": self.deep_get(rootfs0, "slot_status.checksum.sha256"),
                "bundle.compatible": self.deep_get(rootfs0, "slot_status.bundle.compatible"),
                "device": rootfs0["device"],
                "boot-status": self.deep_get(rootfs0, "slot_status.status"),
                "size": self.deep_get(rootfs0, "slot_status.checksum.size"),
                "bundle.build": self.deep_get(rootfs0, "slot_status.bundle.build"),
                "activated.timestamp": self.deep_get(rootfs0, "slot_status.activated.timestamp"),
                "installed.timestamp": self.deep_get(rootfs0, "slot_status.installed.timestamp"),
                "state": rootfs0["state"],
                "bootname": rootfs0["bootname"],
                "class": rootfs0["class"],
                "bundle.version": self.deep_get(rootfs0, "slot_status.bundle.version"),
                "bundle.description": self.deep_get(rootfs0, "slot_status.bundle.description"),
                "description": None,
                "activated.count": self.deep_get(rootfs0, "slot_status.activated.count")
            },
            "rootfs1": {
                "installed.count": self.deep_get(rootfs1, "slot_status.installed.count"),
                "status": self.deep_get(rootfs1, "slot_status.status"),
                "type": rootfs1["type"],
                "sha256": self.deep_get(rootfs1, "slot_status.checksum.sha256"),
                "bundle.compatible": self.deep_get(rootfs1, "slot_status.bundle.compatible"),
                "device": rootfs1["device"],
                "boot-status": self.deep_get(rootfs1, "slot_status.status"),
                "size": self.deep_get(rootfs1, "slot_status.checksum.size"),
                "bundle.build": self.deep_get(rootfs1, "slot_status.bundle.build"),
                "activated.timestamp": self.deep_get(rootfs1, "slot_status.activated.timestamp"),
                "installed.timestamp": self.deep_get(rootfs1, "slot_status.installed.timestamp"),
                "state": rootfs1["state"],
                "bootname": rootfs1["bootname"],
                "class": rootfs1["class"],
                "bundle.version": self.deep_get(rootfs1, "slot_status.bundle.version"),
                "bundle.description": self.deep_get(rootfs1, "slot_status.bundle.description"),
                "description": None,
                "activated.count": self.deep_get(rootfs1, "slot_status.activated.count")
            }
        }
        return slot_status

    def mark_partition(self, state, partition):
        mark_result = self.dbus_proxy.call_sync('Mark', GLib.Variant(
            '(ss)', (state, partition)), Gio.DBusCallFlags.NO_AUTO_START, 500, None)
        return mark_result

    def install(self, path):
        self.dbus_proxy.Install('(s)', (path))
        self.reboot_after_install()

    def reboot_after_install(self, nb):
        os.system("/sbin/reboot")

    def deep_get(self, dictionary, keys, default=None):
        return reduce(lambda d, key: d.get(key, default) if isinstance(d, dict) else default, keys.split("."), dictionary)
