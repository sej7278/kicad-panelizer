#!/usr/bin/env python3

"""
A simple script to create a v-scored panel of a KiCad board.
Original author: Willem Hillier
"""

# pylint: disable=invalid-name,too-many-boolean-expressions

__version__ = "2.0"

import os
import sys
from argparse import ArgumentParser
import pcbnew


def get_layertable():
    """creates a list that can be used to lookup layer numbers by their name"""

    _layertable = {}
    numlayers = pcbnew.PCB_LAYER_ID_COUNT
    for i in range(numlayers):
        _layertable[board.GetLayerName(i)] = i
    return _layertable


# set up command-line arguments parser
parser = ArgumentParser(description="A script to panelize KiCad files.")
parser.add_argument(
    "-v", "--version", action="version", version="%(prog)s " + __version__
)
parser.add_argument(
    dest="sourceBoardFile", help="Path to the *.kicad_pcb file to be panelized"
)
parser.add_argument("--numx", type=int, help="Number of boards in X direction")
parser.add_argument("--numy", type=int, help="Number of boards in Y direction")
parser.add_argument("--padding", type=int, default=0, help="Extra space between boards")
parser.add_argument("--panelx", type=int, help="Maximum panel size in X direction")
parser.add_argument("--panely", type=int, help="Maximum panel size in Y direction")
parser.add_argument("--hrail", type=int, default=0, help="Horizontal edge rail width")
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
    "--vscoretextlayer", default="User.Comments", help="Layer to put v-score text on"
)
parser.add_argument(
    "--vscoretext", default="V-SCORE", help="Text used to indicate v-scores"
)
parser.add_argument(
    "--vscoreextends",
    type=float,
    default="-0.05",
    help="How far past the board to extend the v-score lines, defaults to -0.05",
)
args = parser.parse_args()
sourceBoardFile = args.sourceBoardFile
NUM_X = args.numx
NUM_Y = args.numy
PANEL_X = args.panelx
PANEL_Y = args.panely
PADDING = args.padding
HORIZONTAL_EDGE_RAIL_WIDTH = args.hrail
VERTICAL_EDGE_RAIL_WIDTH = args.vrail
HORIZONTAL_EDGE_RAIL_TEXT = args.hrailtext
VERTICAL_EDGE_RAIL_TEXT = args.vrailtext
V_SCORE_LAYER = args.vscorelayer
V_SCORE_TEXT_LAYER = args.vscoretextlayer
V_SCORE_TEXT = args.vscoretext
V_SCORE_LINE_LENGTH_BEYOND_BOARD = args.vscoreextends

# check that input board is a *.kicad_pcb file
sourceFileExtension = os.path.splitext(sourceBoardFile)[1]
if not sourceFileExtension == ".kicad_pcb":
    print(sourceBoardFile + " is not a *.kicad_pcb file. Quitting.")
    sys.exit()

# check that railtext is at least 1mm
if ((HORIZONTAL_EDGE_RAIL_TEXT or args.htitle) and HORIZONTAL_EDGE_RAIL_WIDTH < 2) or (
    (VERTICAL_EDGE_RAIL_TEXT or args.vtitle) and VERTICAL_EDGE_RAIL_WIDTH < 2
):
    print("Rail width must be at least 2mm if using rail text. Quitting.")
    sys.exit()

# only allow numbers or panels
if (PANEL_X or PANEL_Y) and (NUM_X or NUM_Y):
    print("Specify number of boards or size of panel, not both. Quitting.")
    sys.exit()

# expect panel size or number of boards
if (not PANEL_X or not PANEL_Y) and (not NUM_X or not NUM_Y):
    print("Specify number of boards or size of panel. Quitting.")
    sys.exit()

# warn if user has specified both rails
if HORIZONTAL_EDGE_RAIL_WIDTH and VERTICAL_EDGE_RAIL_WIDTH:
    print("Warning: do you really want both edge rails?")

# output file name is format {inputFile}_panelized.kicad_pcb
panelOutputFile = os.path.splitext(sourceBoardFile)[0] + "_panelized.kicad_pcb"

# all dimension parameters used by this script are mm unless otherwise noted
SCALE = 1000000

# v-scoring parameters
V_SCORE_TEXT_SIZE = 2
V_SCORE_TEXT_THICKNESS = 0.1

# load source board
board = pcbnew.LoadBoard(sourceBoardFile)

# set up layer table
layertable = get_layertable()

