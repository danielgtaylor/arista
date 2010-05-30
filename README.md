Arista Transcoder 0.9.4
=======================
A simple preset-based transcoder for the GNOME Desktop and a small script for 
terminal-based transcoding. Settings are chosen based on output device and 
quality preset.

 * [Official website](http://www.transcoder.org/)

Dependencies
------------
 * python-gudev
 * python-cairo
 * python-gobject
 * python-gtk >=2.16
 * python-gconf
 * python-gstreamer
 * python-pynotify (optional)
 * gstreamer-ffmpeg
 * gstreamer-plugins-base
 * gstreamer-plugins-good
 * gstreamer-plugins-bad
 * gstreamer-plugins-ugly

Installation
------------
Installation uses python distutils. After extracting the archive, run:

    python setup.py install

If you are using Ubuntu 9.04 (Jaunty) or later, make sure to install with:

    python setup.py install --install-layout=deb

Don't forget to use sudo if necessary. This will install the arista python 
module to your python site-packages or dist-packages path, install the arista 
programs into sys.prefix/bin and install all data files into 
sys.prefix/share/arista.

Usage
-----
There are two clients available, a graphical client using GTK+ and a terminal 
client. The graphical client is failry self-explanatory and can be launched 
with:

    arista-gtk

To use the terminal client please see:

    arista-transcode --help

An example of using the terminal client:

    arista-transcode --device=ipod --preset=low test.mp4 test-ipod.m4v

Other usefule terminal options:

    arista-transcode --info
    arista-transcode --info ipod

Generating a Test File
----------------------
Sometimes it may be useful to generate a test file:

    gst-launch-0.10 videotestsrc num-buffers=500 ! x264enc ! mp4mux ! filesink location=test.mp4

Creating New Device Presets
---------------------------
New device presets can be created via the [create preset](http://www.transcoder.org/presets/creat/ "Create a new Arista Transcoder preset")
page on the website or by specifying information about yourself and 
the device you wish to support along with presets that describe how to create a
proper gstreamer pipeline to encode for the device in a JSON file. 

Contributing
------------
All active development has moved to GitHub.com. Code is managed through git and
new bugs should be opened in the GitHub tracker. Translations and Answers
are still managed on Launchpad. The GitHub page is here:

 * [Github project page](http://github.com/danielgtaylor/arista)

You can grab a copy of the source code for Arista via:

    git clone git://github.com/danielgtaylor/arista.git

Feel free to fork on GitHub and propose updates to the main branch. You can
keep your branch up to date via `git pull`

The public website of this project is also open source, and can be found here:

 * [Website project page](http://github.com/danielgtaylor/arista-website)

Feel free to fork it and contribute as well.

