# kicad-panelizer
A simple script to create a v-scored panel of a KiCad board.

To use:
1. Ensure you have KiCad 5.1.2+ installed
2. Clone script to an appropriate location
3. Open a terminal and `cd` to the directory of the script
4. Run it with python3: `./panelizer.py /path/to/source_board.kicad_pcb -x2 -y3 [--vrail=0 --hrail=5 --vrailtext="horizontal text on vrail" --hrailtext="vertical text on hrail"]`
5. Panelized output will be saved to the same directory as the source board, with the name `{sourceboardname}_panelized.kicad_pcb`

Please submit feature requests and bug reports via GitHub Issues.

# Hints & Tips:

If you don't use Edge.Cuts as your ```V_SCORE_LAYER``` don't refill zones when exporting the gerbers as Kicad will essentially merge your panel into a single board.

Both [Seeed](http://support.seeedstudio.com/knowledgebase/articles/388503-what-are-the-pcb-panelization-rules
) and [JLCPCB](https://support.jlcpcb.com/article/49-pcb-panelization
) seem to want v-scores to be on the Edge.Cuts layer. In this case Kicad seems to cope with zones being refilled, however the 3d viewer can't figure out the board outline. Also it will fail the DRC due to the board outline not being a polygon. I would set ```V_SCORE_LINE_LENGTH_BEYOND_BOARD``` to -0.05 in this case, so that the v-scores meet in the middle of the default 0.1mm lines rather than extending past the panel.
