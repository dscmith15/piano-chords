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
    (0, 3, 7, 11): "mMaj7",   # minor-major 7th: minor triad + major 7th
    (0, 3, 6, 11): "dimMaj7",  # diminished-major 7th: dim triad + major 7th
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


def spell_from_letter(root, shape, root_letter):
    """Spell a chord once its root's letter is chosen: the other letters
    follow from it (every other letter). Returns {pitch class: (letter, accidental)}."""
    spelling = {}
    for interval in shape:
        letter = (root_letter + letter_steps(interval, shape)) % 7
        pitch_class = (root + interval) % 12
        spelling[pitch_class] = (letter, accidental_between(pitch_class, letter))
    return spelling


def spell_chord(root, shape):
    """Choose letters for a chord's notes, e.g. Eb major -> Eb G Bb.

    Returns {pitch class: (letter, accidental)}. A black-key root is tried
    as both a sharp and a flat, and the spelling with the fewest
    accidentals wins.
    """
    best = None
    best_score = None
    for root_letter in range(7):
        root_accidental = accidental_between(root, root_letter)
        if abs(root_accidental) > 1:
            continue  # e.g. Eb can be D# but not Cx
        if root in LETTER_PITCHES and root_accidental != 0:
            continue  # a white-key root keeps its own name: C, not B#
        spelling = spell_from_letter(root, shape, root_letter)

        score = sum(abs(accidental) for letter, accidental in spelling.values())
        # On a tie (F# A# C# vs Gb Bb Db), use the usual key name for the root.
        usual = spelled_name(*spelling[root]) == MAJOR_KEY_NAMES[root]
        if best is None or score < best_score or (score == best_score and usual):
            best = spelling
            best_score = score
    return best


def chord_names(notes, key=None):
    """Every name for the chord these MIDI notes make, e.g. ['C6', 'Am7'].

    With a key, e.g. (6, False) for F# major, the name that fits the key
    comes first and is spelled with the key's letters (D#m, not Ebm).
    """
    names = []
    for root, shape in chord_matches(notes):
        root_spelling = spell_chord(root, shape)[root]
        names.append(spelled_name(*root_spelling) + CHORDS[shape])

    in_key = chord_in_key(notes, key) if key and names else None
    if in_key:
        root, shape, root_letter = in_key
        position = chord_matches(notes).index((root, shape))
        names.pop(position)
        root_spelling = spell_from_letter(root, shape, root_letter)[root]
        names.insert(0, spelled_name(*root_spelling) + CHORDS[shape])
    return names


def note_spellings(notes, key=None):
    """How to spell each note, from the primary chord they make.

    With a key, a chord that fits it uses the key's letters. Returns
    {pitch class: (letter, accidental)}, or {} when the notes don't make a
    chord (then the default sharp spellings are used).
    """
    matches = chord_matches(notes)
    if not matches:
        return interval_spellings(notes, key) if len(notes) == 2 else {}
    in_key = chord_in_key(notes, key) if key else None
    if in_key:
        return spell_from_letter(*in_key)
    root, shape = matches[0]
    return spell_chord(root, shape)


def primary_chord(notes, key=None):
    """The chord the big name shows, as (root, shape), or None.

    Like chord_names: with a key, a chord that fits the key comes first.
    """
    matches = chord_matches(notes)
    if not matches:
        return None
    in_key = chord_in_key(notes, key) if key else None
    if in_key:
        root, shape, root_letter = in_key
        return root, shape
    return matches[0]


def interval_label(interval, shape):
    """A chord tone's job, counted up from the root, as (degree, text).

    The number is how many letters up it is, counting the root as 1, so
    the 3rd is 2 letters above the root. The accidental compares it with
    the major scale: a minor 3rd (3 half steps, 1 less than the major
    scale's 4) is "b3". (3, Cm's shape) -> (3, "b3").
    """
    if interval == 0:
        return 1, "R"
    steps = letter_steps(interval, shape)
    degree = steps + 1
    if degree == 2 and (3 in shape or 4 in shape):
        degree = 9  # with a 3rd as well, the 2nd is called the 9th (Cadd9)
    accidental = interval - MAJOR_SCALE[steps]
    return degree, ACCIDENTAL_TEXT[accidental] + str(degree)


