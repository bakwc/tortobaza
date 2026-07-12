export NODE_OPTIONS="--max-old-space-size=4096"
git pull && npm run build:deploy && sudo systemctl restart tortobaza-frontend
