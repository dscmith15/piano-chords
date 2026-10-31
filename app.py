import os

import mido
import pygame

from music import chord_keys, chord_names, note_name, note_spellings, staff_step

WIDTH, HEIGHT = 800, 480  # the usual resolution of a 5-inch Pi screen
BACKGROUND = (20, 20, 30)
TEXT = (240, 240, 240)
DIM_TEXT = (140, 140, 160)
STAFF_LINES = (110, 110, 130)

SUSTAIN_PEDAL = 64  # the standard MIDI control number for the sustain pedal

# The grand staff fills the left of the screen; the text fills the right.
STAFF_LEFT, STAFF_RIGHT = 20, 270
STEP = 8                # pixels between one staff step and the next
SPACE = STEP * 2        # pixels between two staff lines (a "staff space")
MIDDLE_C_Y = 240        # the y position of middle C (step 0)
CLEF_X = 28             # where the clefs start
NOTE_X = 170            # where the chord's note heads go
NOTE_W, NOTE_H = 20, 15  # note head size
TEXT_X = 540            # the middle of the text area

# The staff lines, as steps: E G B D F in treble, G B D F A in bass.
TREBLE_LINES = [2, 4, 6, 8, 10]
BASS_LINES = [-10, -8, -6, -4, -2]

# A free music font (SIL Open Font License, see fonts/OFL.txt), found
# next to this file so the app works whatever folder you run it from.
MUSIC_FONT = os.path.join(os.path.dirname(__file__), "fonts", "NotoMusic-Regular.ttf")


def make_symbol(font, char, above, below):
    """Render a music symbol sized to the staff.

    `above` and `below` say how many staff spaces it reaches above and
    below the point it's lined up on (for a treble clef, the G line).
    Returns the image and how many pixels of it sit above that point.
    """
    image = font.render(char, True, TEXT)
    image = image.subsurface(image.get_bounding_rect())  # trim empty edges
    height = round((above + below) * SPACE)
    width = round(image.get_width() * height / image.get_height())
    return pygame.transform.smoothscale(image, (width, height)), round(above * SPACE)


def draw_text(screen, font, text, color, center):
    """Draw text on the screen with its middle at the point `center`."""
    image = font.render(text, True, color)
    screen.blit(image, image.get_rect(center=center))


def step_y(step):
    """The y position of a staff step. Higher notes are higher up the
    screen, and y grows downwards, so each step up means a smaller y."""
    return MIDDLE_C_Y - step * STEP


def draw_ledger_line(screen, x, step):
    """A short line through (or under) a note that's off the staff."""
    y = step_y(step)
    pygame.draw.line(screen, STAFF_LINES, (x - 18, y), (x + 18, y), 2)


def draw_symbol(screen, symbol, x, step):
    """Draw a symbol from make_symbol, lined up on a staff step."""
    image, above = symbol
    screen.blit(image, (x, step_y(step) - above))


