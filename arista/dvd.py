"""
    Arista DVD Utilities
    ====================
    Utility classes and methods dealing with DVDs.
    
    License
    -------
    Copyright 2011 Daniel G. Taylor <dan@programmer-art.org>
    
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

import gobject
import subprocess

class DvdInfo(gobject.GObject):
    """
        Get info about a DVD using an external process running lsdvd. Emits
        a GObject signal when ready with the DVD info.
    """
    __gsignals__ = {
        "ready": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,  (gobject.TYPE_PYOBJECT,)),
    }

    def __init__(self, path):
        gobject.GObject.__init__(self)
        self.path = path
        self.proc = subprocess.Popen('lsdvd -x -Oy %s' % path, stdout=subprocess.PIPE, shell=True)

        gobject.timeout_add(100, self.run)

    def run(self):
        # Check if we have the info, if not, return and we will be called
        # again to check in 100ms.
        if self.proc.poll() is not None:
            if self.proc.returncode == 0:
                # TODO: is there a safer way to do this?
                exec(self.proc.stdout.read())
                self.emit("ready", lsdvd)
            
            return False

        return True

gobject.type_register(DvdInfo)

