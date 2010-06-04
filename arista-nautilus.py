"""
    Arista Transcoder Nautilus Extension
    ====================================
    Adds the ability to create conversions of media files directly in your
    file browser.
    
    Installation
    ------------
    In order to use this extension, it must be installed either to the global
    nautilus extensions directory or ~/.nautilus/python-extensions/ for each
    user that wishes to use it.
    
    Note that this script will not run outside of Nautilus!
    
    License
    -------
    Copyright 2010 Daniel G. Taylor <dan@programmer-art.org>
    
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

import arista; arista.init()
import gettext
import nautilus
import os

_ = gettext.gettext

SUPPORTED_FORMATS = [
    # Found in /usr/share/mime
    "audio/ac3",
    "audio/AMR",
    "audio/AMR-WB",
    "audio/annodex",
    "audio/basic",
    "audio/midi",
    "audio/mp2",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "audio/prs.sid",
    "audio/vnd.rn-realaudio",
    "audio/x-adpcm",
    "audio/x-aifc",
    "audio/x-aiff",
    "audio/x-aiffc",
    "audio/x-ape",
    "audio/x-flac",
    "audio/x-flac+ogg",
    "audio/x-gsm",
    "audio/x-it",
    "audio/x-m4b",
    "audio/x-matroska",
    "audio/x-minipsf",
    "audio/x-mod",
    "audio/x-mpegurl",
    "audio/x-ms-asx",
    "audio/x-ms-wma",
    "audio/x-musepack",
    "audio/x-psf",
    "audio/x-psflib",
    "audio/x-riff",
    "audio/x-s3m",
    "audio/x-scpls",
    "audio/x-speex",
    "audio/x-speex+ogg",
    "audio/x-stm",
    "audio/x-tta",
    "audio/x-voc",
    "audio/x-vorbis+ogg",
    "audio/x-wav",
    "audio/x-wavpack",
    "audio/x-wavpack-correction",
    "audio/x-xi",
    "audio/x-xm",
    "audio/x-xmf",
    "video/3gpp",
    "video/annodex",
    "video/dv",
    "video/isivideo",
    "video/mp2t",
    "video/mp4",
    "video/mpeg",
    "video/ogg",
    "video/quicktime",
    "video/vivo",
    "video/vnd.rn-realvideo",
    "video/wavelet",
    "video/x-anim",
    "video/x-flic",
    "video/x-flv",
    "video/x-matroska",
    "video/x-mng",
    "video/x-ms-asf",
    "video/x-msvideo",
    "video/x-ms-wmv",
    "video/x-nsv",
    "video/x-ogm+ogg",
    "video/x-sgi-movie",
    "video/x-theora+ogg",
]

class MediaConvertExtension(nautilus.MenuProvider):
    """
        An extension to provide an extra right-click menu for media files to
        convert them to any installed device preset.
    """
    def __init__(self):
        # Apparently required or some versions of nautilus crash!
        pass

    def get_file_items(self, window, files):
        """
            This method is called anytime one or more files are selected and
            the right-click menu is invoked. If we are looking at a media
            file then let's show the new menu item!
        """
        # We currently handle only one file
        if len(files) != 1:
            return
        
        # Check if this is actually a media file
        if files[0].get_mime_type() not in SUPPORTED_FORMATS:
            return
        
        # Create the new menu item, with a submenu of devices each with a 
        # submenu of presets for that particular device.
        menu = nautilus.MenuItem('Nautilus::convert_media',
                                 _('Convert for device'),
                                 _('Convert this media using a device preset'))
        
        devices = nautilus.Menu()
        menu.set_submenu(devices)
        
        presets = arista.presets.get().items()
        for shortname, device in sorted(presets, lambda x,y: cmp(x[1].name, y[1].name)):
            item = nautilus.MenuItem("Nautilus::convert_to_%s" % shortname,
                                     device.name,
                                     device.description)
            
            presets = nautilus.Menu()
            item.set_submenu(presets)
            
            for preset_name, preset in device.presets.items():
                preset_item = nautilus.MenuItem(
                        "Nautilus::convert_to_%s_%s" % (shortname, preset.name),
                        preset.name,
                        "%s: %s" % (device.name, preset.name))
                preset_item.connect("activate", self.callback,
                                    files[0].get_uri()[7:], shortname,
                                    preset.name)
                presets.append_item(preset_item)
            
            devices.append_item(item)
        
        return menu,
    
    def callback(self, menu, filename, device_name, preset_name):
        """
            Called when a menu item is clicked. Start a transcode job for
            the selected device and preset, and show the user the progress.
        """
        command = "arista-transcode -d %s -p \"%s\" \"%s\" /home/dan/test.out" % (device_name, preset_name, filename)
        os.system("gnome-terminal -e '%s'" % command)