# get dimensions of board
boardWidth = board.GetBoardEdgesBoundingBox().GetWidth() + PADDING * SCALE
boardHeight = board.GetBoardEdgesBoundingBox().GetHeight() + PADDING * SCALE

# how many whole boards can we fit on the panel
if PANEL_X:
    NUM_X = int((PANEL_X * SCALE - 2 * HORIZONTAL_EDGE_RAIL_WIDTH * SCALE) / boardWidth)

if PANEL_Y:
    NUM_Y = int((PANEL_Y * SCALE - 2 * VERTICAL_EDGE_RAIL_WIDTH * SCALE) / boardHeight)

# check we can actually panelize the board
if NUM_X == 0 or NUM_Y == 0:
    print("Panel size is too small for board. Quitting.")
    sys.exit()

# array of tracks
tracks = board.GetTracks()
newTracks = []
for sourceTrack in tracks:  # iterate through each track to be copied
    for x in range(0, NUM_X):  # iterate through x direction
        for y in range(0, NUM_Y):  # iterate through y direction
            if (x != 0) or (y != 0):  # do not duplicate source object to location
                newTrack = sourceTrack.Duplicate()
                newTrack.Move(
                    pcbnew.VECTOR2I(pcbnew.wxPoint(x * boardWidth, y * boardHeight))
                )  # move to correct location
                newTracks.append(newTrack)  # add to temporary list of tracks

for track in newTracks:
    board.Add(track)

# array of drawing objects
drawings = board.GetDrawings()
newDrawings = []
for sourceDrawing in drawings:
    for x in range(0, NUM_X):
        for y in range(0, NUM_Y):
            if (x != 0) or (y != 0):
                newDrawing = sourceDrawing.Duplicate()
                newDrawing.Move(
                    pcbnew.VECTOR2I(pcbnew.wxPoint(x * boardWidth, y * boardHeight))
                )
                newDrawings.append(newDrawing)

for drawing in newDrawings:
    board.Add(drawing)

# array of modules
modules = board.GetFootprints()
newModules = []
for sourceModule in modules:
    for x in range(0, NUM_X):
        for y in range(0, NUM_Y):
            if (x != 0) or (y != 0):
                newModule = pcbnew.FOOTPRINT(sourceModule)
                newModule.SetPosition(
                    pcbnew.VECTOR2I(
                        pcbnew.wxPoint(
                            x * boardWidth + sourceModule.GetPosition().x,
                            y * boardHeight + sourceModule.GetPosition().y,
                        )
                    )
                )
                newModules.append(newModule)

for module in newModules:
    board.Add(module)

# array of zones
modules = board.GetFootprints()
newZones = []
for a in range(0, board.GetAreaCount()):
    sourceZone = board.GetArea(a)
    for x in range(0, NUM_X):
        for y in range(0, NUM_Y):
            if (x != 0) or (y != 0):
                newZone = sourceZone.Duplicate()
                newZone.SetNet(sourceZone.GetNet())
                newZone.Move(
                    pcbnew.VECTOR2I(pcbnew.wxPoint(x * boardWidth, y * boardHeight))
                )
                newZones.append(newZone)

for zone in newZones:
    board.Add(zone)

# get dimensions and center coordinate of entire array (without siderails to be added shortly)
arrayWidth = board.GetBoardEdgesBoundingBox().GetWidth()
arrayHeight = board.GetBoardEdgesBoundingBox().GetHeight()
arrayCenter = board.GetBoardEdgesBoundingBox().GetCenter()

# erase all existing edgeCuts objects (individual board outlines)
drawings = board.GetDrawings()
for drawing in drawings:
    if drawing.IsOnLayer(layertable["Edge.Cuts"]):
        drawing.DeleteStructure()

# top Edge.Cuts
edge = pcbnew.PCB_SHAPE(board)
board.Add(edge)
edge.SetStart(
    pcbnew.VECTOR2I(
        pcbnew.wxPoint(
            arrayCenter.x
            - arrayWidth / 2
            - HORIZONTAL_EDGE_RAIL_WIDTH * SCALE
            - PADDING / 2 * SCALE,
            arrayCenter.y
            - arrayHeight / 2
            - VERTICAL_EDGE_RAIL_WIDTH * SCALE
            - PADDING / 2 * SCALE,
        )
    )
)
edge.SetEnd(
    pcbnew.VECTOR2I(
        pcbnew.wxPoint(
            arrayCenter.x
            + arrayWidth / 2
            + HORIZONTAL_EDGE_RAIL_WIDTH * SCALE
            + PADDING / 2 * SCALE,
            arrayCenter.y
            - arrayHeight / 2
            - VERTICAL_EDGE_RAIL_WIDTH * SCALE
            - PADDING / 2 * SCALE,
        )
    )
)
edge.SetLayer(layertable["Edge.Cuts"])

