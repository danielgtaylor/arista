#!/usr/bin/env python

import os
from glob import glob

from distutils.core import setup

# Patch distutils if it can't cope with the "classifiers" or
# "download_url" keywords
from sys import version
if version < '2.2.3':
    from distutils.dist import DistributionMetadata
    DistributionMetadata.classifiers = None
    DistributionMetadata.download_url = None

data_files = [
    (os.path.join("share", "applications"), ["arista.desktop"]),
]

for (prefix, path) in [("arista", "presets"), 
                        ("arista", "ui"), 
                        ("", "locale")]:
    for root, dirs, files in os.walk(path):
        to_add = []
        
        for filename in files:
            to_add.append(os.path.join(root, filename))
            
        if to_add:
            data_files.append((os.path.join("share", prefix, root), to_add))

setup(
    name = "arista",
    version = "0.9.4.1",
    description = "An easy multimedia transcoder for GNOME",
    long_description = """Overview
========
An easy to use multimedia transcoder for the GNOME Desktop. Arista focuses on
being easy to
use by making the complex task of encoding for various devices simple. Pick your
input, pick your target device, choose a file to save to and go.

Arista has been in development since early 2008 as a side project and was just
recently polished to make it release-worthy. The 0.8 release is the first release available to the public. Please see http://github.com/danielgtaylor/arista for information on helping out.

Features
---------

* Presets for iPod, computer, DVD player, PSP, and more
* Live preview to see encoded quality
* Automatically discover available DVD drives and media
* Rip straight from DVD media easily
* Automatically discover and record from Video4Linux devices
* Support for H.264, WebM, FLV, Ogg, DivX and more
* Batch processing of entire directories easily
* Simple terminal client for scripting

Requirements
---------------
Arista is written in Python and requires the bindings for GTK+ 2.16 or newer,
GStreamer, GConf, GObject, Cairo, and udev. If you are an Ubuntu user this means
you need to be using at least Ubuntu 9.04 (Jaunty). The GStreamer plugins
required depend on the presets available, but at this time you should have
gst-plugins-good, gst-plugins-bad, gst-plugins-ugly, and gst-ffmpeg. If you are
on Ubuntu don't forget to install the multiverse packages.

Note: WebM support requires at least GStreamer's gst-plugins-bad-0.10.19.
""",
    author = "Daniel G. Taylor",
    author_email = "dan@programmer-art.org",
    url = "http://www.transcoder.org/",
    download_url = "http://programmer-art.org/media/releases/arista-transcoder/arista-0.9.4.1.tar.gz",
    packages = [
        "arista",
    ],
    scripts = [
        "arista-gtk",
        "arista-transcode",
    ],
    data_files = data_files,
    requires = [
        "gtk(>=2.16)", 
        "gst(>=10.22)",
        "gconf",
        "cairo",
        "udev",
    ],
    provides = [
        "arista",
    ],
    keywords = "gnome gtk gstreamer transcode multimedia",
    platforms = [
        "Platform Independent",
    ],
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: X11 Applications :: GTK",
        "Environment :: X11 Applications :: Gnome",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Multimedia :: Sound/Audio :: Conversion",
        "Topic :: Multimedia :: Video :: Conversion",
        "Topic :: Utilities",
    ],
    zip_safe = False,
)

