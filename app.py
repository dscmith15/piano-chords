import os

import mido
import pygame

from music import (MAJOR_KEY_NAMES, MINOR_KEY_NAMES, chord_keys, chord_matches,
                   chord_names, improv_scale, SCALE_NAMES, interval_name, note_name,
                   note_spellings, progression, scale_for, staff_step)

WIDTH, HEIGHT = 800, 480  # the usual resolution of a 5-inch Pi screen
BACKGROUND = (20, 20, 30)
CARD = (30, 30, 44)            # the slightly lighter panels things sit on
TEXT = (240, 240, 240)
DIM_TEXT = (140, 140, 160)
STAFF_LINES = (110, 110, 130)
BUTTON = (45, 45, 65)
BUTTON_SELECTED = (30, 120, 110)
IN_CHORD = (60, 200, 180)      # teal: a note you're playing
OUTSIDE_KEY = (255, 150, 60)   # orange: a note you're playing that's not in the key
# In improvise mode, each suggested note's name is colored by its role.
ROLE_COLORS = {"chord": IN_CHORD, "color": TEXT, "avoid": OUTSIDE_KEY}
WHITE_KEY = (225, 225, 230)
BLACK_KEY = (30, 30, 40)

# The screen is laid out as cards (rounded panels):
#
#   [Key button]                              • piano status
#   +--- chord card -------------+  +--- staff card ---+
#   | name          | details    |  |  grand staff     |
#   +----------------------------+  +------------------+
#   +--- next chords ------------+  +--- scale --------+
#   keyboard
#
# A pygame.Rect is (left, top, width, height).
KEY_BUTTON = pygame.Rect(8, 4, 210, 34)  # opens the key picker
CHORD_CARD = pygame.Rect(8, 44, 484, 222)
STAFF_CARD = pygame.Rect(500, 44, 292, 222)
NEXT_CARD = pygame.Rect(8, 274, 388, 60)
SCALE_BUTTON = pygame.Rect(404, 274, 388, 60)  # tap it to show the next scale
# With no key there's no scale to show, so the next-chords card takes the
# whole row. union() makes the smallest Rect covering both.
WIDE_CARD = NEXT_CARD.union(SCALE_BUTTON)
NAME_X = CHORD_CARD.left + 16  # the chord name's left edge
NAME_ROOM = 272                # how wide the chord name can be
DETAILS_LEFT, DETAILS_RIGHT = 310, 476  # the details column in the chord card

# The full keyboard along the bottom: all 88 keys, A0 (MIDI 21) to C8 (108).
KEYBOARD = pygame.Rect(8, 342, 784, 130)
LOWEST_KEY, HIGHEST_KEY = 21, 108
BLACK_PITCHES = {1, 3, 6, 8, 10}  # C# D# F# G# A#
WHITE_W = KEYBOARD.width / 52     # 52 white keys share the width: about 15 pixels each
BLACK_W, BLACK_H = 9, 80

SUSTAIN_PEDAL = 64  # the standard MIDI control number for the sustain pedal
# In improvise mode, only notes below this one (middle C) count as the
# chord, so the right hand is free to play a melody on top.
SPLIT_NOTE = 60

# The grand staff, inside the staff card.
STAFF_LEFT, STAFF_RIGHT = 512, 780
STEP = 5.5              # pixels between one staff step and the next
SPACE = STEP * 2        # pixels between two staff lines (a "staff space")
MIDDLE_C_Y = 158        # the y position of middle C (step 0)

# Like sheet music, notes past a few ledger lines are written an octave
# (or two) closer to the staff, with "8va"/"8vb" to say so. These are the
# furthest steps we write before doing that, so everything (the 8va/8vb
# marks too) stays inside the card.
HIGHEST_STEP = 16       # E6: 3 ledger lines above the treble staff
LOWEST_STEP = -14       # C2: 2 ledger lines below the bass staff
CLEF_X = 520            # where the clefs start
NOTE_X = 670            # where the chord's note heads go
NOTE_W, NOTE_H = 15, 11  # note head size

# The staff lines, as steps: E G B D F in treble, G B D F A in bass.
TREBLE_LINES = [2, 4, 6, 8, 10]
BASS_LINES = [-10, -8, -6, -4, -2]

# A free music font (SIL Open Font License, see fonts/OFL.txt), found
# next to this file so the app works whatever folder you run it from.
MUSIC_FONT = os.path.join(os.path.dirname(__file__), "fonts", "NotoMusic-Regular.ttf")

