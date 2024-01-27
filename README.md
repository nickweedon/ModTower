# ModTower
Simple Python script to allow gcode to be inserted into a gcode file at particular layers or intervals.

## Example config file:

```yaml
everyLayer:
  - startingAt: 3
    forEvery: 39
    do: |-
      M117 Level: {level}, Flow: {value}%
      M221 S{value} ;Set flow percentage
    value:
      start: 100
      increment: -5
atLayer:
  0: M221 S100 ;Set flow percentage
```

The 'do' string is provided with two arguments:
* level: The current level, based on 'forEvery', starting at 1.
* value: The current value, based on 'value' start and increment.