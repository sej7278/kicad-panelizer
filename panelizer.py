#!/usr/bin/env python3

import os
import sys
from argparse import ArgumentParser
from pathlib import Path
import pcbnew
from pcbnew import *

"""
A simple script to create a v-scored panel of a KiCad board.
Author: Willem Hillier
This script is very much in-progress, and so here's an extensive TODO list:
    - Put report in panel file in a text field
    - Put logo/text block on panel border
    - Put fuducials on border
    - Auto-calculate distance from line to text center ("V-SCORE") based on text size
    - Is there a way to pull back copper layers to the pullback distances so if the user presses "b" on the panel, it doesn't get wrecked (by copper getting too close to V-scores)
    - (maybe) Make a "DRC" that checks if copper is too close to V-score lines
"""

# set up command-line arguments parser
parser = ArgumentParser(description="A script to panelize KiCad files.")
parser.add_argument(dest="sourceBoardFile", help='Path to the *.kicad_pcb file to be panelized')
parser.add_argument('-x', '--numx', type=int, help='Number of boards in X direction')
parser.add_argument('-y', '--numy', type=int, help='Number of boards in Y direction')
parser.add_argument('--hrail', type=int, default=0, help='Horizontal edge rail width')
parser.add_argument('--vrail', type=int, default=0, help='Vertical edge rail width')
args = parser.parse_args()
sourceBoardFile = args.sourceBoardFile
NUM_X = args.numx
NUM_Y = args.numy
HORIZONTAL_EDGE_RAIL_WIDTH = args.hrail
VERTICAL_EDGE_RAIL_WIDTH = args.vrail

# check that input board is a *.kicad_pcb file
sourceFileExtension = os.path.splitext(sourceBoardFile)[1]
if not(sourceFileExtension == '.kicad_pcb'):
    print(sourceBoardFile + " is not a *.kicad_pcb file. Quitting.")
    quit()

# output file name is format {inputFile}_panelized.kicad_pcb
panelOutputFile = os.path.splitext(sourceBoardFile)[0] + "_panelized.kicad_pcb"

# all dimension parameters used by this script are mm unless otherwise noted
SCALE = 1000000

# v-scoring parameters
V_SCORE_LAYER = "Eco1.User"
V_SCORE_LINE_LENGTH_BEYOND_BOARD = 20
V_SCORE_TEXT_CENTER_TO_LINE_LENGTH = 10
V_SCORE_TEXT = "V-SCORE"
V_SCORE_TEXT_SIZE = 2
V_SCORE_TEXT_THICKNESS = 0.1

# creates a list that can be used to lookup layer numbers by their name
def get_layertable():
    layertable = {}
    numlayers = pcbnew.PCB_LAYER_ID_COUNT
    for i in range(numlayers):
        layertable[board.GetLayerName(i)] = i
    return layertable

# load source board
board = LoadBoard(sourceBoardFile)

# set up layer table
layertable = get_layertable()

# get dimensions of board
boardWidth = board.GetBoardEdgesBoundingBox().GetWidth()
boardHeight = board.GetBoardEdgesBoundingBox().GetHeight()

# array of tracks
tracks = board.GetTracks()
newTracks = []
for sourceTrack in tracks:                          # iterate through each track to be copied
    for x in range(0,NUM_X):                        # iterate through x direction
        for y in range(0, NUM_Y):                   # iterate through y direction
            if((x!=0)or(y!=0)):                     # do not duplicate source object to location
                newTrack = sourceTrack.Duplicate()
                newTrack.Move(wxPoint(x*boardWidth, y*boardHeight)) # move to correct location
                newTracks.append(newTrack)          # add to temporary list of tracks

for track in newTracks:
    tracks.Append(track)

# array of drawing objects
drawings = board.GetDrawings()
newDrawings = []
for drawing in drawings:
    for x in range(0,NUM_X):
        for y in range(0, NUM_Y):
            if((x!=0)or(y!=0)):
                newDrawing = drawing.Duplicate()
                newDrawing.Move(wxPoint(x*boardWidth, y*boardHeight))
                newDrawings.append(newDrawing)

