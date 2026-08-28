# realm-night-sky

The sky above the places you already track.

Install it beside realm-weather and realm-uk-streets and every place those
realms hold quietly grows a night: when astronomical darkness actually falls,
how much moon is in the way, how cloudy it will be hour by hour through the
dark, when the ISS crosses over, and what the planetary K index says about
aurora at that latitude.

```cypher
MATCH (l:WeatherLocation)-[:HAS_DARK_WINDOW]->(d:DarkWindow)
MATCH (l)-[:HAS_SKY_FORECAST]->(f:SkyForecast)
RETURN l.name, d.astroDusk, f.cloudAt22
```

Nothing is stored. Five keyless sources are joined **on demand** onto
coordinates other realms already hold, so this is a pure enrichment layer — and
because the join is keyed on nothing but a latitude and a longitude, pointing it
at a third coordinate-bearing type is a four-line change in `types/night-sky.yml`.

## Sources

No API keys, no accounts, no configuration. All five are open.

| Source | What it gives |
|---|---|
| [sunrise-sunset.org](https://sunrise-sunset.org/api) | civil, nautical and astronomical twilight |
| [MET Norway](https://api.met.no/weatherapi/sunrise/3.0/documentation) | moonrise, moonset, culmination, phase angle |
| [Open-Meteo](https://open-meteo.com) | cloud cover and visibility, hour by hour |
| [NOAA SWPC](https://services.swpc.noaa.gov) | planetary K index, observed and forecast |
| [G7VRD](https://api.g7vrd.co.uk) | ISS pass predictions (self-declared ALPHA) |

## Views

`BestSkyTonight` is the one to run. It ranks every place this world tracks —
across both anchors, in a single query — by how clear and how dark tonight will
be. `SkyTonight` and `UkSkyTonight` give the full picture per anchor;
`CloudThroughTheNight` answers *when* rather than *whether*; `MoonAtMyPlaces`,
`IssPassesAtMyPlaces`, `UkIssPasses`, `AuroraWatch`, `UkAuroraWatch` and
`SpaceWeatherForecast` cover the rest.

## The Observatory

`apps/the-observatory.html` is the realm seen rather than queried — tonight
ranked across every tracked place, the night's cloud drawn hour by hour so the
clearest window is visible at a glance, the moon, upcoming ISS passes with the
bearings to look between, and the aurora outlook. It reads the views live on
every load, one call per panel, cached until you refresh.

## Three decisions worth knowing about

**"Tonight" is local; the twilight source answers for a UTC date.** So every
place reaches two candidate nights and the views pick the one whose sunset falls
on the place's own local date. Without that, a San Franciscan asking at 10pm is
told about tomorrow night while being shown tonight's cloud. It is the kind of
bug that never looks like one from London.

**Cloud is nine fixed local hours, not a fan-out.** Open-Meteo returns parallel
arrays, and with `timezone=auto` index N is local hour N at every place on
earth. Projecting hours 20 through 04 as nine properties makes one record per
place instead of nine, so a view can average them or find the clearest hour
without a join explosion.

**The moon is matched optionally.** MET Norway rejects a longitude rendered in
scientific notation, which is how a coordinate within a thousandth of a degree
of the Greenwich meridian used to arrive — an engine defect in small-float key
rendering, now fixed upstream. The optional match stays anyway: a realm cannot
assume its host's version, and a source failing for one place is a permanent
possibility, not one bug. Dropping those places from a ranking would be silent
and would look exactly like "nowhere good tonight", so instead the row survives,
flags `moonFetchedForThisPlace: false`, and borrows the illuminated fraction from
a place that resolved — legitimate, because lunar phase is a global quantity.
Moonrise, which is genuinely local, stays null.

## Testing

The declarative half of a realm has no unit tests, and its normal failure mode
is a join whose keys never match: zero rows, no error, indistinguishable from an
empty sky.

```bash
export EMBABEL_TOKEN=...
python3 scripts/test-views.py http://127.0.0.1:11043
```

Runs every view, fails on zero rows, surfaces every host warning, and reconciles
the figures against their sources — that the cloud mean really is the mean of
its own hours, that the illuminated fraction really is `(1-cos(phase))/2`, and
that the darkness window and the cloud hours are talking about the same night.

## Licence

Apache 2.0. Source data is each publisher's: MET Norway and Open-Meteo are
CC BY 4.0, NOAA SWPC is US public domain.
