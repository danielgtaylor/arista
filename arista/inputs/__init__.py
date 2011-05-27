#!/usr/bin/env python

"""
    Arista Input Device Discovery
    =============================
    This module provides methods to discover video-capable devices and disks
    using various backends.
    
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
import logging

_ = gettext.gettext

log = logging.getLogger("inputs")

try:
    from udevdisco import *
except ImportError:
    log.debug(_("Falling back to HAL device discovery"))
    try:
        from haldisco import *
    except:
        log.exception(_("Couldn't import udev- or HAL-based device discovery!"))
        raise

