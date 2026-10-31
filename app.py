import os

import mido
import pygame

from music import (MAJOR_KEY_NAMES, MINOR_KEY_NAMES, chord_keys, chord_names,
                   SCALE_NAMES, interval_name, note_name, note_spellings, progression,
                   scale_for, staff_step)

WIDTH, HEIGHT = 800, 480  # the usual resolution of a 5-inch Pi screen
BACKGROUND = (20, 20, 30)
TEXT = (240, 240, 240)
DIM_TEXT = (140, 140, 160)
STAFF_LINES = (110, 110, 130)
BUTTON = (45, 45, 65)
BUTTON_SELECTED = (70, 90, 160)
IN_CHORD = (90, 150, 255)      # blue: a note you're playing
OUTSIDE_KEY = (255, 150, 60)   # orange: a note you're playing that's not in the key
WHITE_KEY = (225, 225, 230)
BLACK_KEY = (30, 30, 40)

# The button that opens the key picker, under the staff.
KEY_BUTTON = pygame.Rect(20, 424, 250, 44)
# The scale's name and notes, on the right; tap it to show the next scale.
SCALE_BUTTON = pygame.Rect(300, 350, 480, 68)

# The mini keyboard (one octave, C to B) between the staff and the button.
KEYBOARD_LEFT, KEYBOARD_TOP = 25, 366
WHITE_W, WHITE_H = 34, 52
BLACK_W, BLACK_H = 20, 32
WHITE_PITCHES = [0, 2, 4, 5, 7, 9, 11]            # C D E F G A B
# Each black key sits on the line after a white key: C# after C (white 0), ...
BLACK_PITCHES = {1: 0, 3: 1, 6: 3, 8: 4, 10: 5}

SUSTAIN_PEDAL = 64  # the standard MIDI control number for the sustain pedal

# The grand staff fills the left of the screen; the text fills the right.
STAFF_LEFT, STAFF_RIGHT = 20, 270
STEP = 8                # pixels between one staff step and the next
SPACE = STEP * 2        # pixels between two staff lines (a "staff space")
MIDDLE_C_Y = 212        # the y position of middle C (step 0)

# Like sheet music, notes past a few ledger lines are written an octave
# (or two) closer to the staff, with "8va"/"8vb" to say so. These are the
# furthest steps we write before doing that. Below the bass there's less
# room, because the mini keyboard is underneath.
HIGHEST_STEP = 17       # F6: 3 ledger lines above the treble staff
LOWEST_STEP = -15       # B1: 2 ledger lines below the bass staff
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


def draw_key_marker(screen, center, pitch_class, scale, optional, chord, on_black):
    """The dot on one keyboard key, showing how that note fits the key."""
    if pitch_class in chord:
        color = IN_CHORD if pitch_class in scale | optional else OUTSIDE_KEY
        pygame.draw.circle(screen, color, center, 8)
    elif pitch_class in scale:
        pygame.draw.circle(screen, (170, 170, 185) if on_black else (140, 140, 155), center, 6)
    elif pitch_class in optional:
        pygame.draw.circle(screen, IN_CHORD, center, 7, 2)  # a ring: optional


def draw_keyboard(screen, scale, optional, chord):
    """A one-octave keyboard marking the scale's notes and the chord's.

    Each argument is a set of pitch classes: the scale's notes, its optional
    notes (a minor key's raised 7th), and the notes being played.
    """
    # White keys first, then black keys on top, like a real keyboard.
    for i, pitch_class in enumerate(WHITE_PITCHES):
        rect = pygame.Rect(KEYBOARD_LEFT + i * WHITE_W, KEYBOARD_TOP, WHITE_W, WHITE_H)
        pygame.draw.rect(screen, WHITE_KEY, rect)
        pygame.draw.rect(screen, BLACK_KEY, rect, 1)  # 1 = just the outline
        center = (rect.centerx, rect.bottom - 14)
        draw_key_marker(screen, center, pitch_class, scale, optional, chord, False)
    for pitch_class, white_before in BLACK_PITCHES.items():
        x = KEYBOARD_LEFT + (white_before + 1) * WHITE_W - BLACK_W // 2
        rect = pygame.Rect(x, KEYBOARD_TOP, BLACK_W, BLACK_H)
        pygame.draw.rect(screen, BLACK_KEY, rect)
        center = (rect.centerx, rect.bottom - 11)
        draw_key_marker(screen, center, pitch_class, scale, optional, chord, True)


