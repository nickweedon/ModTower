# ModTower
Simple Python script to allow gcode to be inserted into a gcode file at particular layers or intervals.

## Example config file:

```yaml
everyLayer:
  - startingAt: 3
    forEvery: 39
    do: M900 K{value}
    value:
      start: 0
      increment: 0.02
atLayer:
  0: M900 K0
```