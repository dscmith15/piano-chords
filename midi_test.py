import mido

print(mido.get_input_names())

with mido.open_input() as port:
    for msg in port:
        print(msg)