#!/bin/bash
#script to protect the ssh connection. 
# add 
# command="/usr/local/bin/ha_virt_protect.sh",no-port-forwarding,no-X11-forwarding,no-agent-forwarding ssh-ed25519 <KEY>
# to the authorized_keys of the linux host.

cmd="$SSH_ORIGINAL_COMMAND"

# Allow all virsh commands, optionally with -c URI
if [[ "$cmd" =~ ^virsh(\ -c\ [^[:space:]]+)?\ .+ ]]; then
  eval "$cmd"

# Allow only base64 on files in /tmp ending in .png
elif [[ "$cmd" =~ ^base64\ /tmp/[a-zA-Z0-9._-]+\.png$ ]]; then
  eval "$cmd"

# Allow only convert from .ppm to .png in /tmp
elif [[ "$cmd" =~ ^convert\ /tmp/[a-zA-Z0-9._-]+\.ppm\ /tmp/[a-zA-Z0-9._-]+\.png$ ]]; then
  eval "$cmd"

# Deny everything else
else
  echo "Command not allowed"
fi