# right Edge.Cuts
edge = pcbnew.PCB_SHAPE(board)
board.Add(edge)
edge.SetStart(
    pcbnew.VECTOR2I(
        pcbnew.wxPoint(
            arrayCenter.x
            + arrayWidth / 2
            + HORIZONTAL_EDGE_RAIL_WIDTH * SCALE
            + PADDING / 2 * SCALE,
            arrayCenter.y
            - arrayHeight / 2
            - VERTICAL_EDGE_RAIL_WIDTH * SCALE
            - PADDING / 2 * SCALE,
        )
    )
)
edge.SetEnd(
    pcbnew.VECTOR2I(
        pcbnew.wxPoint(
            arrayCenter.x
            + arrayWidth / 2
            + HORIZONTAL_EDGE_RAIL_WIDTH * SCALE
            + PADDING / 2 * SCALE,
            arrayCenter.y
            + arrayHeight / 2
            + VERTICAL_EDGE_RAIL_WIDTH * SCALE
            + PADDING / 2 * SCALE,
        )
    )
)
edge.SetLayer(layertable["Edge.Cuts"])

# bottom Edge.Cuts
edge = pcbnew.PCB_SHAPE(board)
board.Add(edge)
edge.SetStart(
    pcbnew.VECTOR2I(
        pcbnew.wxPoint(
            arrayCenter.x
            + arrayWidth / 2
            + HORIZONTAL_EDGE_RAIL_WIDTH * SCALE
            + PADDING / 2 * SCALE,
            arrayCenter.y
            + arrayHeight / 2
            + VERTICAL_EDGE_RAIL_WIDTH * SCALE
            + PADDING / 2 * SCALE,
        )
    )
)
edge.SetEnd(
    pcbnew.VECTOR2I(
        pcbnew.wxPoint(
            arrayCenter.x
            - arrayWidth / 2
            - HORIZONTAL_EDGE_RAIL_WIDTH * SCALE
            - PADDING / 2 * SCALE,
            arrayCenter.y
            + arrayHeight / 2
            + VERTICAL_EDGE_RAIL_WIDTH * SCALE
            + PADDING / 2 * SCALE,
        )
    )
)
edge.SetLayer(layertable["Edge.Cuts"])

# left Edge.Cuts
edge = pcbnew.PCB_SHAPE(board)
board.Add(edge)
edge.SetStart(
    pcbnew.VECTOR2I(
        pcbnew.wxPoint(
            arrayCenter.x
            - arrayWidth / 2
            - HORIZONTAL_EDGE_RAIL_WIDTH * SCALE
            - PADDING / 2 * SCALE,
            arrayCenter.y
            + arrayHeight / 2
            + VERTICAL_EDGE_RAIL_WIDTH * SCALE
            + PADDING / 2 * SCALE,
        )
    )
)
edge.SetEnd(
    pcbnew.VECTOR2I(
        pcbnew.wxPoint(
            arrayCenter.x
            - arrayWidth / 2
            - HORIZONTAL_EDGE_RAIL_WIDTH * SCALE
            - PADDING / 2 * SCALE,
            arrayCenter.y
            - arrayHeight / 2
            - VERTICAL_EDGE_RAIL_WIDTH * SCALE
            - PADDING / 2 * SCALE,
        )
    )
)
edge.SetLayer(layertable["Edge.Cuts"])

# re-calculate board dimensions with new edge cuts
panelWidth = board.GetBoardEdgesBoundingBox().GetWidth()
panelHeight = board.GetBoardEdgesBoundingBox().GetHeight()
panelCenter = arrayCenter  # should be the same as arrayCenter

# absolute edges of v-scoring
vscore_top = panelCenter.y - panelHeight / 2 - V_SCORE_LINE_LENGTH_BEYOND_BOARD * SCALE
vscore_bottom = (
    panelCenter.y + panelHeight / 2 + V_SCORE_LINE_LENGTH_BEYOND_BOARD * SCALE
)
vscore_right = panelCenter.x + panelWidth / 2 + V_SCORE_LINE_LENGTH_BEYOND_BOARD * SCALE
vscore_left = panelCenter.x - panelWidth / 2 - V_SCORE_LINE_LENGTH_BEYOND_BOARD * SCALE
v_scores = []