def chord_intervals(shape):
    """Every chord tone's label, stacked up from the root:
    (0, 2, 4, 7, 11) -> ['R', '3', '5', '7', '9']."""
    labels = sorted(interval_label(interval, shape) for interval in shape)
    return [text for degree, text in labels]  # sorted by degree: 9 after 7


# Which chord tone is in the bass, by how many letters it is above the root.
INVERSIONS = {0: "Root position", 2: "1st inversion", 4: "2nd inversion", 6: "3rd inversion"}


def chord_position(notes, root, shape):
    """Which chord tone is lowest: root position, or an inversion.

    In an inversion the root moves up and another chord tone takes the
    bass: C/E (E lowest, the 3rd) is the 1st inversion of C.
    """
    bass_interval = (min(notes) - root) % 12
    steps = letter_steps(bass_interval, shape)
    if steps in INVERSIONS:
        return INVERSIONS[steps]
    # A tone that isn't a 3rd, 5th or 7th, like the 9th: just name it.
    return interval_label(bass_interval, shape)[1] + " in the bass"


def chord_voicing(notes):
    """"Close" if the notes are packed together, "Open" if they're spread out.

    Chords are stacks of 3rds, so in a close voicing no two neighbouring
    notes are more than a 4th (5 half steps) apart: C4 E4 G4 is close, and
    so is G3 C4 E4. C3 G3 E4 is open: C3 to G3 is a 5th, room for an E.
    """
    ordered = sorted(notes)
    for low, high in zip(ordered, ordered[1:]):  # each neighbouring pair
        if high - low > 5:
            return "Open"
    return "Close"


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
    "mMaj7": (True, "maj7"),  "dimMaj7": (True, "°maj7"),
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


def first_fit(matches, tonic, scale):
    """The first chord name that fits this key, as (root, shape, numeral), or None.

    The primary name is tried first. Another name only wins when the
    primary doesn't fit, e.g. a dim7 chord, which can be named from any note,
    or when it's built on the key's home note: C-E-G-A in A minor is Am7
    (i7), not C6.
    """
    fits = []
    for root, shape in matches:
        numeral = numeral_in_key(root, shape, tonic, scale)
        if numeral:
            fits.append((root, shape, numeral))
    for fit in fits:
        if fit[0] == tonic:
            return fit
    return fits[0] if fits else None


def fit_in_key(notes, tonic, minor):
    """How the chord fits one key, as (root, shape, numeral), or None if it doesn't.

    `tonic` is the key's pitch class (0 = C) and `minor` is True for a minor key.
    """
    matches = chord_matches(notes)
    if minor:
        # Minor keys use both versions of the 7th, so try both scales.
        return (first_fit(matches, tonic, NATURAL_MINOR_SCALE)
                or first_fit(matches, tonic, HARMONIC_MINOR_SCALE))
    return first_fit(matches, tonic, MAJOR_SCALE)


def chord_numeral(notes, tonic, minor):
    """The chord's Roman numeral in one key (e.g. 'V7'), or None if it's not in it."""
    fit = fit_in_key(notes, tonic, minor)
    return fit[2] if fit else None


def chord_keys(notes):
    """The keys this chord belongs to, with its Roman numeral in each.

    Returns two lists of (key, numeral) pairs, major keys and minor keys:
    for a C chord, ([('C', 'I'), ('F', 'V'), ('G', 'IV')], [('Dm', 'VII'), ...]).
    """
    major_keys = []
    minor_keys = []
    for tonic in range(12):
        numeral = chord_numeral(notes, tonic, minor=False)
        if numeral:
            major_keys.append((MAJOR_KEY_NAMES[tonic], numeral))
        numeral = chord_numeral(notes, tonic, minor=True)
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


