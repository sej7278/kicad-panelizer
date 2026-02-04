#!/usr/bin/env python3

"""
A simple script to create a v-scored panel of a KiCad board.
Original author: Willem Hillier
"""

__version__ = "4.0"

import os
import sys
from argparse import ArgumentParser
import pcbnew

# constants
SCALE = 1000000  # mm to internal units
V_SCORE_TEXT_SIZE = 2
V_SCORE_TEXT_THICKNESS = 0.1
MIN_PANEL_SIZE_MM = 70
MIN_RAIL_WIDTH_FOR_TEXT = 2


def get_layertable(board):
    """Creates a dict to lookup layer numbers by name."""
    return {board.GetLayerName(i): i for i in range(pcbnew.PCB_LAYER_ID_COUNT)}


def duplicate_board_items(
    board, items, num_x, num_y, board_width, board_height, create_copy=None
):
    """
    Duplicate board items across the panel grid.

    Args:
        board: The KiCad board object
        items: Iterable of source items to duplicate
        num_x: Number of copies in X direction
        num_y: Number of copies in Y direction
        board_width: Width of single board (in internal units)
        board_height: Height of single board (in internal units)
        create_copy: Optional function to create a copy (defaults to item.Duplicate())
    """
    new_items = []
    for source_item in items:
        for x in range(num_x):
            for y in range(num_y):
                if x != 0 or y != 0:
                    if create_copy:
                        new_item = create_copy(source_item)
                    else:
                        new_item = source_item.Duplicate()
                    new_item.Move(pcbnew.VECTOR2I(x * board_width, y * board_height))
                    new_items.append(new_item)

    for item in new_items:
        board.Add(item)


def duplicate_zones(board, num_x, num_y, board_width, board_height):
    """Duplicate zones across the panel grid, preserving net assignments."""
    new_zones = []
    for i in range(board.GetAreaCount()):
        source_zone = board.GetArea(i)
        for x in range(num_x):
            for y in range(num_y):
                if x != 0 or y != 0:
                    new_zone = source_zone.Duplicate()
                    new_zone.SetNet(source_zone.GetNet())
                    new_zone.Move(pcbnew.VECTOR2I(x * board_width, y * board_height))
                    new_zones.append(new_zone)

    for zone in new_zones:
        board.Add(zone)


def duplicate_footprints(board, num_x, num_y, board_width, board_height):
    """Duplicate footprints across the panel grid with correct positioning."""
    modules = board.GetFootprints()
    new_modules = []
    for source_module in modules:
        for x in range(num_x):
            for y in range(num_y):
                if x != 0 or y != 0:
                    new_module = pcbnew.FOOTPRINT(source_module)
                    new_module.SetPosition(
                        pcbnew.VECTOR2I(
                            x * board_width + source_module.GetPosition().x,
                            y * board_height + source_module.GetPosition().y,
                        )
                    )
                    new_modules.append(new_module)

    for module in new_modules:
        board.Add(module)


def create_edge_cut(board, start_x, start_y, end_x, end_y, layer):
    """Create an edge cut line on the board."""
    edge = pcbnew.PCB_SHAPE(board)
    board.Add(edge)
    edge.SetStart(pcbnew.VECTOR2I(int(start_x), int(start_y)))
    edge.SetEnd(pcbnew.VECTOR2I(int(end_x), int(end_y)))
    edge.SetLayer(layer)


def create_panel_outline(
    board,
    array_center,
    array_width,
    array_height,
    h_rail_width,
    v_rail_width,
    padding,
    layer,
):
    """
    Create the rectangular panel outline with edge cuts.

    Returns the corner coordinates (left, right, top, bottom).
    """
    half_padding = padding / 2 * SCALE
    left = array_center.x - array_width / 2 - h_rail_width * SCALE - half_padding
    right = array_center.x + array_width / 2 + h_rail_width * SCALE + half_padding
    top = array_center.y - array_height / 2 - v_rail_width * SCALE - half_padding
    bottom = array_center.y + array_height / 2 + v_rail_width * SCALE + half_padding

    # create the four edges (top, right, bottom, left)
    create_edge_cut(board, left, top, right, top, layer)  # top
    create_edge_cut(board, right, top, right, bottom, layer)  # right
    create_edge_cut(board, right, bottom, left, bottom, layer)  # bottom
    create_edge_cut(board, left, bottom, left, top, layer)  # left

    return left, right, top, bottom


