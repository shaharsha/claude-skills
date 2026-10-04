# Before you send the episode

Check every item. A failed item is fixed, rebuilt in the same batch as the other fixes, and checked again.

**Build**
- [ ] `episode.py PROJECT check` shows 0 blockers and no "wider than the frame" warning.
- [ ] The build log has no "music cue ... will stop early" warning.
- [ ] The build ended with `video X s audio Y s` and no duration error.

**Picture** (`episode.py PROJECT sheet`, then read every sheet)
- [ ] Every shot shows what the script says: right characters, no doubled props, no extra people or doors.
- [ ] Every subtitle is readable at speed: on screen for the whole line, not covering a face that is talking.
- [ ] No Latin respellings in the subtitles of a non-English episode.
- [ ] Cards and captions stay up long enough (about 1.2-1.5 s per short card, 4-6 s for the final caption).
- [ ] In the group shot, faces are about the same size and none is covered.
- [ ] Lip-synced shots: 3 frames each, the speaking mouth is the right one.

**Sound**
- [ ] Loudness is sane: `ffmpeg -i build/<output>.mp4 -af ebur128 -f null - 2>&1 | grep "I:"` reports about -15 LUFS.
- [ ] Music covers every scene it should, including the last card before it ends.
- [ ] The human has listened to the whole episode, and you sent them a list of the spots to check, with timestamps (names, one-word lines, words under music).

**Delivery**
- [ ] `episode.py PROJECT deliver` produced `build/<output>_whatsapp.mp4` under 100 MB.
- [ ] Sent with your file-sending tool; offered to reveal it in Finder.
