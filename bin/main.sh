#!/bin/sh
while [ -n "$2" ] ; do
     case "$1" in
         -b | --bundle-id)     export SUGAR_BUNDLE_ID="$2" ;;
         -a | --activity-id)   export SUGAR_ACTIVITY_ID="$2" ;;
         -o | --object-id)     export SUGAR_OBJECT_ID="$2" ;;
         -u | --uri)           export SUGAR_URI="$2" ;;
         *) echo unknown argument $1 $2 ;;
     esac
     shift;shift
done

export LD_LIBRARY_PATH=$SUGAR_BUNDLE_PATH/lib:$LD_LIBRARY_PATH
export LD_PRELOAD=$SUGAR_BUNDLE_PATH/lib/libsugarize.so
export NET_WM_NAME="DGI"
cd $SUGAR_BUNDLE_PATH/game/
python -O main.py