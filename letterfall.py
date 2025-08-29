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

# unbuffered print without newline
def p(s):
  print(s,end="",flush=True)

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
def keycontrols(col):
  global latestkey
  if latestkey == 'h' or latestkey == chr(8) or latestkey == chr(68):
    col -= 1
    if col < 0:
      col = 0
  elif latestkey == 'l' or latestkey == chr(12) or latestkey == chr(67):
    col += 1
    if col > 4:
      col = 4
  elif latestkey == 'x':
    col = -1
  latestkey = "?"
  return col
    
def game():
  # printed in upper right corner
  p(clear_screen)
  helpmsg = "hit <- or ->e"

  #wordlist = loadwordlist()

  # game loop
  col = 2
  loopctr = 0
  while True:
    jump(col,col)
    p(' ')
    col = keycontrols(col)
    if col == -1:
      return
    jump(col,col)
    p(str(col))

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
