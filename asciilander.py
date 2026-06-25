#!/usr/bin/env python3
import random
import threading
import time
import sys
import os
from math import floor

# different console interfaces depending on os
if sys.platform.startswith('win'):
  winterm = True
  import msvcrt
else:
  winterm = False
  import tty
  import termios

# useful ansi control seqs
clear_screen = chr(27)+"c"
goto_top_left = chr(27)+"[1;1H"

# global char (omg!) so key-handler thread can pass latest key to main thread
global lastkey
global keeplistening

# global constant
planetwidth = 1024

# unbuffered print without newline
def p(s):
  print(s,end="",flush=True)

# make array of "depth" levels (height-elevation)
def prepterrain(w,h):
  groundy = [0] * w
  y = floor(h*0.50)
  delta_y = 1
  for x in range(0,w):
    rand = random.randint(0,6)
    if rand == 0:
      delta_y = 1
    elif rand == 1:
      delta_y = -1
    elif rand == 2:
      delta_y = 0
    elif rand == 3 and y >= floor(h*0.85):
      delta_y = -1
    elif rand == 3 and y <= floor(h*0.35):
      delta_y = 1
    if y >= floor(h*0.9):
      delta_y = -1
    elif y <= floor(h*0.25):
      delta_y = 1
    y += delta_y
    groundy[x] = y
  return groundy

# leave space above ground blank
# fill space at and below ground with X
def drawground(w,h,frame_x,frame_y,groundy):
  for y in range(frame_y,frame_y+h):
    jump(0,y-frame_y)
    for x in range(frame_x,frame_x+w):
      if y >= groundy[x % planetwidth]:
        p("X")
      else:
        p(" ")

# ansi control seq to go to position on screen
def jump(x,y):
  # indexed from 1,1 (!)
  p(chr(27)+"["+str(floor(y)+1)+";"+str(floor(x)+1)+"H")
def draw_at_screen_xy(s,x,y):
  jump(x,y)
  p(s)
def draw_at_universe_xy(s,frame_x,frame_y,x,y):
  draw_at_screen_xy(s,x - frame_x,y - frame_y)
def draw_at_screen_center(s,w,h):
  draw_at_screen_xy(s, floor(w*0.5) - floor(len(s)*0.5), floor(h*0.5) )

# update position
def moveship(x,y,delta_x,delta_y):
  x += delta_x
  y += delta_y
  if floor(x) < 0:
    x += planetwidth
  elif floor(x) >= planetwidth:
    x -= planetwidth
  return x,y

# loop in key-monitoring thread 
# records keypresses in lastkey global variable,
# where main game loop thread can read it
def keythreadfunc():
  global latestkey
  global keeplistening
  latestkey = '?'
  while keeplistening:
    # if running in windows use msvcrt.getch() and map results to ascii
    if winterm:
      latestkey = msvcrt.getch()
      if latestkey == b'\xe0':
        latestkey = msvcrt.getch()
        if latestkey == b'K':
          latestkey = 'h'
        elif latestkey == b'M':
          latestkey = 'l'
      elif latestkey == b' ':
        latestkey = ' '
    # in linux/wsl just read one byte from stdin
    else:
      latestkey = sys.stdin.read(1)

# main game loop thread calls this to
# grab latest key,posted by keythreadfunc,
# and adjust heading
def keycontrols(ship_delta_x, ship_delta_y, fuel):
  global latestkey
  if fuel <= 0:
    fuel = 0
  elif latestkey == ' ':
    ship_delta_y -= 0.1
    fuel -= 1
  elif latestkey == 'h' or latestkey == chr(8) or latestkey == chr(68):
    ship_delta_x -= 0.1
    fuel -= 1
  elif latestkey == 'l' or latestkey == chr(12) or latestkey == chr(67):
    ship_delta_x += 0.1
    fuel -= 1
  latestkey = "?"
  return ship_delta_x, ship_delta_y, fuel
    
