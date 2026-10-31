"""Music theory helpers: note names and chord names from MIDI note numbers."""

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


def chord_matches(notes):
    """Every chord these MIDI notes make, as (root, shape) pairs.

    For C-E-G-A with C lowest: [(0, (0, 4, 7, 9)), (9, (0, 3, 7, 10))],
    meaning C6 and Am7. The first pair is the primary one. The list is
    empty if no chord fits.
    """
    # Drop the octaves: C3 and C5 are both pitch class 0 (C).
    pitch_classes = {n % 12 for n in notes}

    # Try each note as the root. Try the lowest (bass) note first, so
    # when notes fit more than one chord, the bass note's chord comes first.
    bass = min(notes) % 12
    roots = [bass] + sorted(pitch_classes - {bass})

    matches = []
    for root in roots:
        # Measure every note's distance above this root, in half steps.
        shape = tuple(sorted((pc - root) % 12 for pc in pitch_classes))
        if shape in CHORDS:
            matches.append((root, shape))
    return matches


def chord_names(notes):
    """Every name for the chord these MIDI notes make, e.g. ['C6', 'Am7']."""
    return [NOTE_NAMES[root] + CHORDS[shape] for root, shape in chord_matches(notes)]


# Key names, written the way musicians do: flat keys use flats (Bb, not A#).
# Minor keys borrow the spelling of the major key with the same key
# signature, so it's F#m (relative of A major), not Gbm.
MAJOR_KEY_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
MINOR_KEY_NAMES = ["Cm", "C#m", "Dm", "Ebm", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "Bbm", "Bm"]

# Scales, as half steps above their first note (the tonic).
# Major: whole, whole, half, whole, whole, whole, (half back to the tonic).
MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)
# Natural minor: the same notes as the major scale starting on its 6th note.
NATURAL_MINOR_SCALE = (0, 2, 3, 5, 7, 8, 10)
# Harmonic minor: natural minor with the 7th raised a half step (10 -> 11),
# which gives minor keys their strong V7 chord (E7 in A minor).
HARMONIC_MINOR_SCALE = (0, 2, 3, 5, 7, 8, 11)

# A chord's Roman numeral is the scale step its root is on.
NUMERALS = ["I", "II", "III", "IV", "V", "VI", "VII"]

# Chords are built by stacking every other scale note, so each chord tone
# must sit a set number of scale steps above the root: the 3rd is 2 steps
# up, the 5th is 4, the 7th is 6. This maps a tone's half steps above the
# root to how many scale steps up it must be (9ths fold down to 2nds).
SCALE_STEPS = {0: 0, 2: 1, 3: 2, 4: 2, 5: 3, 6: 4, 7: 4, 8: 4, 9: 5, 10: 6, 11: 6}

# How each chord type is written as a Roman numeral: (lowercase?, ending).
# Major-sounding chords are UPPERCASE (V), minor-sounding ones lowercase (ii).
# 6 chords get "add6" because a plain "6" after a numeral means an inversion.
ROMAN_STYLE = {
    "": (False, ""),          "m": (True, ""),
    "dim": (True, "°"),       "aug": (False, "+"),
    "sus2": (False, "sus2"),  "sus4": (False, "sus4"),
    "7": (False, "7"),        "maj7": (False, "maj7"),
    "m7": (True, "7"),        "dim7": (True, "°7"),
    "m7b5": (True, "ø7"),
    "6": (False, "add6"),     "m6": (True, "add6"),
    "add9": (False, "add9"),  "madd9": (True, "add9"),
    "9": (False, "9"),        "maj9": (False, "maj9"),
    "m9": (True, "9"),
}


def numeral_in_key(root, shape, tonic, scale):
    """The chord's Roman numeral in this key (e.g. 'V7'), or None if it doesn't fit."""
    scale_notes = [(tonic + step) % 12 for step in scale]  # e.g. C D E F G A B
    if root not in scale_notes:
        return None
    degree = scale_notes.index(root)  # 0 = tonic, 4 = the 5th note, ...
    suffix = CHORDS[shape]

    # Check every chord tone sits on the right scale step above the root.
    # Comparing notes alone isn't enough: in C# minor, A-C-E has the right
    # notes, but its "C" is really B#, a note on the wrong step for a 3rd.
    for interval in shape:
        steps = SCALE_STEPS[interval]
        if suffix == "dim7" and interval == 9:
            steps = 6  # in a dim7 chord this tone is the (double-flat) 7th
        if scale_notes[(degree + steps) % 7] != (root + interval) % 12:
            return None

    lowercase, ending = ROMAN_STYLE[suffix]
    numeral = NUMERALS[degree].lower() if lowercase else NUMERALS[degree]
    return numeral + ending


def first_numeral(matches, tonic, scale):
    """The Roman numeral of the first chord name that fits this key, or None.

    The primary name is tried first. Another name only wins when the
    primary doesn't fit, e.g. a dim7 chord, which can be named from any note.
    """
    for root, shape in matches:
        numeral = numeral_in_key(root, shape, tonic, scale)
        if numeral:
            return numeral
    return None


def chord_keys(notes):
    """The keys this chord belongs to, with its Roman numeral in each.

    Returns two lists of (key, numeral) pairs, major keys and minor keys:
    for a C chord, ([('C', 'I'), ('F', 'V'), ('G', 'IV')], [('Dm', 'VII'), ...]).
    """
    matches = chord_matches(notes)
    major_keys = []
    minor_keys = []
    for tonic in range(12):
        numeral = first_numeral(matches, tonic, MAJOR_SCALE)
        if numeral:
            major_keys.append((MAJOR_KEY_NAMES[tonic], numeral))
        # Minor keys use both versions of the 7th, so try both scales.
        numeral = (first_numeral(matches, tonic, NATURAL_MINOR_SCALE)
                   or first_numeral(matches, tonic, HARMONIC_MINOR_SCALE))
        if numeral:
            minor_keys.append((MINOR_KEY_NAMES[tonic], numeral))
    return major_keys, minor_keys
