"""
Coordinate gazetteer for DESC + GPC substations/stations.

Confidence tiers:
  "confirmed"    - taken directly from the organizers' validated example
                   (Projects_Overlaps.xlsx), or is a real named town/city
                   whose coordinates are well-established public knowledge.
  "estimated"    - interpolated as the midpoint between two known points on
                   the same transmission line, used only when no direct
                   town/place match exists. Good enough for the 8/40 km
                   tiers, not precise enough to assert a "touching/crossing"
                   call without manual confirmation (per the challenge's
                   own guidance: public location data is limited).
  "region_only"  - no station-specific data; using the utility's broad
                   service-area or zone city as a stand-in, strictly to
                   filter out pairs that are obviously far apart.

Public location data for individual substations is genuinely sparse (most
coordinates below a named town/city are not published anywhere) -- this
mirrors the real-world constraint the challenge brief itself calls out.
"""

DESC_COORDS = {
    # confirmed - directly from the organizers' validated worked example
    "stevens creek": (33.562599, -82.051362, "confirmed", "organizer example"),
    "thurmond":      (33.660127, -82.195931, "confirmed", "organizer example"),
    "jasper":        (32.359120, -81.124600, "confirmed", "organizer example"),
    "okatie":        (32.333758, -81.032495, "confirmed", "organizer example"),
    "bluffton":      (32.235027, -80.853384, "confirmed", "organizer example"),
    "queensboro":    (32.722793, -79.967332, "confirmed", "organizer example"),

    # confirmed - real town/place names, well-known public coordinates
    "wagener":       (33.6493, -81.4076, "confirmed", "town of Wagener, SC"),
    "yemassee":      (32.6890, -80.8973, "confirmed", "town of Yemassee, SC"),
    "harleyville":   (33.2179, -80.4462, "confirmed", "town of Harleyville, SC"),
    "summerville":   (33.0185, -80.1756, "confirmed", "town of Summerville, SC"),
    "eastover":      (33.8721, -80.7048, "confirmed", "town of Eastover, SC"),
    "cainhoy":       (32.9296, -79.8681, "confirmed", "Cainhoy, Berkeley County SC"),
    "batesburg":     (33.9068, -81.5379, "confirmed", "town of Batesburg-Leesville, SC"),
    "st matthews":   (33.6668, -80.7726, "confirmed", "town of St. Matthews, SC"),
    "st george":     (33.1929, -80.5834, "confirmed", "town of St. George, SC"),
    "sumter":        (33.9204, -80.3414, "confirmed", "city of Sumter, SC"),

    # estimated - midpoint interpolation between two known line endpoints
    "hooks":         (33.6114, -82.1237, "estimated", "midpoint, Stevens Creek<->Thurmond line"),
    "toolebeck":     (33.4200, -81.7900, "estimated", "midpoint, Urquhart(Aiken)<->Toolebeck vicinity"),
    "aiken psa":     (33.5601, -81.7195, "estimated", "Aiken, SC city center (Urquhart-area tie)"),
    "urquhart":      (33.5200, -81.8500, "estimated", "DESC hydro station near Martinez/Augusta GA, Savannah River"),
    "ritter":        (32.9800, -81.0700, "estimated", "midpoint, Yemassee<->Canadys vicinity"),
    "canadys":       (33.0900, -80.8300, "estimated", "Canadys, Colleton County SC (community)"),

    # region_only - Charleston metro (far from GA border, > 100 km)
    "ft johnson": (32.7420, -79.9010, "region_only", "Charleston/James Island, SC"),
    "union pier": (32.7876, -79.9236, "region_only", "Charleston peninsula, SC"),
    "faber place": (32.8850, -80.0170, "region_only", "N. Charleston, SC"),
    "bayfront": (32.7900, -79.9250, "region_only", "Charleston, SC"),
    "hamlin": (32.8600, -79.8400, "region_only", "Mount Pleasant, SC"),
    "church creek": (32.7550, -80.0050, "region_only", "West Ashley/Charleston, SC"),
    "goose creek reservoir": (33.0100, -80.0300, "region_only", "Goose Creek, SC"),

    # region_only - Columbia metro (far from GA border, > 100 km)
    "hopkins": (33.9490, -80.8570, "region_only", "Hopkins, Richland County SC"),
    "cip": (34.0400, -80.9500, "region_only", "Columbia, SC"),
    "wateree": (34.2500, -80.7500, "region_only", "Wateree/Lugoff area, SC"),
    "killian": (34.1900, -80.8700, "region_only", "Killian, Richland County SC"),
    "coit": (34.0500, -80.9700, "region_only", "Columbia, SC"),
    "gills creek": (33.9700, -80.9500, "region_only", "Columbia, SC"),
    "vcs1": (34.0000, -81.0350, "region_only", "Columbia, SC (VC Summer/grid tie)"),
    "vcs2": (34.0000, -81.0350, "region_only", "Columbia, SC (VC Summer/grid tie)"),
    "denny terrace": (34.0500, -80.9800, "region_only", "Columbia, SC"),
    "pineland": (34.0300, -81.0100, "region_only", "Columbia, SC"),
    "ward": (33.9500, -81.2000, "region_only", "near Ward/Saluda, SC"),
    "williams st": (34.0000, -81.0300, "region_only", "Columbia, SC"),
    "williams": (34.0000, -81.0300, "region_only", "Columbia, SC"),
    "edenwood": (34.0000, -81.0300, "region_only", "Columbia, SC"),
    "scout": (34.0000, -81.0300, "region_only", "Columbia, SC"),
    "dawson": (34.0000, -81.0300, "region_only", "Columbia, SC"),
    "jack primus": (33.5000, -81.6000, "region_only", "Aiken County, SC"),

    # region_only - Orangeburg/Santee/Calhoun corridor (far from GA border)
    "cameron jct": (33.5900, -80.7000, "region_only", "Cameron, SC"),
    "cameron": (33.5900, -80.7000, "region_only", "Cameron, SC"),
    "elloree": (33.5300, -80.5700, "region_only", "Elloree, SC"),
    "santee city": (33.4800, -80.4800, "region_only", "Santee, SC"),
    "saluda county": (33.9000, -81.7700, "region_only", "Saluda County, SC"),
    "square d": (33.0185, -80.1756, "region_only", "near Summerville, SC"),
}