# The splash screen: shown for SPLASH_MS milliseconds, then fades out over
# FADE_MS. If you put a logo.png next to app.py, it's used as the logo;
# otherwise a treble clef on a staff is drawn instead.
LOGO_FILE = os.path.join(os.path.dirname(__file__), "logo.png")
SPLASH_MS = 2000
FADE_MS = 500


def make_symbol(font, char, above, below, space=SPACE):
    """Render a music symbol sized to a staff.

    `above` and `below` say how many staff spaces it reaches above and
    below the point it's lined up on (for a treble clef, the G line).
    `space` is the staff's line spacing in pixels.
    Returns the image and how many pixels of it sit above that point.
    """
    image = font.render(char, True, TEXT)
    image = image.subsurface(image.get_bounding_rect())  # trim empty edges
    height = round((above + below) * space)
    width = round(image.get_width() * height / image.get_height())
    return pygame.transform.smoothscale(image, (width, height)), round(above * space)


def make_splash(music_font, title_font, small_font):
    """Draw the splash screen once, onto its own full-screen image."""
    # 24 bits = red, green and blue only, no per-pixel see-through value.
    # (A plain Surface copies the window's format, which on a Mac includes
    # one; drawing text on it then punches see-through holes in the splash.)
    # Without it, set_alpha() below fades the whole image evenly.
    splash = pygame.Surface((WIDTH, HEIGHT), 0, 24)
    splash.fill(BACKGROUND)

    if os.path.exists(LOGO_FILE):
        # Your own logo: shrink (or grow) it to fit a 360 x 260 box,
        # keeping its shape. convert_alpha() keeps see-through parts.
        logo = pygame.image.load(LOGO_FILE).convert_alpha()
        scale = min(360 / logo.get_width(), 260 / logo.get_height())
        size = (round(logo.get_width() * scale), round(logo.get_height() * scale))
        logo = pygame.transform.smoothscale(logo, size)
        splash.blit(logo, logo.get_rect(center=(WIDTH // 2, 180)))
    else:
        # The drawn logo: a big treble clef on five staff lines.
        space = 26
        g_line = 220  # the y position of the G line the clef curls around
        for line in range(-3, 2):  # F D B G E, top to bottom
            y = g_line + line * space
            pygame.draw.line(splash, STAFF_LINES, (WIDTH // 2 - 150, y), (WIDTH // 2 + 150, y), 3)
        clef, above = make_symbol(music_font, "\U0001D11E", 4.4, 2.6, space)
        splash.blit(clef, (WIDTH // 2 - clef.get_width() // 2, g_line - above))

    draw_text(splash, title_font, "Piano Chords", TEXT, (WIDTH // 2, 365))
    draw_text(splash, small_font, "notes, chords, keys and scales as you play",
              DIM_TEXT, (WIDTH // 2, 420))
    return splash


def draw_text(screen, font, text, color, point, anchor="center"):
    """Draw text on the screen, placed by one of its points.

    `anchor` says which point of the text goes at `point`: "center" (the
    middle), "midleft" (the middle of its left edge, for left-aligned
    text), "midright", "topleft", and so on: any of pygame.Rect's names.
    """
    image = font.render(text, True, color)
    rect = image.get_rect(**{anchor: point})  # like get_rect(midleft=point)
    screen.blit(image, rect)


def fit_text(font, text, width):
    """Shorten text with "..." until it fits in `width` pixels."""
    if font.size(text)[0] <= width:
        return text
    while text and font.size(text + "...")[0] > width:
        text = text[:-1]  # drop the last letter and try again
    return text + "..."


def draw_card(screen, rect):
    """A rounded panel for a group of things to sit on."""
    pygame.draw.rect(screen, CARD, rect, border_radius=12)


def draw_detail(screen, label_font, value_font, row, label, value):
    """One row of the chord card's details: a label on the left, its value
    on the right."""
    y = CHORD_CARD.top + 26 + row * 32
    draw_text(screen, label_font, label, DIM_TEXT, (DETAILS_LEFT, y), "midleft")
    room = DETAILS_RIGHT - DETAILS_LEFT - label_font.size(label)[0] - 12
    value = fit_text(value_font, value, room)
    draw_text(screen, value_font, value, TEXT, (DETAILS_RIGHT, y), "midright")


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


def make_keyboard():
    """The 88 keys, as (MIDI note, rectangle, is_black) triples.

    The white keys come first and the black keys after, so drawing them in
    this order puts the black keys on top, like a real keyboard.
    """
    whites = []
    blacks = []
    for note in range(LOWEST_KEY, HIGHEST_KEY + 1):
        # The left edge of the next white key, i.e. the line between it and
        # the white key before it.
        x = KEYBOARD.left + len(whites) * WHITE_W
        if note % 12 in BLACK_PITCHES:
            # A black key sits across that line, half on each white key.
            rect = pygame.Rect(round(x - BLACK_W / 2), KEYBOARD.top, BLACK_W, BLACK_H)
            blacks.append((note, rect, True))
        else:
            # Rects need whole pixels, so round both edges. The -1 leaves a
            # 1-pixel gap of background between neighbouring white keys.
            width = round(x + WHITE_W) - round(x) - 1
            rect = pygame.Rect(round(x), KEYBOARD.top, width, KEYBOARD.height)
            whites.append((note, rect, False))
    return whites + blacks


def draw_key_marker(screen, center, pitch_class, scale, optional, chord, avoid, on_black):
    """The dot on one keyboard key, showing how that note fits the key."""
    if pitch_class in chord:
        pygame.draw.circle(screen, IN_CHORD, center, 4)
    elif pitch_class in scale:
        pygame.draw.circle(screen, (170, 170, 185) if on_black else (140, 140, 155), center, 3)
    elif pitch_class in optional:
        pygame.draw.circle(screen, IN_CHORD, center, 4, 1)  # a ring: optional
    elif pitch_class in avoid:
        pygame.draw.circle(screen, OUTSIDE_KEY, center, 4, 1)  # an orange ring: careful


def draw_keyboard(screen, keys, font, sounding, scale, optional, chord, avoid):
    """The 88-key keyboard, lighting up the keys being played.

    `keys` comes from make_keyboard() and `sounding` is the MIDI notes being
    played. The other arguments are sets of pitch classes, marked with dots
    in every octave: the scale's notes, its optional notes (a minor key's
    raised 7th), chord tones and notes to avoid (both in improvise mode).
    """
    allowed = scale | optional | chord
    for note, rect, is_black in keys:
        pitch_class = note % 12
        if note in sounding:
            # A key you're playing lights up: teal, or orange if it's
            # outside the scale (with no key, everything is teal).
            color = IN_CHORD if not allowed or pitch_class in allowed else OUTSIDE_KEY
        else:
            color = BLACK_KEY if is_black else WHITE_KEY
        pygame.draw.rect(screen, color, rect, border_bottom_left_radius=2,
                         border_bottom_right_radius=2)
        if note not in sounding:
            center = (rect.centerx, rect.bottom - (10 if is_black else 26))
            draw_key_marker(screen, center, pitch_class, scale, optional, chord, avoid, is_black)
        if pitch_class == 0:
            # Label every C with its octave, so you can find your place.
            draw_text(screen, font, f"C{note // 12 - 1}", STAFF_LINES, (rect.centerx, rect.bottom - 9))


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
    pygame.draw.line(screen, STAFF_LINES, (x - 13, y), (x + 13, y), 2)


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
# The chord name uses the biggest of these that fits (long names like
# EbdimMaj7 need a smaller one).
chord_fonts = [pygame.font.SysFont(None, size) for size in (100, 84, 68, 54)]
keys_font = pygame.font.SysFont(None, 30)
numeral_font = pygame.font.SysFont(None, 56)
button_font = pygame.font.SysFont(None, 36)
ottava_font = pygame.font.SysFont(None, 22, italic=True)
small_font = pygame.font.SysFont(None, 26)
label_font = pygame.font.SysFont(None, 22)  # the dim labels on cards
octave_font = pygame.font.SysFont(None, 14)  # C1 ... C8 on the keyboard
clock = pygame.time.Clock()
picker_buttons = make_picker_buttons()
keyboard = make_keyboard()

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

title_font = pygame.font.SysFont(None, 80)
splash = make_splash(music_font, title_font, keys_font)
splash_done = False  # becomes True when the splash has faded out (or was tapped)

held = set()       # keys your fingers are holding down right now
sustained = set()  # keys you let go of that the pedal is keeping alive
pedal_down = False

selected_key = None  # None, or (tonic, minor) like (0, False) for C major
scale_index = 0      # which of SCALE_NAMES to show; 0 is the key's own scale
picking = False      # True while the key picker is on screen
improv_chord = None  # in improvise mode, the left hand's last chord (MIDI notes)

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
            if not splash_done:
                splash_done = True  # a tap skips the splash (and does nothing else)
            elif picking:
                # Choosing a key (or "No key") closes the picker.
                for rect, key in picker_buttons:
                    if rect.collidepoint(event.pos):
                        selected_key = key
                        improv_chord = None  # a new key starts fresh
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

    # The cards go down first, so everything else is drawn on top of them.
    draw_card(screen, CHORD_CARD)
    draw_card(screen, STAFF_CARD)
    if selected_key:
        draw_card(screen, NEXT_CARD)
        pygame.draw.rect(screen, BUTTON, SCALE_BUTTON, border_radius=12)
    else:
        draw_card(screen, WIDE_CARD)
    # The details column, split from the name by a thin line.
    pygame.draw.line(screen, BUTTON, (DETAILS_LEFT - 14, CHORD_CARD.top + 14),
                     (DETAILS_LEFT - 14, CHORD_CARD.bottom - 14), 2)

    # The top bar: the Key button, and a dot saying if the piano's there.
    key_text = "Key: " + key_label(selected_key) if selected_key else "Key: none"
    draw_button(screen, keys_font, KEY_BUTTON, key_text)
    status = port.name if port else "Waiting for piano..."
    draw_text(screen, label_font, status, DIM_TEXT, (WIDTH - 12, 21), "midright")
    dot_x = WIDTH - 12 - label_font.size(status)[0] - 12
    pygame.draw.circle(screen, IN_CHORD if port else OUTSIDE_KEY, (dot_x, 21), 5)

    spellings = note_spellings(sounding, selected_key) if sounding else {}
    draw_staff(screen, symbols, ottava_font, sounding, spellings)
    if port is None:
        draw_text(screen, small_font, "Is the piano switched on", DIM_TEXT,
                  (NAME_X, CHORD_CARD.top + 40), "midleft")
        draw_text(screen, small_font, "and connected?", DIM_TEXT,
                  (NAME_X, CHORD_CARD.top + 66), "midleft")
    # The dots to put on the keyboard: (scale, optional, chord, avoid).
    # With no key there are none, and only the keys you play light up.
    marks = (set(), set(), set(), set())
    if selected_key:
        scale_name = SCALE_NAMES[scale_index]
        playing = {n % 12 for n in sounding}
        if scale_name.startswith("improvise"):
            # Notes to play over the chord your left hand last held. Keeping
            # the last chord means the suggestions stay when you lift it.
            spicy = scale_name == "improvise (spicy)"
            left_hand = {n for n in sounding if n < SPLIT_NOTE}
            if left_hand and chord_matches(left_hand):
                improv_chord = left_hand
            if improv_chord:
                mode, improv_notes = improv_scale(improv_chord, selected_key, spicy)
                chord_tones = {pc for pc, name, role in improv_notes if role == "chord"}
                color = {pc for pc, name, role in improv_notes if role == "color"}
                avoid = {pc for pc, name, role in improv_notes if role == "avoid"}
                marks = (color, set(), chord_tones, avoid)
                chord_name = chord_names(improv_chord, selected_key)[0]
                title = ("Spicy over " if spicy else "Over ") + chord_name + ": " + mode
                words = [(name, ROLE_COLORS[role]) for pc, name, role in improv_notes]
            else:
                title = "Spicy improvise" if spicy else "Improvise"
                words = [("hold a chord below middle C", DIM_TEXT)]
        else:
            # The chosen scale, as dots on the keyboard and a row of names.
            # Notes you're playing are teal (orange if they're outside the scale).
            scale_notes = scale_for(*selected_key, scale_name)
            scale = {pc for pc, name, optional in scale_notes if not optional}
            optional = {pc for pc, name, is_optional in scale_notes if is_optional}
            marks = (scale, optional, set(), set())
            if scale_name == "key":
                title = key_label(selected_key) + " scale"
            else:
                title = key_label(selected_key).split()[0] + " " + scale_name  # "C blues"
            words = []
            for pc, name, is_optional in scale_notes:
                text = f"({name})" if is_optional else name
                words.append((text, IN_CHORD if pc in playing else TEXT))

        # Add the hint when there's room; long titles go without it.
        if label_font.size(title + "   (tap to change)")[0] <= SCALE_BUTTON.width - 20:
            title += "   (tap to change)"
        draw_text(screen, label_font, title, DIM_TEXT, (SCALE_BUTTON.centerx, SCALE_BUTTON.top + 14))
        draw_text_row(screen, keys_font, words, (SCALE_BUTTON.centerx, SCALE_BUTTON.top + 40))
    draw_keyboard(screen, keyboard, octave_font, sounding, *marks)  # * unpacks the 4 sets

    # What the big chord name describes: every note you're playing, or in
    # improvise mode the left hand's chord, so a melody on top doesn't
    # change it and it stays after you lift your hand.
    named = sounding
    if selected_key and SCALE_NAMES[scale_index].startswith("improvise") and improv_chord:
        named = improv_chord
    # The bottom-left card: what comes next in the key, or which keys the
    # chord fits when there's no key. It's labelled at the top left.
    strip = NEXT_CARD if selected_key else WIDE_CARD
    strip_label = (strip.left + 14, strip.top + 14)
    strip_text = (strip.left + 14, strip.top + 40)
    if not named:
        hint = "Play a chord" if selected_key else "Tap Key to see progressions and scales"
        draw_text(screen, small_font, hint, DIM_TEXT, strip_text, "midleft")
    else:
        chords = chord_names(named, selected_key)
        interval = interval_name(named)
        if chords:
            # The biggest font the name fits in, or else the smallest one.
            font = chord_fonts[-1]
            for f in chord_fonts:
                if f.size(chords[0])[0] <= NAME_ROOM:
                    font = f
                    break
            draw_text(screen, font, chords[0], TEXT, (NAME_X, CHORD_CARD.top + 56), "midleft")
        elif interval:
            # Two notes aren't a chord, so name the distance between them.
            draw_text(screen, numeral_font, fit_text(numeral_font, interval, NAME_ROOM),
                      TEXT, (NAME_X, CHORD_CARD.top + 56), "midleft")
            half_steps = max(named) - min(named)
            draw_text(screen, small_font, f"{half_steps} half steps", DIM_TEXT,
                      (NAME_X, CHORD_CARD.top + 104), "midleft")
        if len(chords) > 1:
            also = fit_text(small_font, "also " + ", ".join(chords[1:]), NAME_ROOM)
            draw_text(screen, small_font, also, DIM_TEXT, (NAME_X, CHORD_CARD.top + 104), "midleft")

        # The details column: the note names (no octaves, lowest first,
        # each letter once) and how many notes there are.
        named_spellings = note_spellings(named, selected_key)
        letters = []
        for n in sorted(named):
            name = note_name(n, named_spellings.get(n % 12))[:-1]  # [:-1] drops the octave
            if name not in letters:
                letters.append(name)
        draw_detail(screen, label_font, small_font, 0, "Spelled", " ".join(letters))
        draw_detail(screen, label_font, small_font, 1, "Notes held", str(len(named)))

        if selected_key and chords:
            # With a key chosen, show the chord's job in that key, and the
            # chords that usually come next: "C (I)   Am (vi)".
            result = progression(named, *selected_key)
            draw_text(screen, label_font, "Next", DIM_TEXT, strip_label, "midleft")
            if result:
                numeral, job, nexts = result
                draw_text(screen, numeral_font, numeral, TEXT,
                          (NAME_X, CHORD_CARD.top + 156), "midleft")
                draw_text(screen, small_font, fit_text(small_font, job, NAME_ROOM), DIM_TEXT,
                          (NAME_X, CHORD_CARD.top + 196), "midleft")
                suggestions = "     ".join(f"{name} ({n})" for n, name in nexts)
                draw_text(screen, keys_font, suggestions, TEXT, strip_text, "midleft")
            else:
                draw_text(screen, small_font, "not in " + key_label(selected_key), DIM_TEXT,
                          (NAME_X, CHORD_CARD.top + 156), "midleft")
                draw_text(screen, small_font, "-", DIM_TEXT, strip_text, "midleft")
        elif chords:
            # No key chosen: every key the chord fits, "C: I", in one row.
            major_keys, minor_keys = chord_keys(named)
            fits = "    ".join(f"{key}: {numeral}" for key, numeral in major_keys + minor_keys)
            draw_text(screen, label_font, "Keys it fits", DIM_TEXT, strip_label, "midleft")
            draw_text(screen, keys_font, fit_text(keys_font, fits, strip.width - 28), TEXT,
                      strip_text, "midleft")

    # 4. The splash screen, drawn over the finished frame. During the fade
    #    it gets more see-through, so the app appears underneath it.
    if not splash_done:
        if now < SPLASH_MS:
            splash.set_alpha(255)  # 255 = solid, 0 = invisible
        elif now < SPLASH_MS + FADE_MS:
            splash.set_alpha(round(255 * (1 - (now - SPLASH_MS) / FADE_MS)))
        else:
            splash_done = True
        if not splash_done:
            screen.blit(splash, (0, 0))
    pygame.display.flip()  # show the finished frame

    clock.tick(60)  # wait so the loop runs at most 60 times a second

if port:
    port.close()
pygame.quit()
