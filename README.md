# kicad-panelizer
A simple script to create a v-scored panel of a KiCad board.

To use:
1. Ensure you have KiCad 5.1.2+ installed
2. Clone script to an appropriate location
3. Open a terminal and `cd` to the directory of the script
4. Run it with python3: `./panelizer.py /path/to/source_board.kicad_pcb -x2 -y3 [--vrail=0 --hrail=5]`
5. Panelized output will be saved to the same directory as the source board, with the name `{sourceboardname}_panelized.kicad_pcb`

Please submit feature requests and bug reports via GitHub Issues.
