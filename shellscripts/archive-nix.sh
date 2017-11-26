#!/bin/bash

TODAY=`date +"%Y%m%d"`
ARCHIVENAME="film-archived-$TODAY"

if [ -z "$1" ] || [ -z "$2" ]
then
    echo "archive-nix [source dir] [backup dir]"
    echo
    echo "(Invalid Arguments)"
    echo
else
    cd "$2"

    filename=$ARCHIVENAME.tar.gz
    count=0

    while [[ -f $filename ]]; do
        count=$((count+1))

        filename=$ARCHIVENAME-$count.tar.gz
    done

    tar -cvzf $filename "$1"
fi

read -p "Press Return to continue..."