for drawing in newDrawings:
    board.Add(drawing)

# array of modules
modules = board.GetModules()
newModules = []
for sourceModule in modules:
    for x in range(0,NUM_X):
        for y in range(0, NUM_Y):
            if((x!=0)or(y!=0)):
                newModule = pcbnew.MODULE(sourceModule)
                newModule.SetPosition(wxPoint(x*boardWidth + sourceModule.GetPosition().x, y*boardHeight + sourceModule.GetPosition().y))
                newModules.append(newModule)

for module in newModules:
    board.Add(module)

# array of zones
modules = board.GetModules()
newZones = []
for a in range(0,board.GetAreaCount()):
    sourceZone = board.GetArea(a)
    for x in range(0,NUM_X):
        for y in range(0, NUM_Y):
            if((x!=0)or(y!=0)):
                newZone = sourceZone.Duplicate()
                newZone.SetNet(sourceZone.GetNet())
                newZone.Move(wxPoint(x*boardWidth, y*boardHeight))
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
    if(drawing.IsOnLayer(layertable["Edge.Cuts"])):
        drawing.DeleteStructure()

# top Edge.Cuts
edge = pcbnew.DRAWSEGMENT(board)
board.Add(edge)
edge.SetStart(pcbnew.wxPoint(arrayCenter.x - arrayWidth/2 - HORIZONTAL_EDGE_RAIL_WIDTH*SCALE, arrayCenter.y - arrayHeight/2 - VERTICAL_EDGE_RAIL_WIDTH*SCALE))
edge.SetEnd( pcbnew.wxPoint(arrayCenter.x + arrayWidth/2 + HORIZONTAL_EDGE_RAIL_WIDTH*SCALE, arrayCenter.y - arrayHeight/2 - VERTICAL_EDGE_RAIL_WIDTH*SCALE))
edge.SetLayer(layertable["Edge.Cuts"])

# right Edge.Cuts
edge = pcbnew.DRAWSEGMENT(board)
board.Add(edge)
edge.SetStart(pcbnew.wxPoint(arrayCenter.x + arrayWidth/2 + HORIZONTAL_EDGE_RAIL_WIDTH*SCALE, arrayCenter.y - arrayHeight/2 - VERTICAL_EDGE_RAIL_WIDTH*SCALE))
edge.SetEnd( pcbnew.wxPoint(arrayCenter.x + arrayWidth/2 + HORIZONTAL_EDGE_RAIL_WIDTH*SCALE, arrayCenter.y + arrayHeight/2 + VERTICAL_EDGE_RAIL_WIDTH*SCALE))
edge.SetLayer(layertable["Edge.Cuts"])

# bottom Edge.Cuts
edge = pcbnew.DRAWSEGMENT(board)
board.Add(edge)
edge.SetStart( pcbnew.wxPoint(arrayCenter.x + arrayWidth/2 + HORIZONTAL_EDGE_RAIL_WIDTH*SCALE, arrayCenter.y + arrayHeight/2 + VERTICAL_EDGE_RAIL_WIDTH*SCALE))
edge.SetEnd( pcbnew.wxPoint(arrayCenter.x - arrayWidth/2 - HORIZONTAL_EDGE_RAIL_WIDTH*SCALE, arrayCenter.y + arrayHeight/2 + VERTICAL_EDGE_RAIL_WIDTH*SCALE))
edge.SetLayer(layertable["Edge.Cuts"])

# left Edge.Cuts
edge = pcbnew.DRAWSEGMENT(board)
board.Add(edge)
edge.SetStart( pcbnew.wxPoint(arrayCenter.x - arrayWidth/2 - HORIZONTAL_EDGE_RAIL_WIDTH*SCALE, arrayCenter.y + arrayHeight/2 + VERTICAL_EDGE_RAIL_WIDTH*SCALE))
edge.SetEnd( pcbnew.wxPoint(arrayCenter.x - arrayWidth/2 - HORIZONTAL_EDGE_RAIL_WIDTH*SCALE, arrayCenter.y - arrayHeight/2 - VERTICAL_EDGE_RAIL_WIDTH*SCALE))
edge.SetLayer(layertable["Edge.Cuts"])

