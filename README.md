# Kennywood Navigator

A 3D night map of Kennywood for your phone: live GPS, every ride, food stand, haunt and restroom from the 2026 Fall Fest map, walking directions over the park's real footpaths, live wait times, and a checklist for rides you've done.

Live at https://vishhvak.github.io/kennywood/

- Geometry: OpenStreetMap (ODbL), fetched with the Overpass API.
- Places: the official 2026 Fall Fest park map, georeferenced against OSM-surveyed rides (affine fit plus inverse-distance residual correction; 7.4 m median leave-one-out error).
- Waits: Queue-Times.com (refreshed into the site every 5 minutes by the Deploy workflow) and ThemeParks.wiki (fetched live), newest per ride.

`src/build.py` builds the map data from an Overpass export and `pdftotext -bbox` output of the official map; `src/index.src.html` is the page template.

Not affiliated with Kennywood.
