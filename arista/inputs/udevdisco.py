#!/usr/bin/env python

"""
    Arista Input Device Discovery
    =============================
    A set of tools to discover DVD-capable devices and Video4Linux devices that
    emit signals when disks that contain video are inserted or webcames / tuner
    cards are plugged in using udev.

    http://github.com/nzjrs/python-gudev/blob/master/test.py
    http://www.kernel.org/pub/linux/utils/kernel/hotplug/gudev/GUdevDevice.html
    
    License
    -------
    Copyright 2008 - 2011 Daniel G. Taylor <dan@programmer-art.org>
    
    This file is part of Arista.

    Arista is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as 
    published by the Free Software Foundation, either version 2.1 of
    the License, or (at your option) any later version.

    Arista is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with Arista.  If not, see
    <http://www.gnu.org/licenses/>.
"""

import gettext

import gobject
import gudev

_ = gettext.gettext

class InputSource(object):
    """
        A simple object representing an input source.
    """
    def __init__(self, device):
        """
            Create a new input device.
            
            @type device: gudev.Device
            @param device: The device that we are using as an input source
        """
        self.device = device

    @property
    def nice_label(self):
        """
            Get a nice label for this device.
            
            @rtype: str
            @return: The label, in this case the product name
        """
        return self.path
    
    @property
    def path(self):
        """
            Get the device block in the filesystem for this device.
            
            @rtype: string
            @return: The device block, such as "/dev/cdrom".
        """
        return self.device.get_device_file()

class DVDDevice(InputSource):
    """
        A simple object representing a DVD-capable device.
    """
    @property
    def media(self):
        """
            Check whether media is in the device.
            
            @rtype: bool
            @return: True if media is present in the device.
        """
        return self.device.has_property("ID_FS_TYPE")

    @property
    def nice_label(self):
        if self.device.has_property("ID_FS_LABEL"):
            label = self.device.get_property("ID_FS_LABEL")
            return " ".join([word.capitalize() for word in label.split("_")])
        else:
            return self.device.get_property("ID_MODEL")

class V4LDevice(InputSource):
    """
        A simple object representing a Video 4 Linux device.
    """
    @property
    def nice_label(self):
        return self.device.get_sysfs_attr("name")

    @property
    def version(self):
        """
            Get the video4linux version of this device.
        """
        if self.device.has_property("ID_V4L_VERSION"):
            return self.device.get_property("ID_V4L_VERSION")
        else:
            # Default to version 2
            return "2"

class InputFinder(gobject.GObject):
    """
        An object that will find and monitor DVD-capable devices on your 
        machine and emit signals when video disks are inserted / removed.
        
        Signals:
        
         - disc-found(InputFinder, DVDDevice, label)
         - disc-lost(InputFinder, DVDDevice, label)
         - v4l-capture-found(InputFinder, V4LDevice)
         - v4l-capture-lost(InputFinder, V4LDevice)
    """
    
    __gsignals__ = {
        "disc-found": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, 
                       (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "disc-lost": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, 
                      (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "v4l-capture-found": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                              (gobject.TYPE_PYOBJECT,)),
        "v4l-capture-lost": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                             (gobject.TYPE_PYOBJECT,)),
        
    }
    
    def __init__(self):
        """
            Create a new DVDFinder and attach to the udev system to listen for
            events.
        """
        self.__gobject_init__()

        self.client = gudev.Client(["video4linux", "block"])
        
        self.drives = {}
        self.capture_devices = {}

        for device in self.client.query_by_subsystem("video4linux"):
            block = device.get_device_file()
            self.capture_devices[block] = V4LDevice(device)

        for device in self.client.query_by_subsystem("block"):
            if device.has_property("ID_CDROM"):
                block = device.get_device_file()
                self.drives[block] = DVDDevice(device)

        self.client.connect("uevent", self.event)

    def event(self, client, action, device):
        """
            Handle a udev event.
        """
        return {
            "add": self.device_added,
            "change": self.device_changed,
            "remove": self.device_removed,
        }.get(action, lambda x,y: None)(device, device.get_subsystem())
    
    def device_added(self, device, subsystem):
        """
            Called when a device has been added to the system.
        """
        print device, subsystem
        if subsystem == "video4linux":
            block = device.get_device_file()
            self.capture_devices[block] = V4LDevice(device)
            self.emit("v4l-capture-found", self.capture_devices[block])

    def device_changed(self, device, subsystem):
        """
            Called when a device has changed. If the change represents a disc
            being inserted or removed, fire the disc-found or disc-lost signals
            respectively.
        """
        if subsystem == "block" and device.has_property("ID_CDROM"):
            block = device.get_device_file()
            dvd_device = self.drives[block]
            media_changed = dvd_device.media != device.has_property("ID_FS_TYPE")
            dvd_device.device = device
            if media_changed:
                if dvd_device.media:
                    self.emit("disc-found", dvd_device, dvd_device.nice_label)
                else:
                    self.emit("disc-lost", dvd_device, dvd_device.nice_label)
    
    def device_removed(self, device, subsystem):
        """
            Called when a device has been removed from the system.
        """
        pass

gobject.type_register(InputFinder)

if __name__ == "__main__":
    # Run a test to print out DVD-capable devices and whether or not they
    # have video disks in them at the moment.
    import gobject
    gobject.threads_init()
    
    def found(finder, device, label):
        print device.path + ": " + label
    
    def lost(finder, device, label):
        print device.path + ": " + _("Not mounted.")
    
    finder = InputFinder()
    finder.connect("disc-found", found)
    finder.connect("disc-lost", lost)
    
    for device, drive in finder.drives.items():
        print drive.nice_label + ": " + device
    
    for device, capture in finder.capture_devices.items():
        print capture.nice_label + " V4Lv" + str(capture.version) + ": " + device
    
    loop = gobject.MainLoop()
    loop.run()