# The basic chord on each step of a key: numeral -> (half steps from the
# tonic, chord suffix, its job in the key). Musicians group chords by job:
#   tonic        - home, restful
#   predominant  - moves away from home, usually toward the dominant
#   dominant     - tense, wants to resolve home
MAJOR_KEY_CHORDS = {
    "I": (0, "", "tonic: home"),
    "ii": (2, "m", "predominant: leads to V"),
    "iii": (4, "m", "tonic family: often goes to vi"),
    "IV": (5, "", "predominant: leads to V or home"),
    "V": (7, "", "dominant: wants to resolve to I"),
    "vi": (9, "m", "tonic family: the relative minor"),
    "vii°": (11, "dim", "dominant family: resolves to I"),
}
# Minor keys mix natural minor (VII) and harmonic minor (V, vii°).
MINOR_KEY_CHORDS = {
    "i": (0, "m", "tonic: home"),
    "ii°": (2, "dim", "predominant: leads to V"),
    "III": (3, "", "tonic family: the relative major"),
    "iv": (5, "m", "predominant: leads to V or home"),
    "V": (7, "", "dominant: wants to resolve to i"),
    "VI": (8, "", "predominant: often goes to iv or V"),
    "VII": (10, "", "subtonic: often goes to III"),
    "vii°": (11, "dim", "dominant family: resolves to i"),
}

# Where each chord most often goes next, most common first.
MAJOR_NEXT = {
    "I": ["IV", "V", "vi"],
    "ii": ["V", "vii°"],
    "iii": ["vi", "IV"],
    "IV": ["V", "I", "ii"],
    "V": ["I", "vi"],         # V -> vi is the "deceptive cadence": a surprise
    "vi": ["ii", "IV", "V"],
    "vii°": ["I"],
}
MINOR_NEXT = {
    "i": ["iv", "V", "VI"],
    "ii°": ["V"],
    "III": ["VI", "iv"],
    "iv": ["V", "i"],
    "V": ["i", "VI"],
    "VI": ["iv", "ii°", "V"],
    "VII": ["III", "i"],
    "vii°": ["i"],
}


def tonic_letter(tonic, minor):
    """The letter of a key's home note, from its name: F# major -> 3 (F)."""
    key_name = MINOR_KEY_NAMES[tonic] if minor else MAJOR_KEY_NAMES[tonic]
    return LETTERS.index(key_name[0])


def key_letter(tonic, minor, numeral):
    """The letter of a key chord's root: V in F# major -> 0 (C, spelled C#)."""
    # A key's scale uses each letter once, starting from the tonic's letter,
    # so step V of an F# key is 4 letters up from F: C.
    degree = NUMERALS.index(numeral.upper().rstrip("°"))
    return (tonic_letter(tonic, minor) + degree) % 7


def key_scale(tonic, minor):
    """The notes of a key's scale, in order, as (pitch class, name, optional).

    Each scale step uses the next letter up from the tonic. Minor keys use
    natural minor, plus the raised 7th from harmonic minor marked optional:
    A minor -> A B C D E F G, and (G#) as an option.
    """
    scale = NATURAL_MINOR_SCALE if minor else MAJOR_SCALE
    notes = []
    for degree, offset in enumerate(scale):
        pitch_class = (tonic + offset) % 12
        letter = (tonic_letter(tonic, minor) + degree) % 7
        notes.append((pitch_class, spelled_name(letter, accidental_between(pitch_class, letter)), False))
    if minor:
        pitch_class = (tonic + 11) % 12  # the raised 7th: same letter as the 7th
        letter = (tonic_letter(tonic, minor) + 6) % 7
        notes.append((pitch_class, spelled_name(letter, accidental_between(pitch_class, letter)), True))
    return notes


def key_chord_name(tonic, minor, numeral):
    """Name a key's chord with the key's own letters: IV in Eb major -> 'Ab'."""
    offset, suffix, _ = (MINOR_KEY_CHORDS if minor else MAJOR_KEY_CHORDS)[numeral]
    letter = key_letter(tonic, minor, numeral)
    root = (tonic + offset) % 12
    return spelled_name(letter, accidental_between(root, letter)) + suffix


# The three-note chord shapes by suffix: "" -> (0, 4, 7), "m" -> (0, 3, 7), ...
TRIADS = {suffix: shape for shape, suffix in CHORDS.items() if len(shape) == 3}


def key_chord_notes(tonic, minor, numeral):
    """The pitch classes of a key's chord: IV in C major -> {5, 9, 0} (F A C)."""
    offset, suffix, _ = (MINOR_KEY_CHORDS if minor else MAJOR_KEY_CHORDS)[numeral]
    root = (tonic + offset) % 12
    return {(root + interval) % 12 for interval in TRIADS[suffix]}


