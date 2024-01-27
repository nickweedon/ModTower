import argparse
import re
import sys
import yaml


def read_config(filename):
    with open(filename, "r") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

def get_gcode_for_line(layer_number, config):
    gcode_for_line = []
    if layer_number in config["atLayer"]:
        gcode_for_line.append(config["atLayer"][layer_number])
    
    for every_config in config["everyLayer"]:
        starting_at = every_config.get("startingAt", 0)
        for_every = every_config.get("forEvery")
        if not for_every:
            raise Exception("'everyLayer' must define a 'forEvery' setting")
        if layer_number < starting_at:
            continue
        if (layer_number - starting_at) % for_every == 0:
            occurance = (layer_number - starting_at) / for_every
            current_value = round(every_config["value"]["start"] + (every_config["value"]["increment"] * occurance), 4)
            gcode_line = every_config["do"].format(value=current_value)
            gcode_for_line.append(gcode_line)
            

    return gcode_for_line


def mod_print(args):
    config = read_config(args.config)

    output = sys.stdout

    if args.output:
        output = open(args.output, 'w')

    file = open(args.filename)

    current_line = file.readline()

    while current_line:
        layer_number_capture = re.findall(r'^;LAYER:(\d+)$', current_line)
        print(current_line, end="", file=output)
        if layer_number_capture:
            gcode = get_gcode_for_line(int(layer_number_capture[0]), config)
            if gcode:
                gcode_text = "\n".join(gcode)
                if args.verbose:
                    print(f"At layer {layer_number_capture[0]}:")
                    print(gcode_text)
                print(gcode_text, file=output)
        current_line = file.readline()

parser = argparse.ArgumentParser(
                    prog='Mod-Tower',
                    description='Instrument tower with cusdtom gcode')

parser.add_argument('filename')           # positional argument
parser.add_argument('-c', '--config', action="store", required=True)
parser.add_argument('-o', '--output', action="store", required=False)
parser.add_argument('-v', '--verbose',
                    action='store_true')  # on/off flag

args = parser.parse_args()

mod_print(args)


