#/bin/bash
# Quick way to launch downpour in debug mode if you
# are developing features for it in the src/ directory

if test ! -e "test"; then
	mkdir test
	mkdir test/user-dir
	mkdir test/work-dir
fi
PYTHONPATH=src bin/downpourd -c cfg/debug.cfg -d
