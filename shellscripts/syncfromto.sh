#!/bin/bash

if [ -z "$1" ] || [ -z "$2" ]
then
    echo "syncfromto [from dir] [to dir]"
    echo
    echo "(Invalid Arguments)"
    echo
else
    echo "$1"
    echo "$2"

    rsync -rltDv --delete --exclude 'Footag*' --one-file-system --no-owner --no-perms --no-group $1 $2
fi

read -p "Press Return to continue..."
