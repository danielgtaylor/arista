#!/bin/bash

epydoc --html -o api arista arista-transcode arista-gtk && gnome-open api/index.html