def nearest(note, pitch_class):
    """The closest MIDI note to `note` with this pitch class (up on a tie):
    nearest(64, 5) -> 65 (E4 to F4), nearest(67, 0) -> 72 (G4 to C5)."""
    up = (pitch_class - note) % 12  # half steps up to it, 0 to 11
    return note + up if up <= 6 else note + up - 12


def voice_lead(notes, pitch_classes):
    """Smooth voice leading: move each note the shortest way into the next chord.

    Notes the two chords share stay put, and the rest move by a step or
    so. C4 E4 G4 to F major (F A C) -> C4 F4 A4: C stays, E goes up a half
    step, G up a whole step. Returns the new notes, lowest first.
    """
    # 1. Each note goes to the closest note of the next chord.
    moved = {}
    for note in notes:
        options = [nearest(note, pc) for pc in pitch_classes]
        moved[note] = min(options, key=lambda m: abs(m - note))

    # 2. Two notes may have gone to the same chord tone, leaving another
    #    chord tone out. While there's a "spare" note like that, move the
    #    one that costs least extra to fill in a missing chord tone.
    missing = pitch_classes - {m % 12 for m in moved.values()}
    while missing:
        targets = [m % 12 for m in moved.values()]
        spare = [n for n in moved if targets.count(moved[n] % 12) > 1]
        if not spare:
            break  # fewer notes than chord tones: some have to be left out
        def extra(choice):
            note, pc = choice
            return abs(nearest(note, pc) - note) - abs(moved[note] - note)
        note, pc = min(((n, pc) for n in spare for pc in missing), key=extra)
        moved[note] = nearest(note, pc)
        missing.discard(pc)

    # 3. Two notes can't land on the same key (G7 to C sends both B and D
    #    to C). Notes with the smallest moves keep their key; a later one
    #    whose key is taken goes to the closest free note of the chord.
    taken = set()
    for note in sorted(moved, key=lambda n: abs(moved[n] - n)):
        if moved[note] in taken:
            free = [m for m in range(note - 12, note + 13)
                    if m % 12 in pitch_classes and m not in taken]
            moved[note] = min(free, key=lambda m: abs(m - note))
        taken.add(moved[note])
    return sorted(moved.values())


def numeral_on(tonic, minor, root):
    """Which of the key's basic chords is built on this root, or None."""
    for numeral, (offset, _, _) in (MINOR_KEY_CHORDS if minor else MAJOR_KEY_CHORDS).items():
        if (root - tonic) % 12 == offset:
            return numeral
    return None


def secondary_dominant(notes, tonic, minor):
    """If the chord is a secondary dominant in this key, (root, shape, target).

    A major or dominant 7th chord whose root is a 5th above one of the key's
    chords acts as the V of that chord, borrowed for a moment: G7 in Eb
    major is the V7 of Cm (vi), so this returns its root, shape and 'vi'.
    """
    key_chords = MINOR_KEY_CHORDS if minor else MAJOR_KEY_CHORDS
    matches = chord_matches(notes)
    if not matches:
        return None
    root, shape = matches[0]
    if CHORDS[shape] in ("", "7", "9"):
        target = numeral_on(tonic, minor, (root + 5) % 12)  # a 5th down = a 4th up
        if target and key_chords[target][1] != "dim":  # a dim chord can't be "home"
            return root, shape, target
    return None


def progression(notes, tonic, minor):
    """What a chord does in a key, and where it usually goes next.

    Returns (numeral, job, next chords), where next chords is a list of
    (numeral, chord name) pairs. For a G7 in C major:
    ('V7', 'dominant: wants to resolve to I', [('I', 'C'), ('vi', 'Am')]).
    Returns None if the chord doesn't fit the key at all.
    """
    key_chords = MINOR_KEY_CHORDS if minor else MAJOR_KEY_CHORDS
    next_table = MINOR_NEXT if minor else MAJOR_NEXT

    fit = fit_in_key(notes, tonic, minor)
    if fit:
        root, shape, numeral = fit
        basic = numeral_on(tonic, minor, root)  # 'V' for a V7 chord
        _, _, job = key_chords[basic]
        nexts = [(n, key_chord_name(tonic, minor, n)) for n in next_table[basic]]
        return numeral, job, nexts

    secondary = secondary_dominant(notes, tonic, minor)
    if secondary:
        root, shape, target = secondary
        numeral = "V" + CHORDS[shape] + "/" + target   # e.g. "V7/vi"
        job = f"secondary dominant: resolves to {target}"
        return numeral, job, [(target, key_chord_name(tonic, minor, target))]
    return None


