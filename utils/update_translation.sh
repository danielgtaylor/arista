#!/bin/bash

# Extract all translatable messages to update the Arista PO template

xgettext -L glade -o locale/templates/arista.pot ui/*.ui
xgettext -L python -o locale/templates/arista.pot -j arista-gtk arista-transcode arista-nautilus.py arista/*.py arista/inputs/*.py