def create_vscore_line(board, start_x, start_y, end_x, end_y, layer):
    """Create a v-score line and return it for layer manipulation."""
    line = pcbnew.PCB_SHAPE(board)
    line.SetStart(pcbnew.VECTOR2I(int(start_x), int(start_y)))
    line.SetEnd(pcbnew.VECTOR2I(int(end_x), int(end_y)))
    line.SetLayer(layer)
    return line


def create_vscore_text(board, text, pos_x, pos_y, angle, justify, layer):
    """Create a v-score label text."""
    text_obj = pcbnew.PCB_TEXT(board)
    text_obj.SetText(text)
    text_obj.SetHorizJustify(justify)
    text_obj.SetPosition(pcbnew.VECTOR2I(int(pos_x), int(pos_y)))
    text_obj.SetTextSize(
        pcbnew.VECTOR2I(SCALE * V_SCORE_TEXT_SIZE, SCALE * V_SCORE_TEXT_SIZE)
    )
    text_obj.SetLayer(layer)
    text_obj.SetTextAngle(pcbnew.EDA_ANGLE(angle, 0))
    board.Add(text_obj)


def add_vscores(
    board,
    layertable,
    panel_center,
    panel_width,
    panel_height,
    board_width,
    board_height,
    num_x,
    num_y,
    h_rail_width,
    v_rail_width,
    vscore_extend,
    vscore_layer,
    vscore_text_layer,
    vscore_text,
):
    """Add all v-score lines and labels to the panel."""
    # calculate v-score boundaries
    vscore_top = int(panel_center.y - panel_height / 2 - vscore_extend * SCALE)
    vscore_bottom = int(panel_center.y + panel_height / 2 + vscore_extend * SCALE)
    vscore_right = int(panel_center.x + panel_width / 2 + vscore_extend * SCALE)
    vscore_left = int(panel_center.x - panel_width / 2 - vscore_extend * SCALE)

    v_scores = []

    # vertical v-scores
    if h_rail_width > 0:
        x_range = range(0, num_x + 1)
    else:
        x_range = range(1, num_x)

    for x in x_range:
        x_loc = int(
            panel_center.x - panel_width / 2 + h_rail_width * SCALE + board_width * x
        )
        line = create_vscore_line(
            board, x_loc, vscore_top, x_loc, vscore_bottom, layertable[vscore_layer]
        )
        v_scores.append(line)
        create_vscore_text(
            board,
            vscore_text,
            x_loc,
            vscore_top - V_SCORE_TEXT_SIZE * SCALE,
            900,
            pcbnew.GR_TEXT_H_ALIGN_LEFT,
            layertable[vscore_text_layer],
        )

    # horizontal v-scores
    if v_rail_width > 0:
        y_range = range(0, num_y + 1)
    else:
        y_range = range(1, num_y)

    for y in y_range:
        y_loc = int(
            panel_center.y - panel_height / 2 + v_rail_width * SCALE + board_height * y
        )
        line = create_vscore_line(
            board, vscore_left, y_loc, vscore_right, y_loc, layertable[vscore_layer]
        )
        v_scores.append(line)
        create_vscore_text(
            board,
            vscore_text,
            vscore_left - V_SCORE_TEXT_SIZE * SCALE,
            y_loc,
            0,
            pcbnew.GR_TEXT_H_ALIGN_RIGHT,
            layertable[vscore_text_layer],
        )

    # add v-scores to board via Edge.Cuts layer workaround
    for vscore in v_scores:
        vscore.SetLayer(layertable["Edge.Cuts"])
        board.Add(vscore)

    # move back to correct layer
    for vscore in v_scores:
        vscore.SetLayer(layertable[vscore_layer])

    return vscore_bottom


def add_rail_text(board, text, pos_x, pos_y, angle=0, text_size=1):
    """Add text to a rail on the silkscreen layer."""
    text_obj = pcbnew.PCB_TEXT(board)
    text_obj.SetText(text)
    text_obj.SetTextSize(pcbnew.VECTOR2I(SCALE * text_size, SCALE * text_size))
    text_obj.SetLayer(pcbnew.F_SilkS)
    text_obj.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    text_obj.SetPosition(pcbnew.VECTOR2I(int(pos_x), int(pos_y)))
    if angle != 0:
        text_obj.SetTextAngle(pcbnew.EDA_ANGLE(angle, 0))
    board.Add(text_obj)


