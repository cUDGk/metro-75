# Metro-75: Day 0 Scenario

## Setting
**Precinct 28**, a working-class urban neighborhood somewhere in the northeastern United States. A 250×250-tile city grid bounded by highways to the north and south. Mixed residential + commercial, with pockets of industrial decay.

It's Tuesday, **October 15th**, 6:00 AM. Cold morning, light rain. Lights are coming on in apartment buildings. The night shift at St. Mary's Hospital is changing over.

## Factions at a Glance

| Faction | Territory | HQ |
|---|---|---|
| **NYPD 28th Precinct** | citywide | Police Station (center) |
| **West Side Kings** (blue) | NW quadrant | hideout at (32, 32) |
| **East End Bloods** (red) | SE quadrant | hideout at (217, 217) |
| **Stone Group** (vigilantes) | no fixed territory | meets at an apartment in SW |
| Civilians | everywhere | — |

## Ambient Conditions (Day 0)

### 1. The Ice Cream Truck
A **white-and-pink ice cream truck** has been parked on E. Jackson Street (around tile 146, 131) for **three straight days**. The chime plays once in the morning, once at dusk, but no one has actually been seen buying ice cream. A few residents have noted this on the block's message group.

The truck belongs to "Giovanni's Gelato" — a name nobody has heard of before. The driver is a thin man in his 40s, black baseball cap pulled low.

*Hint for observers: this may be a lookout post, a drug drop, or nothing at all.*

### 2. Unusual Police Presence
**Captain Diaz** took over the 28th Precinct three weeks ago and immediately ordered **doubled foot patrols**. Officers have been doing rolling sweeps of known drug corners. It's been effective at disrupting street sales — but the Kings and the Bloods are both losing money and getting twitchy.

Some whisper that Diaz has a **task force** operating undercover. Nobody knows who they are.

### 3. Mood in the Neighborhood
- Kings are nervous about losing corners, blaming Bloods for snitching to bring heat down
- Bloods are equally squeezed, convinced Kings have a rat giving them time to move product
- Stone Group has been quieter than usual — almost suspiciously so
- Father O'Neill at St. Mary's has been talking publicly about "praying for peace in these streets"
- Eddie the bartender at O'Reilly's is telling anyone who'll listen that "something's about to pop"

## No Scripted Events
There is **no predetermined murder, no inciting shoot-out**. The simulation starts quiet. Whatever happens over the next 75 days emerges from what the agents choose to do.

## Observer's Questions

As the sim runs, ask:
- Who figures out what the ice cream truck is (if anything)?
- Does Diaz's pressure break a gang first, or force them into uneasy cooperation?
- Does Stone or one of his group cross a line?
- Do the Kings and Bloods find out who (if anyone) is snitching?
- Does anyone figure out that the extra police presence includes undercover officers?
- How does Rivera (who grew up here) handle having to police his own neighbors?
- Does Keisha (Malik's girlfriend) make a move on the Bloods' top spot?

## Day 1 Starts
The sim tick begins at **06:00, Day 0**. Each active agent will act every **30 sim-minutes** (so ~48 decisions per agent per sim-day). The world state, every action, every word said in chat is logged.

Time speed: **1 sim-hour = 1 real-minute** for testing (1 sim-day ≈ 24 real-minutes). Adjust via `SIM_SPEED` env var in main.py.
