#!/bin/sh
set -eu
: "${WEBHOOK_PORT:=8081}"

envsubst '$WEBHOOK_PORT' \
  < /etc/nginx/conf.d/default.conf.template \
  > /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