def game():
  # printed in upper right corner
  helpmsg = "hit <- or -> or space"

  # set up random surface of planet
  groundy = prepterrain(planetwidth, os.get_terminal_size().lines)

  # screen size
  scrnwidth = 0
  scrnheight = 0
  # position of visible part of game universe 
  frame_x = 0
  frame_y = 0

  # position and heading of ship
  ship_x = planetwidth * 0.5
  ship_y = 0
  ship_delta_x = random.randint(-5,5)*0.1
  ship_delta_y = 0
  fuel = 20

  # game loop
  loopctr = 0
  while True:
    # re-orient frame?
    movedframe = False
    termsize = os.get_terminal_size()
    if termsize.columns != scrnwidth or termsize.lines != scrnheight:
      scrnwidth = termsize.columns
      scrnheight = termsize.lines
      movedframe = True
    if ship_x < frame_x + scrnwidth * 0.25 or ship_x > frame_x + scrnwidth * 0.75: 
      frame_x = floor(ship_x - scrnwidth * 0.5)
      movedframe = True
    if ship_y < frame_y or ship_y > frame_y + scrnheight * 0.9:
      frame_y = floor(ship_y - 5)
      movedframe = True
    
    # draw background?
    if movedframe:
      p(clear_screen)
      drawground(scrnwidth,scrnheight,frame_x,frame_y,groundy)

    # erase ship at old pos, move, redraw
    draw_at_universe_xy("   ",frame_x,frame_y,floor(ship_x-1),floor(ship_y))
    ship_x,ship_y = moveship(ship_x,ship_y,ship_delta_x,ship_delta_y)
    draw_at_universe_xy("/o\\",frame_x,frame_y,floor(ship_x-1),floor(ship_y))

    # show user current position
    jump(scrnwidth-len(helpmsg),0)
    p(helpmsg)
    fuelbang = "!" if fuel == 0 and int(loopctr/10)%2 == 0 else ""    
    p(goto_top_left + "x={0:0.1f} y={1:0.1f} dx={2:0.2f} dy={3:0.2f} fuel={4}{5}   ".format(
      ship_x,scrnheight-ship_y,
      ship_delta_x,ship_delta_y*-0.1,
      fuel, fuelbang ))

    # gravity!
    ship_delta_y += 0.01
    # adjust heading from keystrokes
    ship_delta_x, ship_delta_y, fuel = keycontrols(ship_delta_x, ship_delta_y, fuel)
    # check for landing/crash
    if floor(ship_y) >= groundy[floor(ship_x)]-1:
      if groundy[floor(ship_x)] == groundy[floor(ship_x)+1] and groundy[floor(ship_x)] == groundy[floor(ship_x)-1]:
        if ship_delta_y >= 0.25 or abs(ship_delta_x) >= 0.25:
          draw_at_universe_xy(">X<",frame_x,frame_y,floor(ship_x-1),floor(ship_y))
          draw_at_screen_center("*** !!!HARD LANDING!!! ***",scrnwidth,scrnheight)          
        else:
          draw_at_screen_center("*** !!!LANDED!!! ***",scrnwidth,scrnheight)
      else:  
        draw_at_universe_xy(">X<",frame_x,frame_y,floor(ship_x-1),floor(ship_y))
        draw_at_screen_center("*** !!!CRASHED!!! *** ",scrnwidth,scrnheight)
      p(goto_top_left)
      time.sleep(0.5)
      break

    # wait short interval so game doesn't finish instantly    
    time.sleep(0.1)
    loopctr += 1

if __name__ == "__main__":
  # set stdin to unbuffered so we can get keystrokes immediately, and cache console state
  # this is for linux/wsl only
  if not winterm:
    old_settings = termios.tcgetattr(sys.stdin.fileno())
    tty.setraw(sys.stdin.fileno())
  # hide cursor
  p(chr(27)+"[?25l")
  # start key handling thread
  global keeplistening
  keeplistening = True
  kbth = threading.Thread(target=keythreadfunc)
  kbth.start()
  # main game func
  game()
  # tell keyboard thread to quit
  keeplistening = False;
  kbth.join()
  # reset terminal. seems to happen automatically in windows terminal
  if not winterm:
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
  p(clear_screen)
