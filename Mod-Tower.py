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

def trunc_round(value):
    return int(value) if value == int(value) else round(value, 4)

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
            level = int((layer_number - starting_at) / for_every)
            current_value = trunc_round(every_config["value"]["start"] + (every_config["value"]["increment"] * level))
            gcode_line = every_config["do"].format(value=current_value, level=level + 1)
            gcode_for_line.append(gcode_line)

    return gcode_for_line

def print_action_summary(config, layer_count: int):
    print("========= Summary =========")
    print("====== Layer Specific =====")
    if config['atLayer']:
        for layer, command in config['atLayer'].items():
            print(f"At layer {layer}: {command}")

    if not config["everyLayer"]:
        return

    print("====== Levels =============")
    for everyConfig in config["everyLayer"]:
        print("===========================")
        print(f"Do '{everyConfig['do']}'")
        print("===========================")
        for level, layer in enumerate(range(int(everyConfig['startingAt']), layer_count, int(everyConfig['forEvery']))):
            print(f"Level {level + 1} (layer {layer}): {trunc_round(everyConfig['value']['start'] + everyConfig['value']['increment'] * level)}")
        print("===========================")


def mod_print(args):
    config = read_config(args.config)

    output = sys.stdout

    if args.output:
        output = open(args.output, 'w')

    file = open(args.filename)

    current_line = file.readline()
    layer_count = None

    while current_line and not layer_count:
        layer_count_capture = re.findall(r'^;LAYER_COUNT:(\d+)$', current_line)
        print(current_line, end="", file=output)
        if layer_count_capture:
            layer_count = layer_count_capture[0]
        current_line = file.readline()

    if args.verbose:
        print_action_summary(config, int(layer_count))

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


