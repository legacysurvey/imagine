#! /bin/bash

echo "Hello, I am desi-daily-cron.sh at $(date)"

export PATH=${PATH}:/app/src/astrometry/solver/startree

echo "SVN cleanup in local directory..."
(cd /desi-tiles-staging && svn cleanup)
echo "SVN up in local directory..."
(cd /desi-tiles-staging && svn up)

echo "Rsync to svn directory"
for x in /desi-tiles-staging/{*,.svn}; do
    echo "Rsync svn tile directory $x"
    rsync -rtv $x data/desi-tiles/
done
#rsync -rtv /desi-tiles-staging/{*,.svn} data/desi-tiles/

echo "Rebuild spectro kd-tree..."
python -u desi-daily.py
result=$?

echo "desi-daily-cron.sh finished at $(date) with return value $result"
exit $result
