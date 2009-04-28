#!/usr/bin/env python

"""
	Run Arista Transcode Tests
	==========================
	Generate test files in various formats and transcode them to all available
	output devices and qualities.
"""

import os
import os.path
import arista

if os.path.exists("tests"):
	os.system("rm -rf tests")

os.system("./generate_tests.py")
	
files = os.listdir("tests")

status = []

for id, plugin in arista.plugins.get().items():
	for file in files:
		print plugin["make"] + " " + plugin["model"] + ": " + file
		cmd = "./transcode -s -o transcodetest tests/%s %s" % (file, id)
		print cmd
		ret = os.system(cmd)
		if ret:
			status.append([file, plugin, True])
		else:
			status.append([file, plugin, False])

print "Report"
print "======"

for file, plugin, failed in status:
	if failed:
		print plugin["make"] + " " + plugin["model"] + " (" + \
														file + "): Failed"
	else:
		print plugin["make"] + " " + plugin["model"] + " (" + \
														file + "): Succeeded"

print "Tests completed."