def get_title_text(board):
    """Build title text from the board's title block."""
    parts = []
    title_block = board.GetTitleBlock()

    if title_block.GetTitle():
        parts.append(str(title_block.GetTitle()))

    if title_block.GetRevision():
        parts.append(f"Rev. {title_block.GetRevision()}")

    if title_block.GetDate():
        parts.append(str(title_block.GetDate()))

    if title_block.GetCompany():
        parts.append(f"(c) {title_block.GetCompany()}")

    if len(parts) <= 1:
        return "".join(parts)

    # join with appropriate separators
    result = parts[0]
    for part in parts[1:]:
        if part.startswith("Rev."):
            result += " " + part
        elif part.startswith("(c)"):
            result += " " + part
        else:
            result += ", " + part
    return result


def parse_args():
    """Parse and validate command line arguments."""
    parser = ArgumentParser(description="A script to panelize KiCad files.")
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        dest="sourceBoardFile", help="Path to the *.kicad_pcb file to be panelized"
    )
    parser.add_argument("--numx", type=int, help="Number of boards in X direction")
    parser.add_argument("--numy", type=int, help="Number of boards in Y direction")
    parser.add_argument(
        "--padding", type=int, default=1, help="Extra space between boards"
    )
    parser.add_argument("--panelx", type=int, help="Maximum panel size in X direction")
    parser.add_argument("--panely", type=int, help="Maximum panel size in Y direction")
    parser.add_argument(
        "--hrail", type=int, default=0, help="Horizontal edge rail width"
    )
    parser.add_argument("--vrail", type=int, default=0, help="Vertical edge rail width")
    parser.add_argument("--hrailtext", help="Text to put on the horizontal edge rail")
    parser.add_argument("--vrailtext", help="Text to put on the vertical edge rail")
    parser.add_argument(
        "--htitle", action="store_true", help="Print title info on horizontal edge rail"
    )
    parser.add_argument(
        "--vtitle", action="store_true", help="Print title info on vertical edge rail"
    )
    parser.add_argument(
        "--vscorelayer", default="Edge.Cuts", help="Layer to put v-score lines on"
    )
    parser.add_argument(
        "--vscoretextlayer",
        default="User.Comments",
        help="Layer to put v-score text on",
    )
    parser.add_argument(
        "--vscoretext", default="V-SCORE", help="Text used to indicate v-scores"
    )
    parser.add_argument(
        "--vscoreextends",
        type=float,
        default=-0.05,
        help="How far past the board to extend the v-score lines, defaults to -0.05",
    )

    return parser.parse_args()


def validate_args(args):
    """Validate command line arguments and return processed values."""
    source_file = args.sourceBoardFile

    # check file extension
    if not source_file.endswith(".kicad_pcb"):
        print(f"{source_file} is not a *.kicad_pcb file. Quitting.")
        sys.exit(1)

    # check rail text requirements
    if ((args.hrailtext or args.htitle) and args.hrail < MIN_RAIL_WIDTH_FOR_TEXT) or (
        (args.vrailtext or args.vtitle) and args.vrail < MIN_RAIL_WIDTH_FOR_TEXT
    ):
        print(
            f"Rail width must be at least {MIN_RAIL_WIDTH_FOR_TEXT}mm if using rail text. Quitting."
        )
        sys.exit(1)

    # check for conflicting options
    if (args.panelx or args.panely) and (args.numx or args.numy):
        print("Specify number of boards or size of panel, not both. Quitting.")
        sys.exit(1)

    if (not args.panelx or not args.panely) and (not args.numx or not args.numy):
        print("Specify number of boards or size of panel. Quitting.")
        sys.exit(1)

    # warn about both rails
    if args.hrail and args.vrail:
        print("Warning: do you really want both edge rails?")


