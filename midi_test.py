import mido

from music import chord_names, note_name


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
