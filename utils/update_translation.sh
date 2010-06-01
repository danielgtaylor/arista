#!/bin/bash

# Extract all translatable messages to update the Arista PO template

xgettext -L glade -o - ui/*.ui | tail -n +6 >locale/templates/arista.pot
xgettext -L python -o - arista-gtk arista-transcode arista/*.py arista/inputs/*.py | tail -n +18 >>locale/templates/arista.pot

