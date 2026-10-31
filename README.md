# Piano Chords

A small screen for the piano stand that shows what you're playing, as you
play it: the notes, the chord's name, where it fits in a key, and the notes
drawn on a grand staff.

It's built for a Yamaha P-525 and a Raspberry Pi with a 5-inch screen, but
it works with any MIDI keyboard on any computer that runs Python.

This is also a learning project. It's built in small steps, one commit
each, so the history shows how it grew, and the code is commented to
explain the music theory, MIDI and Python as it goes.

## What it shows

- **Notes and chords.** Every note you're holding (or holding with the
  sustain pedal), and the chord they make: triads, 6ths, 7ths and 9ths, in
  any inversion. When the same notes have more than one name (C6 is also
  Am7), the other names are listed too.
- **Intervals.** Hold two notes and it names the distance between them
  (major 3rd, perfect 5th, minor 10th...).
- **Keys.** Every major and minor key the chord belongs to, with its Roman
  numeral in each (G7 is V7 in C major).
- **A grand staff.** Treble and bass clefs, with notes spelled correctly
  as sharps or flats for the chord and key, ledger lines, and 8va/8vb for
  very high and low notes.
- **Key mode.** Tap **Key** to choose a key. Then the screen shows:
  - the chord's job in that key (tonic, predominant, dominant), and the
    chords that usually come next;
  - secondary dominants (E7 in C major is V7/vi, which resolves to Am);
  - the key's scale on a mini keyboard. Notes you're playing are blue, or
    orange if they're outside the scale. Tap the scale to switch to
    pentatonic, blues, diminished or whole-tone scales.

## Running it

You need Python 3.9 or newer and a MIDI keyboard connected by USB (or
Bluetooth MIDI, once paired).

```bash
# 1. Make a virtual environment and install the libraries
python3 -m venv ~/chords
~/chords/bin/pip install -r requirements.txt

# 2. Run the app
~/chords/bin/python app.py
```

Press **Escape** or close the window to quit. If the keyboard isn't
connected yet, the app waits for it and connects when it appears.

To see the raw notes and chords in the terminal instead, run
`~/chords/bin/python midi_test.py` (Ctrl+C to stop).

> **Yamaha P-525 tip:** use the square **USB TO HOST** port, not the flat
> USB TO DEVICE port (that one is for flash drives and shows
> "incompatible device").

## How the code is organised

| File | What's in it |
|---|---|
| `music.py` | The music theory: note and chord names, intervals, keys, scales, Roman numerals, progressions, and sharp/flat spelling. No MIDI or screen code, so it's easy to read and test on its own. |
| `app.py` | The window: reads MIDI from the piano, keeps track of which notes are held, and draws everything with pygame about 60 times a second. |
| `midi_test.py` | A terminal version, handy for checking what the piano sends. |
| `fonts/` | Noto Music, used for clefs, sharps and flats. |

## Roadmap

- [x] Steps 1–6: MIDI, note and chord names, sustain pedal, the window,
      grand staff, spelling, keys, progressions, scales
- [ ] Step 7: run it on the Raspberry Pi with the 5-inch screen
- [ ] Step 8: connect the P-525 over Bluetooth MIDI
- [ ] Step 9: start automatically when the Pi boots

## Credits

- [mido](https://mido.readthedocs.io/) and
  [python-rtmidi](https://github.com/SpotlightKid/python-rtmidi) for MIDI
- [pygame](https://www.pygame.org/) for the screen
- [Noto Music](https://github.com/notofonts/music) font by the Noto Project
  Authors, used under the SIL Open Font License (see `fonts/OFL.txt`)
