import mido

# The 12 note names in one octave. A note's position in this list
# is its MIDI note number % 12 (C = 0, C# = 1, ... B = 11).
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name(number):
    """Turn a MIDI note number into a name like 'C4' (60 -> C4)."""
    name = NOTE_NAMES[number % 12]
    octave = number // 12 - 1  # MIDI note 0 is C-1, so subtract 1
    return f"{name}{octave}"


def show(notes):
    """Print notes from lowest to highest, e.g. 'C4 E4 G4'."""
    names = [note_name(n) for n in sorted(notes)]
    print(" ".join(names) if names else "(silence)")


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
