#!/bin/bash

# Extract all translatable messages to update the Arista PO template

xgettext -L glade -o locale/templates/arista.pot ui/*.ui
xgettext -L python -o - arista-gtk arista-transcode arista/*.py | tail -n +18 >>locale/templates/arista.pot