def draw_staff(screen, symbols, notes, spellings):
    """Draw the grand staff with these MIDI notes on it.

    `spellings` says which letter to write each note as (from note_spellings).
    """
    for step in TREBLE_LINES + BASS_LINES:
        y = step_y(step)
        pygame.draw.line(screen, STAFF_LINES, (STAFF_LEFT, y), (STAFF_RIGHT, y), 2)
    draw_symbol(screen, symbols["treble"], CLEF_X, 4)   # curls around G4
    draw_symbol(screen, symbols["bass"], CLEF_X, -4)    # dots either side of F3

    previous_step = None
    shifted = False
    accidentals = []  # (step, accidental) pairs, drawn after the notes
    for number in sorted(notes):
        step, accidental = staff_step(number, spellings.get(number % 12))

        # Notes one step apart (like C and D) would overlap, so the upper
        # one moves to the right side of the stem, the way printed music does.
        if previous_step is not None and step - previous_step == 1 and not shifted:
            x = NOTE_X + NOTE_W
            shifted = True
        else:
            x = NOTE_X
            shifted = False
        previous_step = step

        # Ledger lines: middle C has its own, and notes above the treble
        # staff or below the bass staff need one on every line they pass.
        if step == 0:
            draw_ledger_line(screen, x, 0)
        for line in range(12, step + 1, 2):        # 12, 14, ... up to the note
            draw_ledger_line(screen, x, line)
        for line in range(-12, step - 1, -2):      # -12, -14, ... down to it
            draw_ledger_line(screen, x, line)

        y = step_y(step)
        pygame.draw.ellipse(screen, TEXT, (x - NOTE_W // 2, y - NOTE_H // 2, NOTE_W, NOTE_H))
        if accidental:
            accidentals.append((step, accidental))

    # Signs are about 6 steps tall, so ones closer than that would overlap.
    # Like printed music, work down from the top note, putting each sign in
    # the first column (counting leftwards from the notes) where it fits.
    columns = []  # columns[0] is the list of steps already used next to the notes
    for step, accidental in reversed(accidentals):
        column = 0
        while column < len(columns) and any(abs(step - s) < 6 for s in columns[column]):
            column += 1
        if column == len(columns):
            columns.append([])
        columns[column].append(step)

        symbol = symbols[accidental]
        width = symbol[0].get_width()
        sign_x = NOTE_X - NOTE_W // 2 - 4 - width - column * (width + 3)
        draw_symbol(screen, symbol, sign_x, step)


pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Piano Chords")
chord_font = pygame.font.SysFont(None, 150)
also_font = pygame.font.SysFont(None, 40)
keys_font = pygame.font.SysFont(None, 34)
notes_font = pygame.font.SysFont(None, 44)
clock = pygame.time.Clock()

# Make the music symbols once at the start, not again every frame.
# The above/below sizes are the standard proportions used in printed music.
music_font = pygame.font.Font(MUSIC_FONT, 200)
symbols = {
    "treble": make_symbol(music_font, "\U0001D11E", 4.4, 2.6),  # 𝄞
    "bass": make_symbol(music_font, "\U0001D122", 1.05, 2.55),  # 𝄢
    # Accidentals, keyed by how many half steps they move a note.
    1: make_symbol(music_font, "♯", 1.4, 1.4),             # ♯ sharp
    -1: make_symbol(music_font, "♭", 1.75, 0.7),           # ♭ flat
    2: make_symbol(music_font, "\U0001D12A", 0.5, 0.5),         # 𝄪 double sharp
    -2: make_symbol(music_font, "\U0001D12B", 1.75, 0.7),       # 𝄫 double flat
}

held = set()       # keys your fingers are holding down right now
sustained = set()  # keys you let go of that the pedal is keeping alive
pedal_down = False

port = mido.open_input()
running = True

while running:
    # 1. Handle window events: closing the window or pressing Escape quits.
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    # 2. Handle every MIDI message that arrived since the last frame.
    #    iter_pending() doesn't wait: if nothing came in, the loop is empty.
    for msg in port.iter_pending():
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
            pedal_down = msg.value >= 64
            if not pedal_down:
                sustained.clear()  # pedal up: sustained notes stop

    # 3. Draw the frame: wipe the screen, then draw what's sounding.
    sounding = held | sustained
    screen.fill(BACKGROUND)
    spellings = note_spellings(sounding) if sounding else {}
    draw_staff(screen, symbols, sounding, spellings)
    if sounding:
        chords = chord_names(sounding)
        if chords:
            draw_text(screen, chord_font, chords[0], TEXT, (TEXT_X, 80))
        if len(chords) > 1:
            also = "also " + ", ".join(chords[1:])
            draw_text(screen, also_font, also, DIM_TEXT, (TEXT_X, 160))
        # Major keys in one column, minor keys in the other: "C: I".
        major_keys, minor_keys = chord_keys(sounding)
        for keys, x in ((major_keys, TEXT_X - 120), (minor_keys, TEXT_X + 120)):
            for row, (key, numeral) in enumerate(keys):
                draw_text(screen, keys_font, f"{key}: {numeral}", DIM_TEXT, (x, 215 + row * 34))
        names = "  ".join(note_name(n, spellings.get(n % 12)) for n in sorted(sounding))
        draw_text(screen, notes_font, names, TEXT, (TEXT_X, 440))
    pygame.display.flip()  # show the finished frame

    clock.tick(60)  # wait so the loop runs at most 60 times a second

port.close()
pygame.quit()