GPC_COORDS = {
    # confirmed - directly from the organizers' validated worked example
    "evans primary":  (33.543994, -82.168648, "confirmed", "organizer example"),
    "thurmond dam":   (33.660127, -82.195931, "confirmed", "organizer example"),
    "mcintosh":       (32.352116, -81.175112, "confirmed", "organizer example"),
    "goshen":         (32.248701, -81.209472, "confirmed", "organizer example"),
    "mitchell":       (31.447121, -84.133843, "confirmed", "organizer example"),
    "north tifton":   (31.478089, -83.549130, "confirmed", "organizer example"),
    "jesup":          (31.603106, -81.924947, "confirmed", "organizer example"),
    "ludowici primary": (31.721597, -81.743703, "confirmed", "organizer example"),

    # estimated / confirmed - Savannah zone (219) & Augusta/CSRA zone (215) additions
    "purrysburg":     (32.3400, -81.1600, "estimated", "near McIntosh, SC side of Savannah River"),
    "kraft":          (32.1000, -81.1000, "estimated", "Port Wentworth/Savannah, GA area"),
    "deptford":       (32.0500, -81.1500, "estimated", "Savannah, GA area"),
    "magnolia":       (32.0700, -81.1200, "estimated", "Savannah, GA area"),
    "cc":             (32.0809, -81.0912, "region_only", "Savannah, GA city center"),
    "hyundai motors savannah aka. project ea": (32.1500, -81.2500, "estimated", "Bryan County, GA (Hyundai Metaplant site)"),
    "little ogeechee": (32.0000, -81.1500, "estimated", "Savannah, GA area"),

    # region_only - Atlanta metro & rest of Georgia (far from SC border)
    "adamsville": (33.7700, -84.4900, "region_only", "Atlanta, GA"),
    "jack mcdonough": (33.7900, -84.3800, "region_only", "Atlanta, GA"),
    "echeconnee": (32.7800, -83.7000, "region_only", "Macon, GA area"),
    "wellston": (32.8000, -83.6500, "region_only", "Macon, GA area"),
    "grid": (33.6800, -85.0500, "region_only", "Bremen, GA area"),
    "bremen": (33.7100, -85.1400, "region_only", "Bremen, GA"),
    "crooked creek": (33.6800, -85.0500, "region_only", "Bremen, GA area"),
    "norcross": (33.9400, -84.2100, "region_only", "Norcross, GA"),
    "pine grove primary": (33.0000, -84.0000, "region_only", "central GA"),
    "villa rica": (33.7300, -84.9200, "region_only", "Villa Rica, GA"),
    "alcovy road": (33.6800, -83.8500, "region_only", "Covington, GA area"),
    "skc": (33.6800, -83.8500, "region_only", "Covington, GA area"),
    "bonaire primary": (32.6200, -83.5900, "region_only", "Bonaire, GA"),
    "aultman road": (32.6200, -83.5900, "region_only", "Bonaire, GA"),
    "eatonton primary": (33.3300, -83.3900, "region_only", "Eatonton, GA"),
    "lick creek": (33.3300, -83.3900, "region_only", "Eatonton, GA area"),
    "banks crossing": (34.5500, -83.4200, "region_only", "Banks County, GA"),
    "pond fork": (34.5500, -83.4200, "region_only", "north GA"),
    "camden industrial park": (30.9500, -81.6700, "region_only", "Camden County, GA (SE GA, not near SC border)"),
}
