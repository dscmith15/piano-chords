import mido

# The 12 note names in one octave. A note's position in this list
# is its MIDI note number % 12 (C = 0, C# = 1, ... B = 11).
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name(number):
    """Turn a MIDI note number into a name like 'C4' (60 -> C4)."""
    name = NOTE_NAMES[number % 12]
    octave = number // 12 - 1  # MIDI note 0 is C-1, so subtract 1
    return f"{name}{octave}"


print(mido.get_input_names())

with mido.open_input() as port:
    for msg in port:
        if msg.type == "note_on" and msg.velocity > 0:
            print("pressed ", note_name(msg.note))
        elif msg.type == "note_off" or msg.type == "note_on":
            # Some keyboards send note_on with velocity 0 to mean "released".
            print("released", note_name(msg.note))
        # Everything else (control_change, polytouch, ...) is ignored for now.
