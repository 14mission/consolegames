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
def keycontrols(keepgoing,fastdrop,col,boardwidth):
  global latestkey
  if latestkey == 'h' or latestkey == chr(8) or latestkey == chr(68):
    if col > 0:
      col -= 1
  elif latestkey == 'l' or latestkey == chr(12) or latestkey == chr(67):
    if col < boardwidth-1:
      col += 1
  elif latestkey == 'x' or latestkey == chr(27):
    keepgoing = False
  elif latestkey == ' ':
    fastdrop = True
  latestkey = "?"
  return keepgoing,fastdrop,col
    
def game(wordlist):
  # printed in upper right corner
  p(clear_screen)
  helpmsg = "hit <- or ->e"

  # game loop
  col = 0
  row = 0
  curltr = None
  speed = 0.1
  fastdrop = False
  keepgoing = True
  wantnewltr = True
  loopctr = 0
  boardheight = 25
  boardwidth = 5
  onboard = []
  for i in range(boardheight):
    onboard.append([None for j in range(boardwidth)])
  while keepgoing:
    try:
      # init new letter?
      if wantnewltr == True:
        curltr = chr(random.randint(ord('A'),ord('Z')))
        row = 0
        col = random.randint(0,boardwidth)
        wantnewltr = False
      # erase falliung letter at old pos
      jump(col,row)
      p(' ')
      # key controls, update col, maybe turn on fast mode
      keepgoing, fastdrop, col = keycontrols(keepgoing, fastdrop, col, boardwidth)
      # gravity
      newrow = row + (1 if fastdrop else speed)
      if newrow > boardheight or onboard[int(newrow)][col] != None:
        newrow = boardheight
        wantnewltr = True
        fastdrop = False
        onboard[int(row)][col] = curltr
      else:
        row = newrow
      # draw letter at new pos
      jump(col,row)
      p(curltr)

      # wait short interval so game doesn't finish instantly    
      time.sleep(0.1)
      loopctr += 1
    except Exception as e:
      return e
  return None

if __name__ == "__main__":
  # set stdin to unbuffered so we can get keystrokes immediately, and cache console state
  # this is for linux/wsl only
  if not winterm:
    old_settings = termios.tcgetattr(sys.stdin.fileno())
    tty.setraw(sys.stdin.fileno())
  # load wordlist
  wordset = {}
  wlistfn = os.path.join(sys.path[0], "words.txt")
  wlist = open(wlistfn)
  for ln in wlist:
    ln = ln.strip()
    if len(ln) != 5:
      raise Exception("non-5-letter word: "+ln)
    ln = ln.upper()
    wordset[ln] = True
  print("numwords: "+str(len(wordset.keys())))
  # hide cursor
  p(chr(27)+"[?25l")
  # start key handling thread
  global keeplistening
  keeplistening = True
  kbth = threading.Thread(target=keythreadfunc)
  kbth.start()
  # main game func
  gameExcept = game(wordset)
  # tell keyboard thread to quit
  keeplistening = False;
  kbth.join()
  # reset terminal. seems to happen automatically in windows terminal
  if not winterm:
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
  p(clear_screen)
  if gameExcept != None:
    print(str(gameExcept))
