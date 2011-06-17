#!/usr/bin/env python

"""
    Arista Queue Handling
    =====================
    A set of tools to handle creating a queue of transcodes and running them
    one after the other.
    
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
import threading
import time

import gobject
import gst

from .transcoder import Transcoder

_ = gettext.gettext
_log = logging.getLogger("arista.queue")

class QueueEntry(object):
    """
        An entry in the queue.
    """
    def __init__(self, options):
        """
            @type options: arista.transcoder.TranscoderOptions
            @param options: The input options (uri, subs) to process
        """
        self.options = options
        
        # Set when QueueEntry.stop() was called so you can react accordingly
        self.force_stopped = False
    
    def __repr__(self):
        return _("Queue entry %(infile)s -> %(preset)s -> %(outfile)s" % {
            "infile": self.options.uri,
            "preset": self.options.preset,
            "outfile": self.options.output_uri,
        })
    
    def stop(self):
        """
            Stop this queue entry from processing.
        """
        if hasattr(self, "transcoder") and self.transcoder.pipe:
            self.transcoder.pipe.send_event(gst.event_new_eos())
            self.transcoder.start()
            
            self.force_stopped = True

class TranscodeQueue(gobject.GObject):
    """
        A generic queue for transcoding. This object acts as a list of 
        QueueEntry items with a couple convenience methods. A timeout in the
        gobject main loop continuously checks for new entries and starts
        them as needed.
    """
    
    __gsignals__ = {
        "entry-added": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                       (gobject.TYPE_PYOBJECT,)),      # QueueEntry
        "entry-discovered": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                            (gobject.TYPE_PYOBJECT,    # QueueEntry
                             gobject.TYPE_PYOBJECT,    # info
                             gobject.TYPE_PYOBJECT)),  # is_media
        "entry-pass-setup": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                            (gobject.TYPE_PYOBJECT,)), # QueueEntry
        "entry-start": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                       (gobject.TYPE_PYOBJECT,)),      # QueueEntry
        "entry-error": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                       (gobject.TYPE_PYOBJECT,         # QueueEntry
                        gobject.TYPE_PYOBJECT,)),      # errorstr
        "entry-complete": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                          (gobject.TYPE_PYOBJECT,)),   # QueueEntry
    }
    
    def __init__(self, check_interval = 500):
        """
            Create a new queue, setup locks, and register a callback.
            
            @type check_interval: int
            @param check_interval: The interval in milliseconds between
                                   checking for new queue items
        """
        self.__gobject_init__()
        self._queue = []
        self.running = True
        self.pipe_running = False
        self.enc_pass = 0
        gobject.timeout_add(check_interval, self._check_queue)
    
    def __getitem__(self, index):
        """
            Safely get an item from the queue.
        """
        item = self._queue[index]
        return item
    
    def __setitem__(self, index, item):
        """
            Safely modify an item in the queue.
        """
        self._queue[index] = item
    
    def __delitem__(self, index):
        """
            Safely delete an item from the queue.
        """
        if index == 0 and self.pipe_running:
            self.pipe_running = False
        
        del self._queue[index]
    
    def __len__(self):
        """
            Safely get the length of the queue.
        """
        return len(self._queue)
    
    def __repr__(self):
        """
            Safely get a representation of the queue and its items.
        """
        return _("Transcode queue: ") + repr(self._queue)
    
    def insert(self, pos, entry):
        """
            Insert an entry at an arbitrary position.
        """
        self._queue.insert(pos, entry)
    
    def append(self, options):
        """
            Append a QueueEntry to the queue.
        """
        # Sanity check of input options
        if not options.uri or not options.preset or not options.output_uri:
            raise ValueError("Invalid input options %s" % str(options))
        
        self._queue.append(QueueEntry(options))
        self.emit("entry-added", self._queue[-1])
    
    def remove(self, entry):
        """
            Remove a QueueEntry from the queue.
        """
        self._queue.remove(entry)
    
    def _check_queue(self):
        """
            This method is invoked periodically by the gobject mainloop.
            It watches the queue and when items are added it will call
            the callback and watch over the pipe until it completes, then loop
            for each item so that each encode is executed after the previous
            has finished.
        """
        item = None
        if len(self._queue) and not self.pipe_running:
            item = self._queue[0]
        if item:
            _log.debug(_("Found item in queue! Queue is %(queue)s" % {
                "queue": str(self)
            }))
            item.transcoder =  Transcoder(item.options)
            item.transcoder.connect("complete", self._on_complete)
            
            def discovered(transcoder, info, is_media):
                self.emit("entry-discovered", item, info, is_media)
                if not is_media:
                    self.emit("entry-error", item, _("Not a recognized media file!"))
                    self._queue.pop(0)
                    self.pipe_running = False
            
            def pass_setup(transcoder):
                self.emit("entry-pass-setup", item)
                if transcoder.enc_pass == 0:
                    self.emit("entry-start", item)
            
            def error(transcoder, errorstr):
                self.emit("entry-error", item, errorstr)
                self._queue.pop(0)
                self.pipe_running = False
            
            item.transcoder.connect("discovered", discovered)
            item.transcoder.connect("pass-setup", pass_setup)
            item.transcoder.connect("error", error)
            self.pipe_running = True
        return True
    
    def _on_complete(self, transcoder):
        """
            An entry is complete!
        """
        self.emit("entry-complete", self._queue[0])
        self._queue.pop(0)
        self.pipe_running = False

