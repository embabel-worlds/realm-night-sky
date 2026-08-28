---
name: night-sky
description: Answer questions about observing conditions, the moon, ISS passes, aurora chances and space weather at the places this world tracks. Use for "is tonight any good for stargazing", "where should I look up tonight", "when does it get dark", "how full is the moon", "when does the ISS go over", "any chance of aurora", or any question comparing the sky at several places.
---

# The night sky over this world's places

This realm adds no places of its own. It attaches the sky to places other
realms already hold — `WeatherLocation` from realm-weather and `UkPlace` from
realm-uk-streets — so every answer below is about somewhere the user already
told this world they care about.

## Run a view. Do not hand-write the Cypher.

Ten views cover the realm's whole answer surface, and each one already handles
two things that are easy to get wrong and impossible to notice when you get
them wrong.

| The question | The view |
|---|---|
| Is tonight worth it, and where? | `BestSkyTonight` — every place, both anchors, one ranking |
| Full conditions at the weather locations | `SkyTonight` |
| Full conditions at the UK places | `UkSkyTonight` |
| WHEN tonight should I go out? | `CloudThroughTheNight` — hour by hour, clearest hour picked out |
| How much moon is there? | `MoonAtMyPlaces` |
| When does the ISS go over? | `IssPassesAtMyPlaces`, `UkIssPasses` |
| Any chance of aurora? | `AuroraWatch`, `UkAuroraWatch` |
| What is the sun doing? | `SpaceWeatherForecast` |

## The two traps

**"Tonight" is a local idea and the twilight source answers for a UTC date.**
Every place therefore reaches TWO candidate nights, `HAS_DARK_WINDOW` (today
UTC) and `HAS_PRIOR_DARK_WINDOW` (yesterday UTC). Tonight is whichever opens
with a sunset falling on the place's own local date — which is also the night
the `SkyForecast` hours cover. Taking `HAS_DARK_WINDOW` on its own looks
perfectly fine from London and quietly describes the wrong night from San
Francisco. Every shipped view picks; a query you write by hand will not.

**Moon illumination is not a property.** MET Norway publishes a phase ANGLE in
degrees. The illuminated fraction is `(1 - cos(radians(phaseDegrees))) / 2`.
Reading `phaseDegrees` as a percentage gives a confident, wrong number — 180
degrees is a FULL moon, not an impossible one.

## Reading the answers out

- **Observing starts at astronomical dusk, not sunset.** The gap is over two
  hours in Britain in late summer. Quote `darkFromLocal`, not `sunsetLocal`.
- **`darkHours` under about four is a short night**, and above 50 degrees of
  latitude in June there is no astronomical night at all — the view says so in
  `verdict` rather than scoring it. That is a real answer about the sky, not a
  failure.
- **A full moon beats a clear sky.** A cloudless night at 100% illumination
  still scores badly, and that is correct: everything faint is washed out.
  Say why the score is low, because the user can see it is cloudless.
- **`moonFetchedForThisPlace: false`** means MET Norway could not be reached for
  that coordinate; the illuminated fraction shown was borrowed from another place,
  which is legitimate because lunar phase is global. Moonrise is genuinely
  local and is left null rather than invented.
- **An ISS pass has bearings.** "Rises 274, sets 95" is more use than a time on
  its own: it means low in the west, across the top, out to the east.
- **`auroraPossible: false` is the normal answer** at every latitude this world
  tracks, and reporting it plainly is the job. Do not soften a no into a maybe.
  `marginKp` says how far off it was.

## Warnings are not decoration

Every result carries `warnings`. A `PRODUCER_ERROR` means a source could not be
reached, and the rows you got are a partial answer, not the whole sky. Say which
places are missing and why. Zero rows plus a warning is a broken fetch; zero
rows with no warning is a quiet sky.
