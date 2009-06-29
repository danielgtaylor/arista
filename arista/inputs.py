#!/usr/bin/env python

"""
    Arista Input Device Discovery
    =============================
    A set of tools to discover DVD-capable devices and Video4Linux devices that
    emit signals when disks that contain video are inserted or webcames / tuner
    cards are plugged in using HAL through DBus.
    
    License
    -------
    Copyright 2008 - 2009 Daniel G. Taylor <dan@programmer-art.org>
    
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
import dbus

from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

_ = gettext.gettext

class InputSource(object):
    """
        A simple object representing an input source.
    """
    def __init__(self, udi, interface):
        """
            Create a new input device.
            
            @type udi: string
            @param udi: The HAL device identifier for this device.
            @type interface: dbus.Interface
            @param interface: The Hal.Device DBus interface for this device.
        """
        self.udi = udi
        self.interface = interface
        self.product = self.interface.GetProperty("info.product")
    
    def _get_nice_label(self):
        """
            Get a nice label for this device.
            
            @rtype: str
            @return: The label, in this case the product name
        """
        return self.product
    
    nice_label = property(_get_nice_label)

class DVDDevice(InputSource):
    """
        A simple object representing a DVD-capable device.
    """
    def __init__(self, udi, interface):
        """
            Create a new DVD device.
            
            @type udi: string
            @param udi: The HAL device identifier for this device.
            @type interface: dbus.Interface
            @param interface: The Hal.Device DBus interface for this device.
        """
        super(DVDDevice, self).__init__(udi, interface)
        
        self.video = False
        self.video_udi = ""
        self.label = ""
    
    def _get_media(self):
        """
            Check whether media is in the device.
            
            @rtype: bool
            @return: True if media is present in the device.
        """
        return self.interface.GetProperty("storage.removable.media_available")
    
    media = property(_get_media)
    
    def _get_block(self):
        """
            Get the device block in the filesystem for this device.
            
            @rtype: string
            @return: The device block, such as "/dev/cdrom".
        """
        return self.interface.GetProperty("block.device")
    
    block = property(_get_block)
    
    def get_nice_label(self, label=None):
        """
            Get a nice label that looks like "The Big Lebowski" if a video
            disk is found, otherwise the model name.
            
            @type label: string
            @param label: Use this label instead of the disk label.
            @rtype: string
            @return: The nicely formatted label.
        """
        if not label:
            label = self.label
            
        if label:
            words = [word.capitalize() for word in label.split("_")]
            return " ".join(words)
        else:
            return self.product
    
    nice_label = property(get_nice_label)

class V4LDevice(InputSource):
    """
        A simple object representing a Video 4 Linux device.
    """
    def _get_device(self):
        """
            Get the device block in the filesystem for this device.
            
            @rtype: string
            @return: The device block, such as "/dev/cdrom".
        """
        return self.interface.GetProperty("video4linux.device")
    
    device = property(_get_device)
    
    def _get_version(self):
        """
            Get the Video 4 Linux version of this device.
            
            @rtype: str
            @return: The version, either '1' or '2'
        """
        return self.interface.GetProperty("video4linux.version")
    
    version = property(_get_version)

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
            Create a new DVDFinder and attach to the DBus system bus to find
            device information through HAL.
        """
        self.__gobject_init__()
        self.bus = dbus.SystemBus()
        self.hal_obj = self.bus.get_object("org.freedesktop.Hal",
                                           "/org/freedesktop/Hal/Manager")
        self.hal = dbus.Interface(self.hal_obj, "org.freedesktop.Hal.Manager")
        
        self.drives = {}
        self.capture_devices = {}
        
        udis = self.hal.FindDeviceByCapability("storage.cdrom")
        for udi in udis:
            dev_obj = self.bus.get_object("org.freedesktop.Hal", udi)
            dev = dbus.Interface(dev_obj, "org.freedesktop.Hal.Device")
            if dev.GetProperty("storage.cdrom.dvd"):
                #print "Found DVD drive!"
                block = dev.GetProperty("block.device")
                self.drives[block] = DVDDevice(udi, dev)
        
        udis = self.hal.FindDeviceByCapability("volume.disc")
        for udi in udis:
            dev_obj = self.bus.get_object("org.freedesktop.Hal", udi)
            dev = dbus.Interface(dev_obj, "org.freedesktop.Hal.Device")
            if dev.PropertyExists("volume.disc.is_videodvd"):
                if dev.GetProperty("volume.disc.is_videodvd"):
                    block = dev.GetProperty("block.device")
                    label = dev.GetProperty("volume.label")
                    if self.drives.has_key(block):
                        self.drives[block].video = True
                        self.drives[block].video_udi = udi
                        self.drives[block].label = label
        
        udis = self.hal.FindDeviceByCapability("video4linux")
        for udi in udis:
            dev_obj = self.bus.get_object("org.freedesktop.Hal", udi)
            dev = dbus.Interface(dev_obj, "org.freedesktop.Hal.Device")
            if dev.QueryCapability("video4linux.video_capture"):
                device = dev.GetProperty("video4linux.device")
                self.capture_devices[device] = V4LDevice(udi, dev)
        
        self.hal.connect_to_signal("DeviceAdded", self.device_added)
        self.hal.connect_to_signal("DeviceRemoved", self.device_removed)
    
    def device_added(self, udi):
        """
            Called when a device has been added to the system. If the device
            is a volume with a video DVD the "video-found" signal is emitted.
        """
        dev_obj = self.bus.get_object("org.freedesktop.Hal", udi)
        dev = dbus.Interface(dev_obj, "org.freedesktop.Hal.Device")
        if dev.PropertyExists("block.device"):
            block = dev.GetProperty("block.device")
            if self.drives.has_key(block):
                if dev.PropertyExists("volume.disc.is_videodvd"):
                    if dev.GetProperty("volume.disc.is_videodvd"):
                        label = dev.GetProperty("volume.label")
                        self.drives[block].video = True
                        self.drives[block].video_udi = udi
                        self.drives[block].label = label
                        self.emit("disc-found", self.drives[block], label)
        elif dev.PropertyExists("video4linux.device"):
            device = dev.GetProperty("video4linux.device")
            capture_device = V4LDevice(udi, dev)
            self.capture_devices[device] = capture_device
            self.emit("v4l-capture-found", capture_device)
    
    def device_removed(self, udi):
        """
            Called when a device has been removed from the signal. If the
            device is a volume with a video DVD the "video-lost" signal is
            emitted.
        """
        for block, drive in self.drives.items():
            if drive.video_udi == udi:
                drive.video = False
                drive.udi = ""
                label = drive.label
                drive.label = ""
                self.emit("disc-lost", drive, label)
                break
        
        for device, capture in self.capture_devices.items():
            if capture.udi == udi:
                self.emit("v4l-capture-lost", self.capture_devices[device])
                del self.capture_devices[device]
                break

gobject.type_register(InputFinder)

if __name__ == "__main__":
    # Run a test to print out DVD-capable devices and whether or not they
    # have video disks in them at the moment.
    import gobject
    gobject.threads_init()
    
    def found(finder, device, label):
        print device.product + ": " + label
    
    def lost(finder, device, label):
        print device.product + ": " + _("Not mounted.")
    
    finder = InputFinder()
    finder.connect("disc-found", found)
    finder.connect("disc-lost", lost)
    
    for block, drive in finder.drives.items():
        print drive.product + ": " + (drive.video and drive.label or \
                                      _("Not mounted."))
    
    for device, capture in finder.capture_devices.items():
        print capture.product + ": " + device
    
    loop = gobject.MainLoop()
    loop.run()

