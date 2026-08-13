---
description: RETIRED 2026-08-12 — there is nothing to arm. Native messaging needs no setup.
---

# Retired. There is nothing to arm.

`ccarm`, `ccsend --self` and the `FRESH LEASE` check are gone. Cross-session messaging is on for
every session ≥ **v2.1.224** with nothing to enable. Below that version a session binds no socket,
appears in no listing, and **looks normal from the inside**.

**Where the content that used to live here now lives — one copy each, deliberately:**

```
addressing · TITLE vs NAME · ccpeers      /dispatch §1   ·  /worker §1
channel failure modes (HELD/CAPPED/…)     /dispatch "The channel is better…"
what carries what, RECORD vs MESSAGE      LANE-PREAMBLE.md §8
who is stuck                              ccstatus — messaging never answered this
```

⚠️ **Do not re-add that material here.** This file was a third copy of rules that already had homes,
and a rule written in two places for two readers is a disagreement waiting to be found by whoever is
caught between them. Delete this file rather than growing it.
