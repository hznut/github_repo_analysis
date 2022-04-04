#!/bin/sh

set -e

host="$1"
shift

#apt-get update && apt-get install -y default-mysql-client
#
#until mysql -h "$host" -u "$DB_USERNAME" -p "$DB_PASSWORD"; do
#  >&2 echo "MariaDB is unavailable - sleeping"
#  sleep 1
#done

sleep 15
#
#>&2 echo "MariaDB is up - executing command"
exec "$@"