def chord_in_key(notes, key):
    """The chord to spell in a key, as (root, shape, root's letter), or None.

    In-key chords take their root's letter from the key's scale. A secondary
    dominant's root is 4 letters (a 5th) above its target's: V7/vi in C
    major points at A, so its root is E. Other chords return None.
    """
    tonic, minor = key
    fit = fit_in_key(notes, tonic, minor)
    if fit:
        root, shape, _ = fit
        return root, shape, key_letter(tonic, minor, numeral_on(tonic, minor, root))
    secondary = secondary_dominant(notes, tonic, minor)
    if secondary:
        root, shape, target = secondary
        return root, shape, (key_letter(tonic, minor, target) + 4) % 7
    return None



# More scales to show on the keyboard. These don't use each letter once
# like major and minor do, so each note lists both its half steps and its
# letters above the tonic: (3, 2) is a minor 3rd (C -> Eb). A 5-note scale
# skips letters; an 8-note scale has to use one letter twice (Ab and A).
OTHER_SCALES = {
    # Five notes, no half steps: the sound of folk songs and rock solos.
    "major pentatonic": [(0, 0), (2, 1), (4, 2), (7, 4), (9, 5)],
    "minor pentatonic": [(0, 0), (3, 2), (5, 3), (7, 4), (10, 6)],
    # Minor pentatonic plus the "blue note", a flattened 5th (Gb in C).
    "blues": [(0, 0), (3, 2), (5, 3), (6, 4), (7, 4), (10, 6)],
    # Diminished scales alternate whole and half steps, 8 notes in all.
    # Whole-half fits dim7 chords; half-whole fits dominant 7th chords.
    "whole-half diminished": [(0, 0), (2, 1), (3, 2), (5, 3), (6, 4), (8, 5), (9, 5), (11, 6)],
    "half-whole diminished": [(0, 0), (1, 1), (3, 2), (4, 2), (6, 3), (7, 4), (9, 5), (10, 6)],
    # Six notes, all a whole step apart: dreamy, fits augmented chords.
    "whole tone": [(0, 0), (2, 1), (4, 2), (6, 3), (8, 4), (10, 5)],
    # Barry Harris's 6th diminished scales: the major (or minor) scale with
    # a b6 added. Its 8 notes take turns between two chords: C maj6 dim is
    # C D E F G Ab A B, and every other note makes C6 (C E G A), with
    # Bdim7 (B D F Ab) in between.
    "maj6 dim": [(0, 0), (2, 1), (4, 2), (5, 3), (7, 4), (8, 5), (9, 5), (11, 6)],
    "min6 dim": [(0, 0), (2, 1), (3, 2), (5, 3), (7, 4), (8, 5), (9, 5), (11, 6)],
}
# Each 6th diminished scale's 6 chord (its suffix), and where the dim7
# chord's notes sit: 2, 5, 8 and 11 half steps up (D F Ab B in C).
SIXTH_DIMINISHED = {"maj6 dim": "6", "min6 dim": "m6"}
DIM7_STEPS = {2, 5, 8, 11}
# The order the Scale button steps through. "key" means the key's own scale;
# "improvise" means notes to play over whatever chord the left hand holds,
# and "improvise (spicy)" picks tenser scales where there are some.
SCALE_NAMES = ["key", "improvise", "improvise (spicy)"] + list(OTHER_SCALES)


def spell_scale(root, root_letter, steps):
    """Spell a scale from its root, given as (half steps, letters) pairs.

    Returns [(pitch class, name), ...]: C with the blues scale's steps
    gives [(0, 'C'), (3, 'Eb'), (5, 'F'), (6, 'Gb'), (7, 'G'), (10, 'Bb')].
    """
    notes = []
    for half_steps, letters in steps:
        pitch_class = (root + half_steps) % 12
        letter = (root_letter + letters) % 7
        accidental = accidental_between(pitch_class, letter)
        if abs(accidental) == 2:
            # Strict letters can give a double sharp or flat (Eb blues' blue
            # note would be Bbb); players write the simpler name (A) instead.
            letter = (letter + (1 if accidental > 0 else -1)) % 7
            accidental = accidental_between(pitch_class, letter)
        notes.append((pitch_class, spelled_name(letter, accidental)))
    return notes


