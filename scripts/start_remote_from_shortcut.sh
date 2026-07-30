#!/bin/zsh
# Start VLC Remote from the restricted iPhone Shortcut SSH key.
#
# This file is installed into the app's Application Support directory because
# macOS does not allow SSH sessions to read a project stored on Desktop.

set -eu

readonly remote_port=8000
readonly state_directory="$HOME/Library/Application Support/MacVlcRemote"
readonly access_token_file="$state_directory/access-token"

/usr/bin/open -a "VLC Remote"

for attempt in {1..40}; do
  if /usr/bin/nc -z -w 1 127.0.0.1 "$remote_port" 2>/dev/null; then
    break
  fi
  sleep 0.5
done

if ! /usr/bin/nc -z -w 1 127.0.0.1 "$remote_port" 2>/dev/null; then
  print -u2 "VLC Remote did not start within 20 seconds."
  exit 1
fi

if [[ ! -r "$access_token_file" ]]; then
  print -u2 "VLC Remote started, but its local pairing token is unavailable."
  exit 1
fi

local_host_name="$(/usr/sbin/scutil --get LocalHostName)"
access_token="$(<"$access_token_file")"
if [[ -z "$local_host_name" || ! "$access_token" =~ '^[A-Za-z0-9_-]{32,}$' ]]; then
  print -u2 "VLC Remote started, but its local pairing link could not be created."
  exit 1
fi

print -r -- "http://${local_host_name}.local:${remote_port}/#token=${access_token}"