# re-calculate board dimensions with new edge cuts
panelWidth = board.GetBoardEdgesBoundingBox().GetWidth()
panelHeight = board.GetBoardEdgesBoundingBox().GetHeight()
panelCenter = arrayCenter # should be the same as arrayCenter

# absolute edges of v-scoring
vscore_top = panelCenter.y - panelHeight/2 - V_SCORE_LINE_LENGTH_BEYOND_BOARD*SCALE
vscore_bottom = panelCenter.y + panelHeight/2 + V_SCORE_LINE_LENGTH_BEYOND_BOARD*SCALE
vscore_right = panelCenter.x + panelWidth/2 + V_SCORE_LINE_LENGTH_BEYOND_BOARD*SCALE
vscore_left = panelCenter.x - panelWidth/2 - V_SCORE_LINE_LENGTH_BEYOND_BOARD*SCALE
v_scores = []

# vertical v-scores
for x in range(1,NUM_X):
    x_loc = panelCenter.x - panelWidth/2 + HORIZONTAL_EDGE_RAIL_WIDTH*SCALE + boardWidth*x
    v_score_line = pcbnew.DRAWSEGMENT(board)
    v_scores.append(v_score_line)
    v_score_line.SetStart(pcbnew.wxPoint(x_loc, vscore_top))
    v_score_line.SetEnd(pcbnew.wxPoint(x_loc, vscore_bottom))
    v_score_line.SetLayer(layertable[V_SCORE_LAYER])
    v_score_text = pcbnew.TEXTE_PCB(board)
    v_score_text.SetText(V_SCORE_TEXT)
    v_score_text.SetPosition(wxPoint(x_loc, vscore_top - V_SCORE_TEXT_CENTER_TO_LINE_LENGTH*SCALE))
    v_score_text.SetTextSize(pcbnew.wxSize(SCALE*V_SCORE_TEXT_SIZE,SCALE*V_SCORE_TEXT_SIZE))
    v_score_text.SetLayer(layertable[V_SCORE_LAYER])
    v_score_text.SetTextAngle(900)
    board.Add(v_score_text)

# horizontal v-scores
for y in range(0,NUM_Y+1):
    y_loc = panelCenter.y - panelHeight/2 + VERTICAL_EDGE_RAIL_WIDTH*SCALE + boardHeight*y
    v_score_line = pcbnew.DRAWSEGMENT(board)
    v_scores.append(v_score_line)
    v_score_line.SetStart(pcbnew.wxPoint(vscore_left, y_loc))
    v_score_line.SetEnd(pcbnew.wxPoint(vscore_right, y_loc))
    v_score_line.SetLayer(layertable[V_SCORE_LAYER])
    v_score_text = pcbnew.TEXTE_PCB(board)
    v_score_text.SetText(V_SCORE_TEXT)
    v_score_text.SetPosition(wxPoint(vscore_left - V_SCORE_TEXT_CENTER_TO_LINE_LENGTH*SCALE, y_loc))
    v_score_text.SetTextSize(pcbnew.wxSize(SCALE*V_SCORE_TEXT_SIZE,SCALE*V_SCORE_TEXT_SIZE))
    v_score_text.SetLayer(layertable[V_SCORE_LAYER])
    v_score_text.SetTextAngle(0)
    board.Add(v_score_text)

# move vscores to edge.cuts layer
for vscore in v_scores:
    vscore.SetLayer(layertable["Edge.Cuts"])
    board.Add(vscore)

# move back to correct layer
for vscore in v_scores:
    vscore.SetLayer(layertable[V_SCORE_LAYER])

# save output
board.Save(panelOutputFile)

# print report
print("Board dimensions: " + str(boardWidth/SCALE) + "x" + str(boardHeight/SCALE) + "mm")
print("Panel dimensions: " + str(panelWidth/SCALE) + "x" + str(panelHeight/SCALE) + "mm")
