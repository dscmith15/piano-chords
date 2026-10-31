import mido

# The 12 note names in one octave. A note's position in this list
# is its MIDI note number % 12 (C = 0, C# = 1, ... B = 11).
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name(number):
    """Turn a MIDI note number into a name like 'C4' (60 -> C4)."""
    name = NOTE_NAMES[number % 12]
    octave = number // 12 - 1  # MIDI note 0 is C-1, so subtract 1
    return f"{name}{octave}"


# Chord shapes, as half-step distances from the root, mapped to the
# suffix written after the root's name (C + "m7" -> "Cm7").
CHORDS = {
    (0, 4, 7): "",            # major: root, major 3rd, perfect 5th
    (0, 3, 7): "m",           # minor: root, minor 3rd, perfect 5th
    (0, 3, 6): "dim",         # diminished: minor 3rd, flattened 5th
    (0, 4, 8): "aug",         # augmented: major 3rd, raised 5th
    (0, 2, 7): "sus2",        # 2nd instead of the 3rd
    (0, 5, 7): "sus4",        # 4th instead of the 3rd
    (0, 4, 7, 10): "7",       # dominant 7th: major triad + minor 7th
    (0, 4, 7, 11): "maj7",    # major 7th: major triad + major 7th
    (0, 3, 7, 10): "m7",      # minor 7th: minor triad + minor 7th
    (0, 3, 6, 9): "dim7",     # diminished 7th: stacked minor 3rds
    (0, 3, 6, 10): "m7b5",    # half-diminished: dim triad + minor 7th
    (0, 4, 7, 9): "6",        # major 6th: major triad + major 6th
    (0, 3, 7, 9): "m6",       # minor 6th: minor triad + major 6th
    # A 9th is an octave + a 2nd (14 half steps); % 12 folds it to 2.
    (0, 2, 4, 7): "add9",     # major triad + 9th, no 7th
    (0, 2, 3, 7): "madd9",    # minor triad + 9th, no 7th
    (0, 2, 4, 7, 10): "9",    # dominant 9th: dominant 7th + 9th
    (0, 2, 4, 7, 11): "maj9",  # major 9th: major 7th + 9th
    (0, 2, 3, 7, 10): "m9",   # minor 9th: minor 7th + 9th
    # Pianists often leave out the 5th in 9th chords, so match those too.
    (0, 2, 4, 10): "9",
    (0, 2, 4, 11): "maj9",
    (0, 2, 3, 10): "m9",
}


def chord_names(notes):
    """Every name for the chord these MIDI notes make, e.g. ['C6', 'Am7'].

    The first name is the primary one. The list is empty if no chord fits.
    """
    # Drop the octaves: C3 and C5 are both pitch class 0 (C).
    pitch_classes = {n % 12 for n in notes}

    # Try each note as the root. Try the lowest (bass) note first, so
    # when notes fit more than one chord, the bass note's name comes first.
    bass = min(notes) % 12
    roots = [bass] + sorted(pitch_classes - {bass})

    names = []
    for root in roots:
        # Measure every note's distance above this root, in half steps.
        shape = tuple(sorted((pc - root) % 12 for pc in pitch_classes))
        if shape in CHORDS:
            names.append(NOTE_NAMES[root] + CHORDS[shape])
    return names


def show(notes):
    """Print notes from lowest to highest, plus the chord if there is one."""
    if not notes:
        print("(silence)")
        return
    names = " ".join(note_name(n) for n in sorted(notes))
    chords = chord_names(notes)
    if not chords:
        print(names)
    elif len(chords) == 1:
        print(f"{names}   ->  {chords[0]}")
    else:
        # chords[0] is the primary name; chords[1:] is everything after it.
        also = ", ".join(chords[1:])
        print(f"{names}   ->  {chords[0]}  (also {also})")


SUSTAIN_PEDAL = 64  # the standard MIDI control number for the sustain pedal

held = set()       # keys your fingers are holding down right now
sustained = set()  # keys you let go of that the pedal is keeping alive
pedal_down = False

print(mido.get_input_names())

with mido.open_input() as port:
    for msg in port:
        if msg.type == "note_on" and msg.velocity > 0:
            held.add(msg.note)
            sustained.discard(msg.note)  # it's held by a finger again
        elif msg.type == "note_off" or msg.type == "note_on":
            # Some keyboards send note_on with velocity 0 to mean "released".
            held.discard(msg.note)
            if pedal_down:
                sustained.add(msg.note)
        elif msg.type == "control_change" and msg.control == SUSTAIN_PEDAL:
            # value runs 0 (up) to 127 (down); 64 or more counts as down.
            now_down = msg.value >= 64
            if now_down == pedal_down:
                continue  # a small pedal movement, no change: don't print
            pedal_down = now_down
            if not pedal_down:
                sustained.clear()  # pedal up: sustained notes stop
        else:
            continue  # ignore everything else and skip the print below

        # | joins two sets: every note that is held OR sustained.
        show(held | sustained)