def draw_text_row(screen, font, words, center):
    """Draw several (text, color) words in a row, centered on a point."""
    images = [font.render(text, True, color) for text, color in words]
    gap = 18
    width = sum(image.get_width() for image in images) + gap * (len(images) - 1)
    x = center[0] - width // 2
    for image in images:
        screen.blit(image, image.get_rect(midleft=(x, center[1])))
        x += image.get_width() + gap


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


def ottava(steps):
    """Move very high and very low notes by octaves, the way sheet music does.

    Takes a list of staff steps. Returns the steps to draw them at, and
    (text, step) labels to draw: "8va" above notes written an octave lower
    than they sound, "15ma" for two octaves, "8vb"/"15mb" below the staff
    for notes written higher than they sound. An octave is 7 steps.

    As in sheet music, the mark covers the whole staff: if any treble note
    is too high, every treble note moves down together, so the chord keeps
    its shape. (Treble = middle C and up, bass = below middle C.)
    """
    labels = []
    treble_shift = 0
    bass_shift = 0
    treble = [s for s in steps if s >= 0]
    bass = [s for s in steps if s < 0]
    if treble and max(treble) > HIGHEST_STEP:
        treble_shift = 7 if max(treble) - 7 <= HIGHEST_STEP else 14
        labels.append(("8va" if treble_shift == 7 else "15ma", max(treble) - treble_shift + 3))
    if bass and min(bass) < LOWEST_STEP:
        bass_shift = 7 if min(bass) + 7 >= LOWEST_STEP else 14
        labels.append(("8vb" if bass_shift == 7 else "15mb", min(bass) + bass_shift - 3))
    steps = [s - treble_shift if s >= 0 else s + bass_shift for s in steps]
    return steps, labels


def draw_staff(screen, symbols, label_font, notes, spellings):
    """Draw the grand staff with these MIDI notes on it.

    `spellings` says which letter to write each note as (from note_spellings).
    """
    for step in TREBLE_LINES + BASS_LINES:
        y = step_y(step)
        pygame.draw.line(screen, STAFF_LINES, (STAFF_LEFT, y), (STAFF_RIGHT, y), 2)
    draw_symbol(screen, symbols["treble"], CLEF_X, 4)   # curls around G4
    draw_symbol(screen, symbols["bass"], CLEF_X, -4)    # dots either side of F3

    # Where each note goes, (step, accidental), after any octave shifts.
    placed = [staff_step(n, spellings.get(n % 12)) for n in notes]
    steps, labels = ottava([step for step, accidental in placed])
    placed = sorted(zip(steps, [accidental for step, accidental in placed]))
    for text, step in labels:
        draw_text(screen, label_font, text, TEXT, (NOTE_X, step_y(step)))

    previous_step = None
    shifted = False
    accidentals = []  # (step, accidental) pairs, drawn after the notes
    for step, accidental in placed:

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
ottava_font = pygame.font.SysFont(None, 28, italic=True)
small_font = pygame.font.SysFont(None, 26)
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
scale_index = 0      # which of SCALE_NAMES to show; 0 is the key's own scale
picking = False      # True while the key picker is on screen

port = None        # the piano's MIDI connection, or None while it isn't there
last_check = -1000  # when we last looked for the piano (in milliseconds)
running = True

