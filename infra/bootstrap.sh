# This will function now as a general bootstrap script for Arch Linux, 
# testing locally first and then figuring out where I'll deploy the infra since the GCP trial is now done 

#!/bin/bash
set -e

# 1. Update system and install dependencies
pacman -Syu --noconfirm
pacman -S --noconfirm ca-certificates curl gnupg ufw fail2ban jq postgresql-libs base-devel

# 2. Install Docker & Docker Compose
# Docker is in the official Arch repos, no extra key setup needed
pacman -S --noconfirm docker docker-compose docker-buildx

# Enable and start Docker
systemctl enable docker
systemctl start docker

# 3. Setup basic OS Firewall (UFW) as defense-in-depth
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable

# 4. Create application directory
mkdir -p /opt/fbt
# Arch doesn't have an 'ubuntu' user by default — adjust to your actual user
# If you created a user during install (e.g., 'capomk'), use that:
chown -R $SUDO_USER:$SUDO_USER /opt/fbt 2>/dev/null || chown -R root:root /opt/fbt

# Note: In your deployment pipeline, you will scp your docker-compose.yml 
# and .env files to /opt/fbt, then run `docker compose up -d`.

echo "Bootstrap complete!"