# vertical v-scores
if HORIZONTAL_EDGE_RAIL_WIDTH > 0:
    RANGE_START = 0
    RANGE_END = NUM_X + 1
else:
    RANGE_START = 1
    RANGE_END = NUM_X

for x in range(RANGE_START, RANGE_END):
    x_loc = (
        panelCenter.x
        - panelWidth / 2
        + HORIZONTAL_EDGE_RAIL_WIDTH * SCALE
        + boardWidth * x
    )
    v_score_line = pcbnew.PCB_SHAPE(board)
    v_scores.append(v_score_line)
    v_score_line.SetStart(pcbnew.VECTOR2I(pcbnew.wxPoint(x_loc, vscore_top)))
    v_score_line.SetEnd(pcbnew.VECTOR2I(pcbnew.wxPoint(x_loc, vscore_bottom)))
    v_score_line.SetLayer(layertable[V_SCORE_LAYER])
    v_score_text = pcbnew.PCB_TEXT(board)
    v_score_text.SetText(V_SCORE_TEXT)
    v_score_text.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    v_score_text.SetPosition(
        pcbnew.VECTOR2I(pcbnew.wxPoint(x_loc, vscore_top - V_SCORE_TEXT_SIZE * SCALE))
    )
    v_score_text.SetTextSize(
        pcbnew.VECTOR2I(
            pcbnew.wxSize(SCALE * V_SCORE_TEXT_SIZE, SCALE * V_SCORE_TEXT_SIZE)
        )
    )
    v_score_text.SetLayer(layertable[V_SCORE_TEXT_LAYER])
    v_score_text.SetTextAngle(pcbnew.EDA_ANGLE(900, 0))
    board.Add(v_score_text)

# horizontal v-scores
if VERTICAL_EDGE_RAIL_WIDTH > 0:
    RANGE_START = 0
    RANGE_END = NUM_Y + 1
else:
    RANGE_START = 1
    RANGE_END = NUM_Y

for y in range(RANGE_START, RANGE_END):
    y_loc = (
        panelCenter.y
        - panelHeight / 2
        + VERTICAL_EDGE_RAIL_WIDTH * SCALE
        + boardHeight * y
    )
    v_score_line = pcbnew.PCB_SHAPE(board)
    v_scores.append(v_score_line)
    v_score_line.SetStart(pcbnew.VECTOR2I(pcbnew.wxPoint(vscore_left, y_loc)))
    v_score_line.SetEnd(pcbnew.VECTOR2I(pcbnew.wxPoint(vscore_right, y_loc)))
    v_score_line.SetLayer(layertable[V_SCORE_LAYER])
    v_score_text = pcbnew.PCB_TEXT(board)
    v_score_text.SetText(V_SCORE_TEXT)
    v_score_text.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_RIGHT)
    v_score_text.SetPosition(
        pcbnew.VECTOR2I(pcbnew.wxPoint(vscore_left - V_SCORE_TEXT_SIZE * SCALE, y_loc))
    )
    v_score_text.SetTextSize(
        pcbnew.VECTOR2I(
            pcbnew.wxSize(SCALE * V_SCORE_TEXT_SIZE, SCALE * V_SCORE_TEXT_SIZE)
        )
    )
    v_score_text.SetLayer(layertable[V_SCORE_TEXT_LAYER])
    v_score_text.SetTextAngle(pcbnew.EDA_ANGLE(0, 0))
    board.Add(v_score_text)

# move vscores to edge.cuts layer
for vscore in v_scores:
    vscore.SetLayer(layertable["Edge.Cuts"])
    board.Add(vscore)

# move back to correct layer
for vscore in v_scores:
    vscore.SetLayer(layertable[V_SCORE_LAYER])

# add text to rail
if args.hrailtext:
    hrail_text = pcbnew.PCB_TEXT(board)
    hrail_text.SetText(HORIZONTAL_EDGE_RAIL_TEXT)
    hrail_text.SetTextSize(pcbnew.VECTOR2I(pcbnew.wxSize(SCALE * 1, SCALE * 1)))
    hrail_text.SetLayer(pcbnew.F_SilkS)
    hrail_text.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    hrail_text.SetPosition(
        pcbnew.VECTOR2I(
            pcbnew.wxPoint(
                panelCenter.x - panelWidth / 2 + HORIZONTAL_EDGE_RAIL_WIDTH / 2 * SCALE,
                panelCenter.y + panelHeight / 2 - SCALE * 1,
            )
        )
    )
    hrail_text.SetTextAngle(pcbnew.EDA_ANGLE(900, 0))  # rotate if on hrail
    board.Add(hrail_text)

