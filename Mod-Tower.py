import argparse
import re
import sys
from typing_extensions import Literal, NotRequired, Optional, TypedDict
from pydantic import TypeAdapter
import yaml

MidpointSetting = Literal["off", "high", "low"]

RoundSetting = Literal["round", "truncate"]

class ValueIncrementConfig(TypedDict):
    midpointSetting: MidpointSetting
    start: float
    increment: float
    roundSetting: NotRequired[RoundSetting]

class ValueInterpolateConfig(TypedDict):
    midpointSetting: MidpointSetting
    start: float
    end: float
    roundSetting: NotRequired[RoundSetting]

class ValueExpression(TypedDict):
    expression: str

ValueType = ValueIncrementConfig | ValueInterpolateConfig | ValueExpression

class LayerConfig(TypedDict):
    startingAt: NotRequired[int]
    forEvery: int
    do: str
    value: ValueType

class TowerConfig(TypedDict):
    everyLayer: list[LayerConfig]
    atLayer: dict[int, str]

def read_config(filename: str) -> TowerConfig:
    with open(filename, "r") as stream:
        try:
            config = yaml.safe_load(stream)
            config_validator = TypeAdapter(TowerConfig)
            config = config_validator.validate_python(config)
            return config
        except yaml.YAMLError as exc:
            print(exc)
            raise

def apply_round_setting(value, round_setting: RoundSetting):
    if round_setting == 'round':
        return int(value) if value == int(value) else round(value, 4)
    if round_setting == 'truncate':
        return int(value)

def eval_value_expression(expression: str, level: int, level_count: int, layer: int, layer_count: int) -> float:
    return eval(expression, {}, {
            "level": level,
            "level_count": level_count,
            "layer": layer,
            "layer_count": layer_count            
        })

def get_current_value(value_config: ValueType, level: int, level_count: int, layer: int, layer_count: int) -> float:

    round_setting : RoundSetting = "round" if "roundSetting" not in value_config else value_config['roundSetting']

    if "expression" in value_config:
        return apply_round_setting(eval_value_expression(value_config["expression"], level, level_count, layer, layer_count), round_setting)

    # Set the cofficient to either 1 or -1 so that the increment is either added or subtracted accordingly
    if value_config["midpointSetting"] == "off":

        if "increment" in value_config:
            return apply_round_setting(value_config["start"] + (level * value_config["increment"]), round_setting)

        # Interpolate using the 'end' value
        return apply_round_setting(value_config["start"] + ((level / (level_count - 1)) * (value_config["end"] - value_config['start'])), round_setting)

    if "end" in value_config:
        raise Exception("Cannout interpolate using an 'end' value when using a 'midpointSetting' other than 'off'")

    mid_level = int(level_count / 2) + 1
    if value_config["midpointSetting"] == "low" and level_count % 2 == 0:
        mid_level -= 1
    # Do a origin shift
    coefficient = (level + 1) - mid_level

    return apply_round_setting(value_config["start"] + (coefficient * value_config["increment"]), round_setting)


def get_gcode_for_line(layer_number: int, layer_count: int, config: TowerConfig):
    gcode_for_line = []
    if layer_number in config["atLayer"]:
        gcode_for_line.append(config["atLayer"][layer_number])


    for every_config in config["everyLayer"]:
        starting_at = int(every_config.get("startingAt", 0))
        for_every = int(every_config["forEvery"])
        level_count = int((layer_count - starting_at) / for_every)
        if layer_number < starting_at:
            continue
        if (layer_number - starting_at) % for_every == 0:
            level = int((layer_number - starting_at) / for_every)
            if level + 1 > level_count:
                break
            value_config = every_config["value"]
            current_value = get_current_value(
                value_config,
                level, 
                level_count,
                layer_number,
                layer_count)
            gcode_line = every_config["do"].format(value=current_value, level=level + 1)
            gcode_for_line.append(gcode_line)

    return gcode_for_line

def print_action_summary(config: TowerConfig, layer_count: int):
    print("========= Summary =========")
    print(f"Layer Count: {layer_count}")
    print("====== Layer Specific =====")
    if config['atLayer']:
        for layer, command in config['atLayer'].items():
            print(f"At layer {layer}: {command}")

    if not config["everyLayer"]:
        return

    print("====== Tower Levels =======")
    for everyConfig in config["everyLayer"]:
        starting_at = int(everyConfig.get('startingAt', 0))
        for_every = int(everyConfig['forEvery'])
        level_count = int((layer_count - starting_at) / for_every)
        print("===========================")
        print(f"Starting at: {starting_at}")
        print(f"For every: {for_every}")
        print("Do:")
        print("---------------------------")
        print(everyConfig['do'])
        print("---------------------------")
        if 'start' in everyConfig['value']:
            print(f"With initial value: {everyConfig['value']['start']}")
            if 'increment' in everyConfig['value']:
                print(f"Change increment/decrement: {everyConfig['value']['increment']}")
            else:
                print(f"Interpolate by level up to: {everyConfig['value']['end']}")
        else:
            print(f"With expression: {everyConfig['value']['expression']}")
        print("===========================")
        for level, layer in reversed(list(enumerate(range(starting_at, layer_count, for_every)))):
            if level + 1 > level_count:
                continue
            value_config = everyConfig['value']
            current_value = get_current_value(
                value_config,
                level, 
                level_count,
                layer,
                layer_count)
            print(f"Level {level + 1} (layer {layer}): {current_value}")
        print("===========================")


def mod_print(filename: str, config_file: str, output_file: str, verbose: bool):

    config = read_config(config_file)

    print(f"Config: {repr(config)}")

    output = sys.stdout

    if output_file:
        output = open(output_file, 'w')

    file = open(filename)

    current_line = file.readline()
    layer_count: Optional[int] = None

    # Read to the point where we get the layer count
    while current_line and not layer_count:
        layer_count_capture = re.findall(r'^;LAYER_COUNT:(\d+)$', current_line)
        print(current_line, end="", file=output)
        if layer_count_capture:
            layer_count = int(layer_count_capture[0])
        current_line = file.readline()

    if layer_count is None:
        raise Exception("Could not find any 'LAYER_COUNT' comment in entire file")

    if verbose:
        print_action_summary(config, layer_count)

    while current_line:
        layer_number_capture = re.findall(r'^;LAYER:(\d+)$', current_line)
        print(current_line, end="", file=output)
        if layer_number_capture:
            layer_number = int(layer_number_capture[0])
            gcode = get_gcode_for_line(layer_number, layer_count, config)
            if gcode:
                gcode_text = "\n".join(gcode)
                if args.verbose:
                    print(f"At layer {layer_number}:")
                    print(gcode_text)
                print(gcode_text, file=output)
        current_line = file.readline()

parser = argparse.ArgumentParser(
                    prog='Mod-Tower',
                    description='Instrument tower with cusdtom gcode')

parser.add_argument('filename')           # positional argument
parser.add_argument('-c', '--config-file', action="store", required=True)
parser.add_argument('-o', '--output-file', action="store", required=False)
parser.add_argument('-v', '--verbose',
                    action='store_true')  # on/off flag

args = parser.parse_args()

mod_print(**vars(args))


