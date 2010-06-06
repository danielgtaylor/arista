#!/usr/bin/env python

"""
    Arista Transcoder
    =================
    A class to transcode files given a preset.
    
    License
    -------
    Copyright 2009 - 2010 Daniel G. Taylor <dan@programmer-art.org>
    
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
import os
import os.path
import sys
import time

try:
    import multiprocessing
    CPU_COUNT = multiprocessing.cpu_count()
except ImportError:
    # Older version of python... just default to one to be safe
    CPU_COUNT = 1

import gobject
import gst

import discoverer

_ = gettext.gettext
_log = logging.getLogger("arista.transcoder")

# =============================================================================
# Custom exceptions
# =============================================================================

class TranscoderException(Exception):
    """
        A generic transcoder exception to be thrown when something goes wrong.
    """
    pass

class TranscoderStatusException(TranscoderException):
    """
        An exception to be thrown when there is an error retrieving the current
        status of an transcoder.
    """
    pass

class PipelineException(TranscoderException):
    """
        An exception to be thrown when the transcoder fails to construct a 
        working pipeline for whatever reason.
    """
    pass

# =============================================================================
# Transcoder Options
# =============================================================================

class TranscoderOptions(object):
    """
        Options pertaining to the input/output location, presets, 
        subtitles, etc.
    """
    def __init__(self, uri = None, preset = None, output_uri = None, 
                 subfile = None, font = "Sans Bold 16", deinterlace = None):
        """
            @type uri: str
            @param uri: The URI to the input file, device, or stream
            @type preset: Preset
            @param preset: The preset to convert to
            @type output_uri: str
            @param output_uri: The URI to the output file, device, or stream
            @type subfile: str
            @param subfile: The location of the subtitle file
            @type font: str
            @param font: Pango font description
            @type deinterlace: bool
            @param deinterlace: Force deinterlacing of the input data
        """
        self.reset(uri, preset, output_uri, subfile, font, deinterlace)
    
    def reset(self, uri = None, preset = None, output_uri = None,
              subfile = None, font = "Sans Bold 16", deinterlace = None):
        """
            Reset the input options to nothing.
        """
        self.uri = uri
        self.preset = preset
        self.output_uri = output_uri
        self.subfile = subfile
        self.font = font
        self.deinterlace = deinterlace

# =============================================================================
# The Transcoder
# =============================================================================

class Transcoder(gobject.GObject):
    """
        The transcoder - converts media between formats.
    """
    __gsignals__ = {
        "discovered": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                      (gobject.TYPE_PYOBJECT,      # info
                       gobject.TYPE_PYOBJECT)),    # is_media
        "pass-setup": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, tuple()),
        "pass-complete": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, tuple()),
        "message": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                   (gobject.TYPE_PYOBJECT,         # bus
                    gobject.TYPE_PYOBJECT)),       # message
        "complete": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, tuple()),
        "error": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                 (gobject.TYPE_PYOBJECT,)),        # error
    }
    
    def __init__(self, options):
        """
            @type options: TranscoderOptions
            @param options: The options, like input uri, subtitles, preset, 
                            output uri, etc.
        """
        self.__gobject_init__()
        self.options = options
        
        self.pipe = None
        
        self.enc_pass = 0
        
        self._percent_cached = 0
        self._percent_cached_time = 0
        
        def _got_info(info, is_media):
            self.info = info
            self.emit("discovered", info, is_media)
            
            if info.is_video or info.is_audio:
                try:
                    self._setup_pass()
                except PipelineException, e:
                    self.emit("error", str(e))
                    return
                    
                self.start()
        
        self.info = None
        self.discoverer = discoverer.Discoverer(options.uri)
        self.discoverer.connect("discovered", _got_info)
        self.discoverer.discover()
    
    @property
    def infile(self):
        """
            Provide access to the input uri for backwards compatibility after
            moving to TranscoderOptions for uri, subtitles, etc.
            
            @rtype: str
            @return: The input uri to process
        """
        return self.options.uri
    
    @property
    def preset(self):
        """
            Provide access to the output preset for backwards compatibility
            after moving to TranscoderOptions.
            
            @rtype: Preset
            @return: The output preset
        """
        return self.options.preset
    
    def _get_source(self):
        """
            Return a file or dvd source string usable with gst.parse_launch.
            
            This method uses self.infile to generate its output.
            
            @rtype: string
            @return: Source to prepend to gst-launch style strings.
        """
        if self.infile.startswith("dvd://"):
            filename = self.infile.split("@")[0]
            if self.options.deinterlace is None:
                self.options.deinterlace = True
        elif self.infile.startswith("v4l://") or self.infile.startswith("v4l2://"):
            filename = self.infile
        elif self.infile.startswith("file://"):
            filename = self.infile
        else:
            filename = "file://" + self.infile
            
        return "uridecodebin uri=\"%s\" name=dmux" % filename
    
    def _setup_pass(self):
        """
            Setup the pipeline for an encoding pass. This configures the
            GStreamer elements and their setttings for a particular pass.
        """
        # Get limits and setup caps
        self.vcaps = gst.Caps()
        self.vcaps.append_structure(gst.Structure("video/x-raw-yuv"))
        self.vcaps.append_structure(gst.Structure("video/x-raw-rgb"))
        
        self.acaps = gst.Caps()
        self.acaps.append_structure(gst.Structure("audio/x-raw-int"))
        self.acaps.append_structure(gst.Structure("audio/x-raw-float"))
        
        # =====================================================================
        # Setup video, audio/video, or audio transcode pipeline
        # =====================================================================
        
        # Figure out which mux element to use
        container = None
        if self.info.is_video and self.info.is_audio:
            container = self.preset.container
        elif self.info.is_video:
            container = self.preset.vcodec.container and \
                        self.preset.vcodec.container or \
                        self.preset.container
        elif self.info.is_audio:
            container = self.preset.acodec.container and \
                        self.preset.acodec.container or \
                        self.preset.container
        
        mux_str = ""
        if container:
            mux_str = "%s name=mux ! queue !" % container
        
        # Decide whether or not we are using a muxer and link to it or just
        # the file sink if we aren't (for e.g. mp3 audio)
        if mux_str:
            premux = "mux."
        else:
            premux = "sink."
        
        src = self._get_source()
        
        cmd = "%s %s filesink name=sink " \
              "location=\"%s\"" % (src, mux_str, self.options.output_uri)
            
        if self.info.is_video and self.preset.vcodec:
            # =================================================================
            # Update limits based on what the encoder really supports
            # =================================================================
            element = gst.element_factory_make(self.preset.vcodec.name,
                                               "vencoder")
            
            # TODO: Add rate limits based on encoder sink below
            for cap in element.get_pad("sink").get_caps():
                for field in ["width", "height"]:
                    if cap.has_field(field):
                        value = cap[field]
                        if isinstance(value, gst.IntRange):
                            vmin, vmax = value.low, value.high
                        else:
                            vmin, vmax = value, value
                        
                        cur = getattr(self.preset.vcodec, field)
                        if cur[0] < vmin:
                            cur = (vmin, cur[1])
                            setattr(self.preset.vcodec, field, cur)
                    
                        if cur[1] > vmax:
                            cur = (cur[0], vmax)
                            setattr(self.preset.vcodec, field, cur)
            
            # =================================================================
            # Calculate video width/height and add black bars if necessary
            # =================================================================
            wmin, wmax = self.preset.vcodec.width
            hmin, hmax = self.preset.vcodec.height
            
            owidth, oheight = self.info.videowidth, self.info.videoheight
            width, height = owidth, oheight
            
            # Scale width / height down
            if owidth > wmax:
                width = wmax
                height = int((float(wmax) / owidth) * oheight)
            if height > hmax:
                height = hmax
                width = int((float(hmax) / oheight) * owidth)
            
            # Add any required padding
            vbox = ""
            if width < wmin and height < hmin:
                wpx = (wmin - width) / 2
                hpx = (hmin - height) / 2
                vbox = "videobox left=%i right=%i top=%i bottom=%i ! " % \
                       (-wpx, -wpx, -hpx, -hpx)
            elif width < wmin:
                px = (wmin - width) / 2
                vbox = "videobox left=%i right=%i ! " % (-px, -px)
            elif height < hmin:
                px = (hmin - height) / 2
                vbox = "videobox top=%i bottom=%i ! " % (-px, -px)
            
            try:
                if self.info.videocaps[0].has_key("pixel-aspect-ratio"):
                    width = int(width * float(self.info.videocaps[0]["pixel-aspect-ratio"]))
            except KeyError:
                # The videocaps we are looking for may not even exist, just ignore
                pass
            
            # FIXME Odd widths / heights seem to freeze gstreamer
            if width % 2:
                width += 1
            if height % 2:
                height += 1
            
            for vcap in self.vcaps:
                vcap["width"] = width
                vcap["height"] = height
            
            # =================================================================
            # Setup video framerate and add to caps
            # =================================================================
            rmin = self.preset.vcodec.rate[0].num / \
                   float(self.preset.vcodec.rate[0].denom)
            rmax = self.preset.vcodec.rate[1].num / \
                   float(self.preset.vcodec.rate[1].denom)
            orate = self.info.videorate.num / float(self.info.videorate.denom)
            
            if orate > rmax:
                num = self.preset.vcodec.rate[1].num
                denom = self.preset.vcodec.rate[1].denom
            elif orate < rmin:
                num = self.preset.vcodec.rate[0].num
                denom = self.preset.vcodec.rate[0].denom
            else:
                num = self.info.videorate.num
                denom = self.info.videorate.denom
            
            for vcap in self.vcaps:
                vcap["framerate"] = gst.Fraction(num, denom)
            
            # =================================================================
            # Properly handle and pass through pixel aspect ratio information
            # =================================================================
            for x in range(self.info.videocaps.get_size()):
                struct = self.info.videocaps[x]
                if struct.has_field("pixel-aspect-ratio"):
                    # There was a bug in xvidenc that flipped the fraction
                    # Fixed in svn on 12 March 2008
                    # We need to flip the fraction on older releases!
                    par = struct["pixel-aspect-ratio"]
                    if self.preset.vcodec.name == "xvidenc":
                        for p in gst.registry_get_default().get_plugin_list():
                            if p.get_name() == "xvid":
                                if p.get_version() <= "0.10.6":
                                    par.num, par.denom = par.denom, par.num
                    for vcap in self.vcaps:
                        vcap["pixel-aspect-ratio"] = par
                    break
            
            # FIXME a bunch of stuff doesn't seem to like pixel aspect ratios
            # Just force everything to go to 1:1 for now...
            for vcap in self.vcaps:
                vcap["pixel-aspect-ratio"] = gst.Fraction(1, 1)
            
            # =================================================================
            # Setup the video encoder and options
            # =================================================================
            vencoder = "%s %s" % (self.preset.vcodec.name,
                                  self.preset.vcodec.passes[self.enc_pass] % {
                                    "threads": CPU_COUNT,
                                  })
            
            deint = ""
            if self.options.deinterlace:
                deint = " ffdeinterlace ! "
            
            sub = ""
            if self.options.subfile:
                # Render subtitles onto the video stream
                sub = "textoverlay font-desc=\"%(font)s\" name=txt ! " % {
                    "font": self.options.font,
                }
                cmd += " filesrc location=\"%(subfile)s\" ! subparse ! txt." % {
                    "subfile": self.options.subfile
                }
            
            vmux = premux
            if container in ["qtmux", "webmmux", "ffmux_dvd", "matroskamux"]:
                if premux.startswith("mux"):
                    vmux += "video_%d"
            
            cmd += " dmux. ! queue ! ffmpegcolorspace ! videorate !" \
                   "%s %s videoscale ! %s ! %s%s ! tee " \
                   "name=videotee ! queue ! %s" % \
                   (deint, sub, self.vcaps.to_string(), vbox, vencoder, vmux)
            
        if self.info.is_audio and self.preset.acodec and \
           self.enc_pass == len(self.preset.vcodec.passes) - 1:
            # =================================================================
            # Update limits based on what the encoder really supports
            # =================================================================
            element = gst.element_factory_make(self.preset.acodec.name,
                                               "aencoder")
            
            fields = {}
            for cap in element.get_pad("sink").get_caps():
                for field in ["width", "depth", "rate", "channels"]:
                    if cap.has_field(field):
                        if field not in fields:
                            fields[field] = [0, 0]
                        value = cap[field]
                        if isinstance(value, gst.IntRange):
                            vmin, vmax = value.low, value.high
                        else:
                            vmin, vmax = value, value
                        
                        if vmin < fields[field][0]:
                            fields[field][0] = vmin
                        if vmax > fields[field][1]:
                            fields[field][1] = vmax
            
            for name, (amin, amax) in fields.items():
                cur = getattr(self.preset.acodec, field)
                if cur[0] < amin:
                    cur = (amin, cur[1])
                    setattr(self.preset.acodec, field, cur)
                if cur[1] > amax:
                    cur = (cur[0], amax)
                    setattr(self.preset.acodec, field, cur)
            
            # =================================================================
            # Prepare audio capabilities
            # =================================================================
            for attribute in ["width", "depth", "rate", "channels"]:
                current = getattr(self.info, "audio" + attribute)
                amin, amax = getattr(self.preset.acodec, attribute)
                
                for acap in self.acaps:
                    if amin < amax:
                        acap[attribute] = gst.IntRange(amin, amax)
                    else:
                        acap[attribute] = amin
            
            # =================================================================
            # Add audio transcoding pipeline to command
            # =================================================================
            aencoder = self.preset.acodec.name + " " + \
                       self.preset.acodec.passes[ \
                            len(self.preset.vcodec.passes) - \
                            self.enc_pass - 1 \
                       ] % {
                            "threads": CPU_COUNT,
                       }
            
            amux = premux
            if container in ["qtmux", "webmmux", "ffmux_dvd", "matroskamux"]:
                if premux.startswith("mux"):
                    amux += "audio_%d"
            
            cmd += " dmux. ! queue ! audioconvert ! audiorate ! " \
                   "audioresample ! %s ! %s ! %s" % \
                   (self.acaps.to_string(), aencoder, amux)
        
        # =====================================================================
        # Build the pipeline and get ready!
        # =====================================================================
        self._build_pipeline(cmd)
        
        self.emit("pass-setup")
    
    def _build_pipeline(self, cmd):
        """
            Build a gstreamer pipeline from a given gst-launch style string and
            connect a callback to it to receive messages.
            
            @type cmd: string
            @param cmd: A gst-launch string to construct a pipeline from.
        """
        _log.debug(cmd.replace("(", "\\(").replace(")", "\\)")\
                      .replace(";", "\;"))
        
        try:
            self.pipe = gst.parse_launch(cmd)
        except gobject.GError, e:
            raise PipelineException(_("Unable to construct pipeline! ") + \
                                    str(e))
        
        bus = self.pipe.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_message)
    
    def _on_message(self, bus, message):
        """
            Process pipe bus messages, e.g. start new passes and emit signals
            when passes and the entire encode are complete.
            
            @type bus: object
            @param bus: The session bus
            @type message: object
            @param message: The message that was sent on the bus
        """
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.state = gst.STATE_NULL
            self.emit("pass-complete")
            if self.enc_pass < self.preset.pass_count - 1:
                self.enc_pass += 1
                self._setup_pass()
                self.start()
            else:
                self.emit("complete")
        
        self.emit("message", bus, message)
    
    def start(self, reset_timer=True):
        """
            Start the pipeline!
        """
        self.state = gst.STATE_PLAYING
        if reset_timer:
            self.start_time = time.time()
    
    def pause(self):
        """
            Pause the pipeline!
        """
        self.state = gst.STATE_PAUSED

    def stop(self):
        """
            Stop the pipeline!
        """
        self.state = gst.STATE_NULL

    def get_state(self):
        """
            Return the gstreamer state of the pipeline.
            
            @rtype: int
            @return: The state of the current pipeline.
        """
        if self.pipe:
            return self.pipe.get_state()[1]
        else:
            return None
    
    def set_state(self, state):
        """
            Set the gstreamer state of the pipeline.
            
            @type state: int
            @param state: The state to set, e.g. gst.STATE_PLAYING
        """
        if self.pipe:
            self.pipe.set_state(state)
    
    state = property(get_state, set_state)
    
    def get_status(self):
        """
            Get information about the status of the encoder, such as the
            percent completed and nicely formatted time remaining.
            
            Examples
            
             - 0.14, "00:15" => 14% complete, 15 seconds remaining
             - 0.0, "Uknown" => 0% complete, uknown time remaining
            
            Raises EncoderStatusException on errors.
            
            @rtype: tuple
            @return: A tuple of percent, time_rem
        """
        duration = max(self.info.videolength, self.info.audiolength)
        
        if not duration or duration < 0:
            return 0.0, _("Unknown")
        
        try:
            pos, format = self.pipe.query_position(gst.FORMAT_TIME)
        except gst.QueryError:
            raise TranscoderStatusException(_("Can't query position!"))
        except AttributeError:
            raise TranscoderStatusException(_("No pipeline to query!"))
        
        percent = pos / float(duration)
        if percent <= 0.0:
            return 0.0, _("Unknown")
        
        if self._percent_cached == percent and time.time() - self._percent_cached_time > 5:
            self.pipe.post_message(gst.message_new_eos(self.pipe))
        
        if self._percent_cached != percent:
            self._percent_cached = percent
            self._percent_cached_time = time.time()
        
        total = 1.0 / percent * (time.time() - self.start_time)
        rem = total - (time.time() - self.start_time)
        min = rem / 60
        sec = rem % 60
        
        try:
            time_rem = _("%(min)d:%(sec)02d") % {
                "min": min,
                "sec": sec,
            }
        except TypeError:
            raise TranscoderStatusException(_("Problem calculating time " \
                                              "remaining!"))
        
        return percent, time_rem
    
    status = property(get_status)
    