def scale_for(tonic, minor, scale_name):
    """The notes of a scale starting on the key's home note.

    Same format as key_scale: (pitch class, name, optional) for each note.
    """
    if scale_name == "key":
        return key_scale(tonic, minor)
    notes = spell_scale(tonic, tonic_letter(tonic, minor), OTHER_SCALES[scale_name])
    return [(pitch_class, name, False) for pitch_class, name in notes]


def sixth_dim_chords(tonic, minor, scale_name):
    """Split a 6th diminished scale into its two chords.

    Returns the 6 chord's name, the dim7 chord's name, and the dim7's
    pitch classes: for C maj6 dim, ('C6', 'Bdim7', {2, 5, 8, 11}).
    """
    notes = scale_for(tonic, minor, scale_name)
    sixth = notes[0][1] + SIXTH_DIMINISHED[scale_name]  # built on the first note
    dim = notes[-1][1] + "dim7"                         # built on the last (the 7th)
    dim_notes = {(tonic + steps) % 12 for steps in DIM7_STEPS}
    return sixth, dim, dim_notes


def sixth_dim_movement(notes, tonic, minor, scale_name):
    """Barry Harris's movement: step every note up to the next scale note.

    In a 6th diminished scale the chords take turns, so moving each note
    of the 6 chord up one scale note gives the dim7, and moving the dim7's
    notes up gives the 6 chord again: C4 E4 G4 A4 -> D4 F4 Ab4 B4.
    Works for any voicing of at least 3 notes from one of the two chords.

    Returns (the next chord's name, its MIDI notes, their names), or None
    if the notes aren't from either chord.
    """
    scale = scale_for(tonic, minor, scale_name)
    names = {pc: name for pc, name, optional in scale}
    sixth, dim, dim_notes = sixth_dim_chords(tonic, minor, scale_name)
    pitch_classes = {n % 12 for n in notes}
    if len(pitch_classes) < 3:
        return None
    if pitch_classes <= dim_notes:          # <= on sets: "all of them are in"
        next_name = sixth
    elif pitch_classes <= set(names) - dim_notes:
        next_name = dim
    else:
        return None
    moved = []
    for note in sorted(notes):
        up = note + 1
        while up % 12 not in names:  # find the next note that's in the scale
            up += 1
        moved.append(up)
    return next_name, moved, [names[n % 12] for n in moved]


# Modes: a 7-note scale started from a different note. In C major, starting
# on D gives D Dorian, on G gives G Mixolydian. Each mode has its own
# pattern of half steps above its first note, so the pattern names it.
MODES = {
    (0, 2, 4, 5, 7, 9, 11): "major",                # also called Ionian
    (0, 2, 3, 5, 7, 9, 10): "Dorian",
    (0, 1, 3, 5, 7, 8, 10): "Phrygian",
    (0, 2, 4, 6, 7, 9, 11): "Lydian",
    (0, 2, 4, 5, 7, 9, 10): "Mixolydian",
    (0, 2, 3, 5, 7, 8, 10): "Aeolian",              # the natural minor scale
    (0, 1, 3, 5, 6, 8, 10): "Locrian",
    # Modes you get by swapping a borrowed chord's notes into the key:
    (0, 2, 4, 5, 7, 8, 10): "Aeolian dominant",    # A7 in C major
    (0, 1, 4, 5, 7, 8, 10): "Phrygian dominant",   # E7 in C major or A minor
    (0, 2, 3, 5, 7, 8, 11): "harmonic minor",
}


def one_letter_each(half_steps):
    """Steps for a 7-note scale, which uses each letter once, in order."""
    return [(steps, letters) for letters, steps in enumerate(half_steps)]


