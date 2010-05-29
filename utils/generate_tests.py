#!/usr/bin/env python

"""
	Arista Test Generator
	=====================
	Generate a series of test files containing audio/video to run through the
	transcoder for unit testing.

	License
	-------
	Copyright 2008 Daniel G. Taylor <dan@programmer-art.org>

	This file is part of Arista.

	Arista is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	Foobar is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with Arista.  If not, see <http://www.gnu.org/licenses/>.
"""

import os

if not os.path.exists("tests"):
	os.mkdir("tests")

os.chdir("tests")

print "Generating test samples..."

# Ogg (Theora/Vorbis) tests
os.system("gst-launch-0.10 audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! vorbisenc ! oggmux ! filesink location='test-audio.ogg'")

os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! theoraenc ! oggmux ! filesink location='test-video.ogg'")

os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! theoraenc ! queue ! oggmux name=mux ! filesink location='test.ogg' audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! vorbisenc ! queue ! mux.")

# AVI (XVID, MP3), etc.
os.system("gst-launch-0.10 audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! lame ! filesink location='test-audio.mp3'")

os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! xvidenc ! avimux ! filesink location='test-video.avi'")

os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! xvidenc ! queue ! avimux name=mux ! filesink location='test.avi' audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! lame ! queue ! mux.")

# MP4 (H.264, AAC), etc
os.system("gst-launch-0.10 audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! faac ! qtmux ! filesink location='test-audio.m4a'")

os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! x264enc ! qtmux ! filesink location='test-video.mp4'")

os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! x264enc ! queue ! qtmux name=mux ! filesink location='test.mp4' audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! faac ! queue ! mux.")

os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! xvidenc ! queue ! qtmux name=mux ! filesink location='test2.mp4' audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! lame ! queue ! mux.")

# DV
# Why does this fail?
#os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! ffenc_dvvideo ! queue ! ffmux_dv name=mux ! filesink location='test.dv' audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! queue ! mux.")

# ASF (WMV/WMA)
os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! ffenc_wmv2 ! queue ! asfmux name=mux ! filesink location='test.wmv' audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! ffenc_wmav2 ! queue ! mux.")

print "Test samples can be found in the tests directory."

