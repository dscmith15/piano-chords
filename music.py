"""Music theory helpers: note names and chord names from MIDI note numbers."""

# Notes are written as a letter plus an accidental. Letters are numbered
# up from C (C=0, D=1, ... B=6), and LETTER_PITCHES is each letter's pitch
# class with no accidental: the white keys.
LETTERS = "CDEFGAB"
LETTER_PITCHES = [0, 2, 4, 5, 7, 9, 11]

# An accidental moves a letter up or down by half steps. Written in text
# as: bb double flat, b flat, # sharp, x double sharp.
ACCIDENTAL_TEXT = {-2: "bb", -1: "b", 0: "", 1: "#", 2: "x"}

# Each black key has two names (C# = Db). With no chord to decide, use
# sharps: (letter, accidental) for pitch classes 0 to 11.
DEFAULT_SPELLING = [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (3, 0),
                    (3, 1), (4, 0), (4, 1), (5, 0), (5, 1), (6, 0)]


def spelled_name(letter, accidental):
    """Write a spelling as text: (2, -1) -> 'Eb'."""
    return LETTERS[letter] + ACCIDENTAL_TEXT[accidental]


def note_name(number, spelling=None):
    """Turn a MIDI note number into a name like 'C4' (60 -> C4).

    `spelling` is an optional (letter, accidental) pair, e.g. to write
    63 as Eb4 instead of D#4.
    """
    letter, accidental = spelling or DEFAULT_SPELLING[number % 12]
    # Octave numbers go with the letter: B#3 sounds the same as C4, so take
    # the accidental off before working out the octave.
    octave = (number - accidental) // 12 - 1  # MIDI note 0 is C-1
    return f"{spelled_name(letter, accidental)}{octave}"


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

# Chords are built by stacking every other letter (C E G B), so each chord
# tone sits a set number of letters above the root: the 3rd is 2 letters
# up, the 5th is 4, the 7th is 6. This maps a tone's half steps above the
# root to how many letters up it must be (9ths fold down to 2nds).
LETTER_STEPS = {0: 0, 2: 1, 3: 2, 4: 2, 5: 3, 6: 4, 7: 4, 8: 4, 9: 5, 10: 6, 11: 6}


def letter_steps(interval, shape):
    """How many letters above the root this chord tone is written."""
    if CHORDS[shape] == "dim7" and interval == 9:
        return 6  # in a dim7 chord this tone is the (double-flat) 7th
    return LETTER_STEPS[interval]


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


def accidental_between(pitch_class, letter):
    """The accidental that turns a letter into a pitch class: (3, 'E') -> -1 (Eb)."""
    # Wrap into -6..5 so going down a half step gives -1, not 11.
    return (pitch_class - LETTER_PITCHES[letter] + 6) % 12 - 6


def spell_chord(root, shape):
    """Choose letters for a chord's notes, e.g. Eb major -> Eb G Bb.

    Returns {pitch class: (letter, accidental)}. A black-key root is tried
    as both a sharp and a flat; the other letters follow from it (every
    other letter), and the spelling with the fewest accidentals wins.
    """
    best = None
    best_score = None
    for root_letter in range(7):
        root_accidental = accidental_between(root, root_letter)
        if abs(root_accidental) > 1:
            continue  # e.g. Eb can be D# but not Cx
        if root in LETTER_PITCHES and root_accidental != 0:
            continue  # a white-key root keeps its own name: C, not B#
        spelling = {}
        for interval in shape:
            letter = (root_letter + letter_steps(interval, shape)) % 7
            pitch_class = (root + interval) % 12
            spelling[pitch_class] = (letter, accidental_between(pitch_class, letter))

        score = sum(abs(accidental) for letter, accidental in spelling.values())
        # On a tie (F# A# C# vs Gb Bb Db), use the usual key name for the root.
        usual = spelled_name(*spelling[root]) == MAJOR_KEY_NAMES[root]
        if best is None or score < best_score or (score == best_score and usual):
            best = spelling
            best_score = score
    return best


def chord_names(notes):
    """Every name for the chord these MIDI notes make, e.g. ['C6', 'Am7']."""
    names = []
    for root, shape in chord_matches(notes):
        root_spelling = spell_chord(root, shape)[root]
        names.append(spelled_name(*root_spelling) + CHORDS[shape])
    return names


def note_spellings(notes):
    """How to spell each note, from the primary chord they make.

    Returns {pitch class: (letter, accidental)}, or {} when the notes don't
    make a chord (then the default sharp spellings are used).
    """
    matches = chord_matches(notes)
    if not matches:
        return {}
    root, shape = matches[0]
    return spell_chord(root, shape)


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

    # Check every chord tone sits on the right scale step above the root.
    # Comparing notes alone isn't enough: in C# minor, A-C-E has the right
    # notes, but its "C" is really B#, a note on the wrong step for a 3rd.
    for interval in shape:
        steps = letter_steps(interval, shape)
        if scale_notes[(degree + steps) % 7] != (root + interval) % 12:
            return None

    lowercase, ending = ROMAN_STYLE[CHORDS[shape]]
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


def staff_step(number, spelling=None):
    """Where a note sits on the grand staff, and its accidental.

    The step counts lines AND spaces above middle C, so each letter is one
    step: C4 = 0, D4 = 1, E4 = 2 (the treble staff's bottom line), B3 = -1.
    A sharp or flat sits on its letter's step: C#4 is (0, 1), Db4 is (1, -1).
    """
    letter, accidental = spelling or DEFAULT_SPELLING[number % 12]
    octave = (number - accidental) // 12 - 1
    return (octave - 4) * 7 + letter, accidental