# Chords from outside the key have no key scale to borrow from, so each
# chord type gets the scale jazz players usually reach for. Like your
# teacher's sheet: Fm(maj7) -> F melodic minor, Cdim(maj7) -> C WH-diminished.
LYDIAN = ("Lydian", one_letter_each((0, 2, 4, 6, 7, 9, 11)))  # major, raised 4th
DORIAN = ("Dorian", one_letter_each((0, 2, 3, 5, 7, 9, 10)))  # minor, raised 6th
MIXOLYDIAN = ("Mixolydian", one_letter_each((0, 2, 4, 5, 7, 9, 10)))  # major, flat 7th
LOCRIAN_SHARP_2 = ("Locrian #2", one_letter_each((0, 2, 3, 5, 6, 8, 10)))
MELODIC_MINOR = ("melodic minor", one_letter_each((0, 2, 3, 5, 7, 9, 11)))
WH_DIMINISHED = ("WH-diminished", OTHER_SCALES["whole-half diminished"])
HW_DIMINISHED = ("HW-diminished", OTHER_SCALES["half-whole diminished"])
WHOLE_TONE = ("whole tone", OTHER_SCALES["whole tone"])

CHORD_TYPE_SCALES = {
    # Major chords: Lydian, since its raised 4th has no clash with the 3rd.
    "": LYDIAN, "maj7": LYDIAN, "maj9": LYDIAN, "6": LYDIAN, "add9": LYDIAN,
    "m": DORIAN, "m7": DORIAN, "m9": DORIAN, "m6": DORIAN, "madd9": DORIAN,
    "7": MIXOLYDIAN, "9": MIXOLYDIAN, "sus2": MIXOLYDIAN, "sus4": MIXOLYDIAN,
    # Locrian with a natural 2nd: plain Locrian's b2 clashes with the root.
    "m7b5": LOCRIAN_SHARP_2,
    "mMaj7": MELODIC_MINOR,
    "dim": WH_DIMINISHED, "dim7": WH_DIMINISHED, "dimMaj7": WH_DIMINISHED,
    "aug": WHOLE_TONE,
}

# Spicier choices for "improvise (spicy)": more tension to resolve. HW-
# diminished over a dominant 7th adds the b9, #9 and #11, like your
# teacher's C7 (it has no natural 9th, so it doesn't suit 9 chords).
SPICY_SCALES = {"7": HW_DIMINISHED}


def key_swap_scale(root, root_letter, chord, key):
    """The key's scale with the chord's notes swapped in, from the root.

    Each chord tone replaces the key's note on the same letter: over A7
    in C major, C# replaces C. Returns (mode name, [(pitch class, name)]).
    """
    tonic, minor = key
    scale = NATURAL_MINOR_SCALE if minor else MAJOR_SCALE
    letters = {}  # letter -> pitch class: letters[2] is the key's E (or Eb...)
    for degree, offset in enumerate(scale):
        letters[(tonic_letter(tonic, minor) + degree) % 7] = (tonic + offset) % 12
    for pitch_class, (letter, accidental) in chord.items():
        letters[letter] = pitch_class

    notes = []
    for step in range(7):
        letter = (root_letter + step) % 7
        pitch_class = letters[letter]
        notes.append((pitch_class, spelled_name(letter, accidental_between(pitch_class, letter))))
    pattern = tuple((pitch_class - root) % 12 for pitch_class, name in notes)
    return MODES.get(pattern, "scale"), notes


