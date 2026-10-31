import os

import mido
import pygame

from music import (MAJOR_KEY_NAMES, MINOR_KEY_NAMES, chord_keys, chord_names,
                   note_name, note_spellings, progression, staff_step)

WIDTH, HEIGHT = 800, 480  # the usual resolution of a 5-inch Pi screen
BACKGROUND = (20, 20, 30)
TEXT = (240, 240, 240)
DIM_TEXT = (140, 140, 160)
STAFF_LINES = (110, 110, 130)
BUTTON = (45, 45, 65)
BUTTON_SELECTED = (70, 90, 160)

# The button that opens the key picker, under the staff.
KEY_BUTTON = pygame.Rect(20, 424, 250, 44)

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


def key_label(key):
    """Write a key as words: (3, False) -> 'Eb major', (9, True) -> 'A minor'."""
    tonic, minor = key
    if minor:
        return MINOR_KEY_NAMES[tonic][:-1] + " minor"  # [:-1] drops the "m"
    return MAJOR_KEY_NAMES[tonic] + " major"


def draw_button(screen, font, rect, text, selected=False):
    """A rounded box with text in the middle."""
    pygame.draw.rect(screen, BUTTON_SELECTED if selected else BUTTON, rect, border_radius=10)
    draw_text(screen, font, text, TEXT, rect.center)


def make_picker_buttons():
    """The key picker's buttons, as (rectangle, key) pairs.

    Two rows of 6 major keys, then two rows of 6 minor keys, then "No key".
    A key is (tonic, minor), e.g. (0, False) for C major; "No key" is None.
    """
    buttons = []
    for minor, top in ((False, 70), (True, 230)):
        for tonic in range(12):
            row, column = divmod(tonic, 6)  # tonic 7 -> row 1, column 1
            rect = pygame.Rect(15 + column * 130, top + row * 66, 120, 56)
            buttons.append((rect, (tonic, minor)))
    buttons.append((pygame.Rect(300, 400, 200, 56), None))
    return buttons


def draw_picker(screen, font, buttons, selected_key):
    """The full-screen key picker."""
    for rect, key in buttons:
        if key is None:
            text = "No key"
        elif key[1]:
            text = MINOR_KEY_NAMES[key[0]]
        else:
            text = MAJOR_KEY_NAMES[key[0]]
        draw_button(screen, font, rect, text, selected=(key == selected_key))
    draw_text(screen, font, "Major keys", DIM_TEXT, (WIDTH // 2, 45))
    draw_text(screen, font, "Minor keys", DIM_TEXT, (WIDTH // 2, 205))


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
numeral_font = pygame.font.SysFont(None, 90)
button_font = pygame.font.SysFont(None, 36)
clock = pygame.time.Clock()
picker_buttons = make_picker_buttons()

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

selected_key = None  # None, or (tonic, minor) like (0, False) for C major
picking = False      # True while the key picker is on screen

port = mido.open_input()
running = True

while running:
    # 1. Handle window events: closing the window or pressing Escape quits.
    #    A tap on a touchscreen arrives as a mouse click, so this handles both.
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if picking:
                # Choosing a key (or "No key") closes the picker.
                for rect, key in picker_buttons:
                    if rect.collidepoint(event.pos):
                        selected_key = key
                        picking = False
            elif KEY_BUTTON.collidepoint(event.pos):
                picking = True

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
    if picking:
        draw_picker(screen, button_font, picker_buttons, selected_key)
        pygame.display.flip()
        clock.tick(60)
        continue  # skip the normal screen while the picker is open

    spellings = note_spellings(sounding, selected_key) if sounding else {}
    draw_staff(screen, symbols, sounding, spellings)
    key_text = "Key: " + key_label(selected_key) if selected_key else "Key: none"
    draw_button(screen, button_font, KEY_BUTTON, key_text)
    if sounding:
        chords = chord_names(sounding, selected_key)
        if chords:
            draw_text(screen, chord_font, chords[0], TEXT, (TEXT_X, 80))
        if len(chords) > 1:
            also = "also " + ", ".join(chords[1:])
            draw_text(screen, also_font, also, DIM_TEXT, (TEXT_X, 160))
        if selected_key and chords:
            # With a key chosen, show the chord's job in that key and the
            # chords that usually come next: "next:  C (I)   Am (vi)".
            result = progression(sounding, *selected_key)
            if result:
                numeral, job, nexts = result
                draw_text(screen, numeral_font, numeral, TEXT, (TEXT_X, 235))
                draw_text(screen, keys_font, job, DIM_TEXT, (TEXT_X, 295))
                suggestions = "   ".join(f"{name} ({n})" for n, name in nexts)
                draw_text(screen, also_font, "next:  " + suggestions, TEXT, (TEXT_X, 355))
            else:
                draw_text(screen, keys_font, "not in " + key_label(selected_key),
                          DIM_TEXT, (TEXT_X, 260))
        else:
            # No key chosen: list every key the chord fits, "C: I".
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