if args.vrailtext:
    vrail_text = pcbnew.PCB_TEXT(board)
    vrail_text.SetText(VERTICAL_EDGE_RAIL_TEXT)
    vrail_text.SetTextSize(pcbnew.VECTOR2I(pcbnew.wxSize(SCALE * 1, SCALE * 1)))
    vrail_text.SetLayer(pcbnew.F_SilkS)
    vrail_text.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    vrail_text.SetPosition(
        pcbnew.VECTOR2I(
            pcbnew.wxPoint(
                panelCenter.x - panelWidth / 2 + SCALE * 1,
                panelCenter.y - panelHeight / 2 + VERTICAL_EDGE_RAIL_WIDTH / 2 * SCALE,
            )
        )
    )
    board.Add(vrail_text)

# add title text to rail
TITLE_TEXT = ""
if board.GetTitleBlock().GetTitle():
    TITLE_TEXT += str(board.GetTitleBlock().GetTitle())

if board.GetTitleBlock().GetRevision():
    TITLE_TEXT += " Rev. " + str(board.GetTitleBlock().GetRevision())

if board.GetTitleBlock().GetDate():
    TITLE_TEXT += ", " + str(board.GetTitleBlock().GetDate())

if board.GetTitleBlock().GetCompany():
    TITLE_TEXT += " (c) " + str(board.GetTitleBlock().GetCompany())

if args.htitle:
    titleblock_text = pcbnew.PCB_TEXT(board)
    titleblock_text.SetText(TITLE_TEXT)
    titleblock_text.SetTextSize(pcbnew.VECTOR2I(pcbnew.wxSize(SCALE * 1, SCALE * 1)))
    titleblock_text.SetLayer(pcbnew.F_SilkS)
    titleblock_text.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    titleblock_text.SetPosition(
        pcbnew.VECTOR2I(
            pcbnew.wxPoint(
                panelCenter.x + panelWidth / 2 - HORIZONTAL_EDGE_RAIL_WIDTH / 2 * SCALE,
                panelCenter.y + panelHeight / 2 - SCALE * 1,
            )
        )
    )
    titleblock_text.SetTextAngle(pcbnew.EDA_ANGLE(900, 0))
    board.Add(titleblock_text)

if args.vtitle:
    titleblock_text = pcbnew.PCB_TEXT(board)
    titleblock_text.SetText(TITLE_TEXT)
    titleblock_text.SetTextSize(pcbnew.VECTOR2I(pcbnew.wxSize(SCALE * 1, SCALE * 1)))
    titleblock_text.SetLayer(pcbnew.F_SilkS)
    titleblock_text.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    titleblock_text.SetPosition(
        pcbnew.VECTOR2I(
            pcbnew.wxPoint(
                panelCenter.x - panelWidth / 2 + SCALE * 1,
                panelCenter.y + panelHeight / 2 - VERTICAL_EDGE_RAIL_WIDTH / 2 * SCALE,
            )
        )
    )
    board.Add(titleblock_text)

# print report to panel
report_text = pcbnew.PCB_TEXT(board)
report_args = (
    str(panelOutputFile)
    + " ("
    + str(NUM_X)
    + "x"
    + str(NUM_Y)
    + " panel) generated with:\n./panelizer.py"
)
for x in sys.argv[1:]:
    report_args += " " + x
report_text.SetText(report_args)
report_text.SetTextSize(pcbnew.VECTOR2I(pcbnew.wxSize(SCALE * 1, SCALE * 1)))
report_text.SetLayer(layertable["User.Comments"])
report_text.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
report_text.SetPosition(
    pcbnew.VECTOR2I(pcbnew.wxPoint(panelCenter.x, vscore_bottom + 10 * SCALE))
)
board.Add(report_text)

# save output
board.Save(panelOutputFile)

# warn if panel is under 70x70mm
if panelWidth / SCALE < 70 or panelHeight / SCALE < 70:
    print("Warning: panel is under 70x70mm")

# print report
if PANEL_X or PANEL_Y:
    print("You can fit " + str(NUM_X) + " x " + str(NUM_Y) + " boards on the panel")
print(
    "Board dimensions: "
    + str(boardWidth / SCALE)
    + "x"
    + str(boardHeight / SCALE)
    + "mm"
)
print(
    "Panel dimensions: "
    + str(panelWidth / SCALE)
    + "x"
    + str(panelHeight / SCALE)
    + "mm"
)