def improv_scale(notes, key, spicy=False):
    """Notes to improvise with over a chord, in a key.

    Chords in the key (and secondary dominants) use the key's scale with
    the chord's notes swapped in, started on the chord's root: that gives
    D Dorian over Dm7 in C major. Other chords use CHORD_TYPE_SCALES.
    With spicy=True, chord types in SPICY_SCALES use that scale instead.
    Each note gets a role:
      "chord"  - a chord tone: the safest notes to land on
      "color"  - another scale note: adds flavour (9ths, 11ths, 13ths)
      "avoid"  - a half step above a chord tone: it clashes if you hold
                 it, but is fine to pass through on the way somewhere
    Returns (title, [(pitch class, name, role), ...]), e.g. for Dm7 in
    C major: ('D Dorian', [(2, 'D', 'chord'), (4, 'E', 'color'), ...]).
    Returns None if the notes don't make a chord.
    """
    matches = chord_matches(notes)
    if not matches:
        return None
    in_key = chord_in_key(notes, key)
    if in_key:
        root, shape, root_letter = in_key
    else:
        root, shape = matches[0]
        root_letter = spell_chord(root, shape)[root][0]
    chord = spell_from_letter(root, shape, root_letter)
    chord_type = CHORDS[shape]

    if spicy and chord_type in SPICY_SCALES:
        mode, steps = SPICY_SCALES[chord_type]
        scale = spell_scale(root, root_letter, steps)
    elif in_key:
        mode, scale = key_swap_scale(root, root_letter, chord, key)
    else:
        mode, steps = CHORD_TYPE_SCALES[chord_type]
        scale = spell_scale(root, root_letter, steps)

    # Usually a note a half step above a chord tone clashes. Dominant
    # scales (a major 3rd and a minor 7th, like G7's) are the exception:
    # there the b9 and b13 are wanted tension, so only the 11th clashes.
    pattern = {(pitch_class - root) % 12 for pitch_class, name in scale}
    dominant = 4 in pattern and 10 in pattern
    clashes_with = {(root + 4) % 12} if dominant else set(chord)

    result = []
    for pitch_class, name in scale:
        if pitch_class in chord:
            role = "chord"
        elif (pitch_class - 1) % 12 in clashes_with:
            role = "avoid"
        else:
            role = "color"
        result.append((pitch_class, name, role))
    return scale[0][1] + " " + mode, result


# Intervals: the distance between two notes, by half steps within an
# octave -> (name, how many letters apart). C up to E is 4 half steps and
# 2 letters (C D E), a major 3rd. The tritone (6) is spelled as a 4th (C-F#).
INTERVALS = {
    1: ("minor 2nd", 1),
    2: ("major 2nd", 1),
    3: ("minor 3rd", 2),
    4: ("major 3rd", 2),
    5: ("perfect 4th", 3),
    6: ("tritone", 3),
    7: ("perfect 5th", 4),
    8: ("minor 6th", 5),
    9: ("major 6th", 5),
    10: ("minor 7th", 6),
    11: ("major 7th", 6),
}
# Past an octave, some intervals have their own names: a 9th is an octave
# plus a 2nd, a 10th an octave plus a 3rd, and so on.
COMPOUND_INTERVALS = {
    1: "minor 9th", 2: "major 9th", 3: "minor 10th", 4: "major 10th",
    5: "perfect 11th", 7: "perfect 12th", 8: "minor 13th", 9: "major 13th",
}


def interval_name(notes):
    """Name the distance between exactly two notes, e.g. 'perfect 5th', or None."""
    if len(notes) != 2:
        return None
    low, high = sorted(notes)
    octaves, half_steps = divmod(high - low, 12)  # 19 -> 1 octave + 7
    if half_steps == 0:
        return "octave" if octaves == 1 else f"{octaves} octaves"
    if octaves == 0:
        return INTERVALS[half_steps][0]
    if octaves == 1 and half_steps in COMPOUND_INTERVALS:
        return COMPOUND_INTERVALS[half_steps]
    plural = "s" if octaves > 1 else ""
    return f"{INTERVALS[half_steps][0]} + {octaves} octave{plural}"


def interval_spellings(notes, key=None):
    """Spell two notes so their letters match the interval's name.

    A minor 3rd is 2 letters apart, so D#-F# or Eb-Gb, never D#-Gb.
    The lower note takes the key's letter if it's in the key's scale;
    otherwise both choices for a black key are tried and the one with
    fewer accidentals wins. Returns {pitch class: (letter, accidental)}.
    """
    low, high = sorted(notes)
    low_pc, high_pc = low % 12, high % 12
    letters_apart = INTERVALS.get((high - low) % 12, ("", 0))[1]

    candidates = [letter for letter in range(7) if abs(accidental_between(low_pc, letter)) <= 1]
    if low_pc in LETTER_PITCHES:
        candidates = [LETTER_PITCHES.index(low_pc)]  # a white key keeps its own name
    if key:
        for pc, name, optional in key_scale(*key):
            if pc == low_pc:
                candidates = [LETTERS.index(name[0])]

    best = None
    for letter in candidates:
        upper = (letter + letters_apart) % 7
        spelling = {low_pc: (letter, accidental_between(low_pc, letter)),
                    high_pc: (upper, accidental_between(high_pc, upper))}
        score = sum(abs(accidental) for _, accidental in spelling.values())
        if best is None or score < best_score:
            best, best_score = spelling, score
    return best