while running:
    # 0. Once a second, check the piano is still there, or look for it.
    #    It might be switched off, asleep, or still connecting over Bluetooth.
    now = pygame.time.get_ticks()  # milliseconds since the app started
    if now - last_check >= 1000:
        last_check = now
        names = mido.get_input_names()
        if port is None and names:
            port = mido.open_input(names[0])
        elif port is not None and port.name not in names:
            # The piano went away: forget any notes it was holding.
            port.close()
            port = None
            held.clear()
            sustained.clear()
            pedal_down = False

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
            elif selected_key and SCALE_BUTTON.collidepoint(event.pos):
                # Step to the next scale, wrapping round to the start.
                scale_index = (scale_index + 1) % len(SCALE_NAMES)

    # 2. Handle every MIDI message that arrived since the last frame.
    #    iter_pending() doesn't wait: if nothing came in, the loop is empty.
    for msg in port.iter_pending() if port else []:
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
    draw_staff(screen, symbols, ottava_font, sounding, spellings)
    key_text = "Key: " + key_label(selected_key) if selected_key else "Key: none"
    draw_button(screen, button_font, KEY_BUTTON, key_text)
    if port is None:
        draw_text(screen, also_font, "Waiting for piano...", DIM_TEXT, (TEXT_X, 120))
        draw_text(screen, keys_font, "Is it switched on and connected?", DIM_TEXT, (TEXT_X, 165))
    if selected_key:
        # The chosen scale, on the mini keyboard and as a row of names.
        # Notes you're playing are blue (orange if they're outside the scale).
        scale_name = SCALE_NAMES[scale_index]
        scale_notes = scale_for(*selected_key, scale_name)
        scale = {pc for pc, name, optional in scale_notes if not optional}
        optional = {pc for pc, name, is_optional in scale_notes if is_optional}
        playing = {n % 12 for n in sounding}
        draw_keyboard(screen, scale, optional, playing)

        pygame.draw.rect(screen, BUTTON, SCALE_BUTTON, border_radius=10)
        if scale_name == "key":
            title = key_label(selected_key) + " scale"
        else:
            title = key_label(selected_key).split()[0] + " " + scale_name  # "C blues"
        draw_text(screen, small_font, title + "   (tap to change)", DIM_TEXT,
                  (SCALE_BUTTON.centerx, SCALE_BUTTON.top + 16))
        words = []
        for pc, name, is_optional in scale_notes:
            text = f"({name})" if is_optional else name
            words.append((text, IN_CHORD if pc in playing else TEXT))
        draw_text_row(screen, keys_font, words, (SCALE_BUTTON.centerx, SCALE_BUTTON.top + 46))
    if sounding:
        chords = chord_names(sounding, selected_key)
        interval = interval_name(sounding)
        if chords:
            draw_text(screen, chord_font, chords[0], TEXT, (TEXT_X, 80))
        elif interval:
            # Two notes aren't a chord, so name the distance between them.
            draw_text(screen, numeral_font, interval, TEXT, (TEXT_X, 80))
            half_steps = max(sounding) - min(sounding)
            draw_text(screen, also_font, f"{half_steps} half steps", DIM_TEXT, (TEXT_X, 160))
        if len(chords) > 1:
            also = "also " + ", ".join(chords[1:])
            draw_text(screen, also_font, also, DIM_TEXT, (TEXT_X, 160))
        if selected_key and chords:
            # With a key chosen, show the chord's job in that key and the
            # chords that usually come next: "next:  C (I)   Am (vi)".
            result = progression(sounding, *selected_key)
            if result:
                numeral, job, nexts = result
                draw_text(screen, numeral_font, numeral, TEXT, (TEXT_X, 225))
                draw_text(screen, keys_font, job, DIM_TEXT, (TEXT_X, 280))
                suggestions = "   ".join(f"{name} ({n})" for n, name in nexts)
                draw_text(screen, also_font, "next:  " + suggestions, TEXT, (TEXT_X, 330))
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
        draw_text(screen, notes_font, names, TEXT, (TEXT_X, 446))
    pygame.display.flip()  # show the finished frame

    clock.tick(60)  # wait so the loop runs at most 60 times a second

if port:
    port.close()
pygame.quit()
