#/bin/bash
# Quick way to launch downpour in debug mode if you
# are developing features for it in the src/ directory

if test ! -e "debug"; then
	mkdir debug
	mkdir debug/user-dir
	mkdir debug/work-dir
fi
export PYTHONPATH=$PWD
echo $PYTHONPATH
python bin/downpourd -c cfg/debug.cfg -d
