#
# RLM.py
#
# The python implementation of the Random Legal Move chess-playin', sass talkin', ... thing 
#
# 
versionNumber = 0.01 # Just getting started, not at all functional

import numpy as np
import re

# Let's start off with this as a single file and refactor it into multple files when we feel 
# like this one is getting unwieldy

class Board:
  '''A class to hold and manipulate representations of the chess board'''
  
  EMPTY_SQUARE = '-'

  def __init__(self, board_position=None):
    ''' Constructor for Board class.  Optional board_position input allows construction
    from a given position.  board_position can be supplied as a numpy array of single 
    characters (which is what Board uses internally, or as an FEN-style board position
    string.'''
    print('running init...')
    if board_position is None:
      # default to standard starting position
      b = np.array(['p']*64).reshape((8,8))
      b[0,:] = [piece for piece in ['R','N','B','Q','K','B','N','R']] # RNBQKBNR
      b[1,:] = ['P']*8
      for rankIdx in range(2,6):
        b[rankIdx,:] = [Board.EMPTY_SQUARE]*8
      b[6,:] = ['p']*8
      b[7,:] = [piece for piece in ['r','n','b','q','k','b','n','r']]
      self.board_array = b
    else: 
      # a board_position was supplied check if it's valid 
      if isinstance(board_position, np.ndarray):
        if board_position.shape==(8,8) and board_position.dtype==np.dtype('<U1'): 
          # right shape and data type
          self.board_array = np.copy(board_position) # make a copy of the input array, don't just use a reference!
        else:
          raise Exception('Input array has wrong shape or data type!')
      elif self.is_FEN(board_position):
        # Convert FEN to array 
        self.board_array = self.convert_FEN_to_board_array(board_position)
      else:
        # Couldn't interpret board position input, throw an error
        raise Exception("Couldn't interpret board position input as 8x8 numpy array of single characters or as FEN board position!")


  def is_FEN(self, possible_FEN):
    '''Checks if input is a valid FEN or FEN board position'''
    #TODO: actually write this function
    return True 
  
  @classmethod
  def convert_FEN_to_board_array(cls, FEN):
    '''Converts FEN or FEN board position to a board array and returns it'''
    # FEN's look like "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    FEN_board = FEN.split()[0] # keep only first part of FEN if full FEN    
    FEN_chars = list(FEN_board)
    # NB that FEN order is increasing column, then decreasing row
    squareIdx = 0
    board_array = np.array([Board.EMPTY_SQUARE]*64).reshape(8,8)
    valid_pieces = list('rnbqkpRNBQKP') # split into list of characters
    valid_digits = list('12345678')
    for char in FEN_chars:
      if char in valid_pieces:
        # This character is a piece, add it to the board array
        fileIdx = squareIdx % 8 
        rankIdx, fileIdx = cls.squareIdx_to_boardIdxs(squareIdx)
        board_array[rankIdx, fileIdx] = char
        squareIdx+=1 # increment
      elif char in valid_digits: 
        # This character is a number, representing that many empty squares
        squareIdx+= int(char)
      elif char=='/':
        # This character is a slash, ignore it
        pass
      else:
        # This character is not a valid FEN board position character! 
        raise Exception('Invalid character "%s" found in FEN input'%(char))
    return board_array

  @classmethod
  def squareIdx_to_boardIdxs(cls, squareIdx, board_size=(8,8)):
    # FEN square index to board_array indices.  Must take into
    # account that ranks are in a different order and that board
    # array indices are 0-based.
    # First FEN square is board_array[7,0], next is [7,1], 
    # 8th is [7,7], 9th is [6,0], 10th is [6,1], 64th is [0,7]
    # So, if we take squareIdx to be 0-based, mappings are looking like 
    # [0] -> [7,0]
    # [1] -> [7,1]
    # [7] -> [7,7]
    # [8] -> [6,0]
    # [10] -> [6,2]
    # [63] -> [0,7]
    #
    # OK, so we can get the file index by taking the square idx mod 8
    fileIdx = squareIdx % board_size[1]
    # The rank index is based on the floor of the square idx / 8 
    rankIdx = int(7 - np.floor(squareIdx/board_size[0]))
    return rankIdx, fileIdx

def run_me_if_i_am_the_main_file():
  # This function is called if you run "python rlm.py"
  print('I am running!!!')
  # Create a board with no inputs
  startingBoard = Board()
  print('Board array generated from no inputs: \n%s'%(str(startingBoard.board_array)))
  # Test FEN conversion function
  FEN_board_string = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
  board_array_from_FEN = Board.convert_FEN_to_board_array(FEN_board_string)
  print('Board array generated from FEN board string "%s": \n%s'%(FEN_board_string, board_array_from_FEN))
  # Create a board from a different FEN-type string
  FEN_board_string_2 = "rnbqkbnr/pp1ppppp/8/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2" # after 1. e4 c5; 2. Nf3 
  otherBoard = Board(FEN_board_string_2)
  print('Board array generated from FEN board string "%s": \n%s'%(FEN_board_string_2, str(otherBoard.board_array)))
  # Create a board from an existing board array
  board_array_from_FEN[4,4] = 'Q' # add a white queen at e5
  boardFromArray = Board(board_array_from_FEN)
  print('Board array generated from array: \n%s'%(str(boardFromArray.board_array)))

  

if __name__ == '__main__':
  run_me_if_i_am_the_main_file()

      