def main():
    """Main entry point for the panelizer script."""
    args = parse_args()
    validate_args(args)

    source_file = args.sourceBoardFile
    num_x = args.numx
    num_y = args.numy
    panel_x = args.panelx
    panel_y = args.panely
    padding = args.padding
    h_rail_width = args.hrail
    v_rail_width = args.vrail
    vscore_layer = args.vscorelayer
    vscore_text_layer = args.vscoretextlayer
    vscore_text = args.vscoretext
    vscore_extend = args.vscoreextends

    # output file name
    output_file = os.path.splitext(source_file)[0] + "_panelized.kicad_pcb"

    # load source board
    board = pcbnew.LoadBoard(source_file)
    layertable = get_layertable(board)

    # get board dimensions
    bbox = board.GetBoardEdgesBoundingBox()
    board_width = bbox.GetWidth() + padding * SCALE
    board_height = bbox.GetHeight() + padding * SCALE

    # calculate number of boards if panel size specified
    if panel_x:
        num_x = int((panel_x * SCALE - 2 * h_rail_width * SCALE) / board_width)
    if panel_y:
        num_y = int((panel_y * SCALE - 2 * v_rail_width * SCALE) / board_height)

    # check we can actually panelize
    if num_x == 0 or num_y == 0:
        print("Panel size is too small for board. Quitting.")
        sys.exit(1)

    # duplicate all board items
    duplicate_board_items(
        board, board.GetTracks(), num_x, num_y, board_width, board_height
    )
    duplicate_board_items(
        board, board.GetDrawings(), num_x, num_y, board_width, board_height
    )
    duplicate_footprints(board, num_x, num_y, board_width, board_height)
    duplicate_zones(board, num_x, num_y, board_width, board_height)

    # get array dimensions
    array_bbox = board.GetBoardEdgesBoundingBox()
    array_width = array_bbox.GetWidth()
    array_height = array_bbox.GetHeight()
    array_center = array_bbox.GetCenter()

    # erase existing edge cuts
    for drawing in board.GetDrawings():
        if drawing.IsOnLayer(layertable["Edge.Cuts"]):
            drawing.DeleteStructure()

    # create panel outline
    create_panel_outline(
        board,
        array_center,
        array_width,
        array_height,
        h_rail_width,
        v_rail_width,
        padding,
        layertable["Edge.Cuts"],
    )

    # get final panel dimensions
    panel_bbox = board.GetBoardEdgesBoundingBox()
    panel_width = panel_bbox.GetWidth()
    panel_height = panel_bbox.GetHeight()
    panel_center = array_center

    # add v-scores
    vscore_bottom = add_vscores(
        board,
        layertable,
        panel_center,
        panel_width,
        panel_height,
        board_width,
        board_height,
        num_x,
        num_y,
        h_rail_width,
        v_rail_width,
        vscore_extend,
        vscore_layer,
        vscore_text_layer,
        vscore_text,
    )

    # add rail text
    if args.hrailtext:
        add_rail_text(
            board,
            args.hrailtext,
            panel_center.x - panel_width / 2 + h_rail_width / 2 * SCALE,
            panel_center.y + panel_height / 2 - SCALE,
            angle=900,
        )

    if args.vrailtext:
        add_rail_text(
            board,
            args.vrailtext,
            panel_center.x - panel_width / 2 + SCALE,
            panel_center.y - panel_height / 2 + v_rail_width / 2 * SCALE,
        )

    # add title text to rail
    title_text = get_title_text(board)

    if args.htitle:
        add_rail_text(
            board,
            title_text,
            panel_center.x + panel_width / 2 - h_rail_width / 2 * SCALE,
            panel_center.y + panel_height / 2 - SCALE,
            angle=900,
        )

    if args.vtitle:
        add_rail_text(
            board,
            title_text,
            panel_center.x - panel_width / 2 + SCALE,
            panel_center.y + panel_height / 2 - v_rail_width / 2 * SCALE,
        )

    # add report text
    report_args = (
        f"{output_file} ({num_x}x{num_y} panel) generated with:\n./panelizer.py"
    )
    report_args += " " + " ".join(sys.argv[1:])
    report_text = pcbnew.PCB_TEXT(board)
    report_text.SetText(report_args)
    report_text.SetTextSize(pcbnew.VECTOR2I(SCALE, SCALE))
    report_text.SetLayer(layertable["User.Comments"])
    report_text.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    report_text.SetPosition(pcbnew.VECTOR2I(panel_center.x, vscore_bottom + 10 * SCALE))
    board.Add(report_text)

    # save output
    board.Save(output_file)

    # print warnings and report
    if (
        panel_width / SCALE < MIN_PANEL_SIZE_MM
        or panel_height / SCALE < MIN_PANEL_SIZE_MM
    ):
        print(f"Warning: panel is under {MIN_PANEL_SIZE_MM}x{MIN_PANEL_SIZE_MM}mm")

    if panel_x or panel_y:
        print(f"You can fit {num_x} x {num_y} boards on the panel")

    print(f"Board dimensions: {board_width / SCALE}x{board_height / SCALE}mm")
    print(f"Panel dimensions: {panel_width / SCALE}x{panel_height / SCALE}mm")


if __name__ == "__main__":
    main()
