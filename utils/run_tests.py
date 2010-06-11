#!/usr/bin/env python

"""
	Run Arista Transcode Tests
	==========================
	Generate test files in various formats and transcode them to all available
	output devices and qualities.
"""
import os
import subprocess
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import arista; arista.init()

if not os.path.exists("tests"):
	os.system("./utils/generate_tests.py")
	
files = os.listdir("tests")

status = []

try:
	for id, device in arista.presets.get().items():
		for file in files:
			print device.make + " " + device.model + ": " + file
			cmd = "./arista-transcode -q -d %s -o test_output tests/%s" % (id, file)
			print cmd
			ret = subprocess.call(cmd, shell=True)
			if ret:
				status.append([file, device, True])
			else:
				status.append([file, device, False])
except KeyboardInterrupt:
	pass

print "Report"
print "======"

for file, device, failed in status:
	if failed:
		print device.make + " " + device.model + " (" + \
														file + "): Failed"
	else:
		print device.make + " " + device.model + " (" + \
														file + "): Succeeded"

print "Tests completed."
