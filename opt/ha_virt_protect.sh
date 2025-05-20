#!/bin/bash

cmd="$SSH_ORIGINAL_COMMAND"

# Allow specific virsh commands with qemu:///system only
if [[ "$cmd" =~ ^virsh\ -c\ qemu:///system\ (list\ --all\ --name|dominfo\ [a-zA-Z0-9._-]+|domstate\ [a-zA-Z0-9._-]+|start\ [a-zA-Z0-9._-]+|shutdown\ [a-zA-Z0-9._-]+|suspend\ [a-zA-Z0-9._-]+|resume\ [a-zA-Z0-9._-]+|snapshot-create-as\ [a-zA-Z0-9._-]+\ [a-zA-Z0-9._-]+|snapshot-revert\ [a-zA-Z0-9._-]+\ [a-zA-Z0-9._-]+|snapshot-delete\ [a-zA-Z0-9._-]+\ [a-zA-Z0-9._-]+|domifaddr\ [a-zA-Z0-9._-]+\ --source\ agent|screenshot\ [a-zA-Z0-9._-]+\ /tmp/[a-zA-Z0-9._-]+\.ppm\ --screen\ 0)$ ]]; then
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
