import mido
import pygame

from music import chord_keys, chord_names, note_name

WIDTH, HEIGHT = 800, 480  # the usual resolution of a 5-inch Pi screen
BACKGROUND = (20, 20, 30)
TEXT = (240, 240, 240)
DIM_TEXT = (140, 140, 160)

SUSTAIN_PEDAL = 64  # the standard MIDI control number for the sustain pedal


def draw_text(screen, font, text, color, center):
    """Draw text on the screen with its middle at the point `center`."""
    image = font.render(text, True, color)
    screen.blit(image, image.get_rect(center=center))


pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Piano Chords")
chord_font = pygame.font.SysFont(None, 180)
also_font = pygame.font.SysFont(None, 44)
keys_font = pygame.font.SysFont(None, 36)
notes_font = pygame.font.SysFont(None, 52)
clock = pygame.time.Clock()

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
    if sounding:
        chords = chord_names(sounding)
        if chords:
            draw_text(screen, chord_font, chords[0], TEXT, (WIDTH // 2, 120))
        if len(chords) > 1:
            also = "also " + ", ".join(chords[1:])
            draw_text(screen, also_font, also, DIM_TEXT, (WIDTH // 2, 210))
        # One line of major keys and one of minor keys, e.g. "C: I   F: V".
        major_keys, minor_keys = chord_keys(sounding)
        for keys, y in ((major_keys, 275), (minor_keys, 320)):
            if keys:
                line = "    ".join(f"{key}: {numeral}" for key, numeral in keys)
                draw_text(screen, keys_font, line, DIM_TEXT, (WIDTH // 2, y))
        names = "  ".join(note_name(n) for n in sorted(sounding))
        draw_text(screen, notes_font, names, TEXT, (WIDTH // 2, 410))
    pygame.display.flip()  # show the finished frame

    clock.tick(60)  # wait so the loop runs at most 60 times a second

port.close()
pygame.quit()
