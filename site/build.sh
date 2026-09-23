#!/bin/sh
# Assemble the static Vercel site: only the demo assets, never the pipeline source or raw data.
set -e
rm -rf public
mkdir -p public/demo public/demo-jerusalem
cp site/index.html public/
cd poc/demo
cp index.html buildings.geojson stats.json top50.json ../../public/demo/
cd ../demo-jerusalem
cp index.html buildings.geojson plans.geojson boundary.geojson renewal.geojson \
   stats.json validation.json figure-6-beit-hakerem.jpg ../../public/demo-jerusalem/
cd ../..
echo "Built:"; find public -type f | sort
