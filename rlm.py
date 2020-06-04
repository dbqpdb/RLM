#!/usr/bin/python
# RLM.py
#
# The python implementation of the Random Legal Move chess-playin', sass talkin', ... thing 
#
# 
versionNumber = 0.01 # Just getting started, not at all functional

import numpy as np
import re
import sys
from random import *
import time
import gzip
import pandas as pd

# Let's start off with this as a single file and refactor it into multple files when we feel 
# like this one is getting unwieldy
# --Okay. :)

class Board:
    '''A class to hold and manipulate representations of the chess board'''

    EMPTY_SQUARE = '-' # class constant, a single character string to represent an empty square

    def __init__(self, board_position=None):
        '''
        Constructor for Board class.  Optional board_position input allows construction
        from a given position.  board_position can be supplied as a numpy array of single 
        characters (which is what Board uses internally, or as an FEN-style board position
        string.
        : param board_position: a board position, specified as ndarray or FEN string
        '''
        print('running init...')
        if board_position is None:
            # default to standard starting position
            b = np.array([Board.EMPTY_SQUARE]*64).reshape((8,8))
            b[0,:] = [piece for piece in ['R','N','B','Q','K','B','N','R']] # RNBQKBNR
            b[1,:] = ['P']*8
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

    
    FILE_TO_IDX_DICT = {
        'a': 0,
        'b': 1,
        'c': 2,
        'd': 3,
        'e': 4,
        'f': 5,
        'g': 6,
        'h': 7,
        '1': 0,
        '2': 1,
        '3': 2,
        '4': 3,
        '5': 4,
        '6': 5,
        '7': 6,
        '8': 7,
        0: 0,
        1: 1,
        2: 2,
        3: 3,
        4: 4,
        5: 5,
        6: 6,
        7: 7,
    }
    def __getitem__(self, square_name):
        ''' Allows indexing into Board objects.  If b is a Board, then b['a3'] should return 
        the piece which is on square a3. This function should handle indexing in pretty much any 
        sensible way we can think of.  The actual intepretation of the square name is handled
        by square_name_to_array_idxs(), but here are ways indexing can currently be used to 
        access the contents of the a3 square: 
        b['a3'] - a two-character string, a letter for the file and a number for the rank
        b['a','3'] - two one-character strings, a letter for the file and number for the rank
        b[0, 2] - two integers, zero-based, these are indices into the board_array (but in opposite order; file, rank instead of rank, file)
        b['1', '3'] - two one-character strings, a number for the file and a number for the rank (one-based, not zero-based)
        We'll need to decide as we carry on whether the non-string inputs should be allowed and if so, whether they should be
        file, rank, (consistent with other inputs order) or rank, file (consistent with board_array index order).  
        
        The return value is either a 1 character string containing the case-sensitive piece name on that square, the 
        Board.EMPTY_SQUARE string if the square was empty, or None if the square name is invalid or off the board. 
        '''
        file_idx, rank_idx = self.square_name_to_array_idxs(square_name)
        if rank_idx is None or file_idx is None:
            return None
        else:
            return self.board_array[rank_idx, file_idx]
        
    VALID_BOARD_SQUARE_CONTENTS_PATTERN = re.compile('(^[pnbrkqPNBRKQ]$)|(^%s$)' % EMPTY_SQUARE)    

    def __setitem__(self, square_name, new_value):
        ''' Allows setting of board positions via indexing expressions. If b is a Board, then 
        b['a3'] = 'P' should place a white pawn on square 'a3' of the board. All the ways of specifiying
        a square name allowed by square_name_to_array_idxs() are allowed. new_value must be a single 
        character string with a case-sensitive piece name, or the Board.EMPTY_SQUARE string.
        '''
        assert re.match(Board.VALID_BOARD_SQUARE_CONTENTS_PATTERN, new_value), 'new_value "%s" is not a valid character to place in a Board array' % (new_value)
        file_idx, rank_idx = self.square_name_to_array_idxs(square_name)
        if rank_idx is None or file_idx is None:
            Exception('Square name "%s" did not parse to valid rank and file indices, setting board position failed!'%(square_name))
        else:
            self.board_array[rank_idx, file_idx] = new_value

    def square_name_to_array_idxs(self, square_name):
        '''This function should handle interpreting square names in pretty much any 
        sensible way we can think of.  Here are some thoughts of how it might make sense to call
        this:
        'a3' - a two-character string, a letter for the file and a number for the rank
        ['a','3'] - two one-character strings, a letter for the file and number for the rank
        [0, 2] - two integers, zero-based, these are indices into the board_array (but in opposite order; file, rank instead of rank, file)
        ['1', '3'] - two one-character strings, a number for the file and a number for the rank (one-based, not zero-based)
        We'll need to decide as we carry on whether the non-string inputs should be allowed and if so, whether they should be
        file, rank, (consistent with other inputs order) or rank, file (consistent with board_array index order).  
        '''
        assert len(square_name)==2, 'Board square names must have len 2 to be interpretable!'
        # Convert first element of square name to a file index (or None if it doesn't convert)
        file_idx = Board.FILE_TO_IDX_DICT.setdefault(square_name[0], None)
        # Try to convert second element of square name to a rank index
        try:
            if isinstance(square_name[1], str):
                rank_idx = int(square_name[1]) - 1 # go from 1-based to 0-based
            else: 
                rank_idx = int(square_name[1]) 
        except:
            # Conversion failed
            rank_idx = None
        return file_idx, rank_idx


    def move(self, source_square_name, destination_square_name):
        '''Moves whatever piece is on the source square to the destination square.
        Throws an error if the source square is empty. Returns the contents of the 
        destination square (might be handy for capture processing). Square names 
        are processed by square_name_to_array_idxs(), so any format that function 
        can handle is fine for square names.
        '''
        moving_piece = self[source_square_name]
        if moving_piece==Board.EMPTY_SQUARE:
            raise Exception('You attempted to move an empty square!')
        destination_occupant = self[destination_square_name]
        # Move the piece
        self[source_square_name] = Board.EMPTY_SQUARE # former square becomes empty
        self[destination_square_name] = moving_piece # new square filled by moving piece
        return destination_occupant # return the captured piece (or empty square if it was empty)


    def list_pieces(self):
        '''Lists all pieces which are on the board, divided into a list of white pieces
        and a list of black pieces'''
        pieces = [piece for piece in self.board_array.ravel() if not (piece==Board.EMPTY_SQUARE)]
        white_pieces = [piece for piece in pieces if piece==piece.upper()]
        black_pieces = [piece for piece in pieces if piece==piece.lower()]
        return white_pieces, black_pieces




    def __str__(self):
        '''This is called whenever a board is converted to a string (like when it is being printed)'''
        # How about something like this:
        '''
          +-------------------------------+
        8 | r | n | b | q | k | b | n | r |
          |---|---|---|---|---|---|---|---|
        7 | p | p | p | p | p | p | p | p |
          |---|---|---|---|---|---|---|---|
        6 |   |   |   |   |   |   |   |   |
          |---|---|---|---|---|---|---|---|
        5 |   |   |   |   |   |   |   |   |
          |---|---|---|---|---|---|---|---|
        4 |   |   |   |   |   |   |   |   |
          |---|---|---|---|---|---|---|---|
        3 |   |   |   |   |   |   |   |   |
          |---|---|---|---|---|---|---|---|
        2 | P | P | P | P | P | P | P | P |
          |---|---|---|---|---|---|---|---|
        1 | R | N | B | Q | K | B | N | R |
          +-------------------------------+
            a   b   c   d   e   f   g   h  
        '''
        upper_edge = '  +-------------------------------+\n'
        lower_edge = upper_edge
        internal_row_edge = '  |---|---|---|---|---|---|---|---|\n'
        make_row_string = lambda row_num, row: '%i | %c | %c | %c | %c | %c | %c | %c | %c |\n'%(row_num, *row)
        file_labels = '    a   b   c   d   e   f   g   h  \n'

        board_string = upper_edge # start with the upper edge
        for rank_num in range(8,0,-1):
            row_idx = rank_num-1
            row = list(self.board_array[row_idx,:]) # get list of piece characters (including '-' for empty squares)
            board_string += make_row_string(rank_num, row)
            if rank_num > 1:
                board_string += internal_row_edge
            else:
                board_string += lower_edge
        board_string += file_labels
        return board_string


    @classmethod
    def isValidFENboard(cls, board: str) -> bool:
        '''
        Checks that a given string is a valid FEN board representation.

        :param str board: the string to test
        :return bool: whether it's valid
        '''
        rows = board.split('/')
        if len(rows) != 8:
            return False
        for whalefart in rows:
            # if the row has a non-piece character or non 1-8 digit,
            # or the sum of represented squares is un-8-ly, return Nope
            if re.search('[^prnbqk1-8]', whalefart, re.IGNORECASE) or sum([int(x) if x.isdigit() else 1 for x in whalefart]) != 8:
                return False
        return True


    @classmethod
    def is_FEN(cls, possible_FEN: str) -> bool:
        '''
        Checks if input is a valid complete FEN
        
        :param str possible_FEN: the candidate FEN string
        :return bool: whether it's valid
        '''
        fen_fields = possible_FEN.split()
        if len(fen_fields) != 6:
            return False
        
        boardMaybe, side, castle, enpass, halfmovecounter, turnnum = fen_fields
        if not Board.isValidFENboard(boardMaybe):
            return False
        if side not in ['w', 'b']:
            return False
        # The castling string can be 1-4 "k"s and "q"s, or the string "-"
        if len(castle) not in [1, 2, 3, 4]:
            return False
        if re.search('[^qk]', castle, re.IGNORECASE) and castle != '-':
            return False
        # The en passant field can be '-' or a square representation in row 3 or 6 depending on the side.
        if enpass != '-' and not (side == 'w' and re.match('^[a-h]6$', enpass)) and not (side == 'b' and re.match('^[a-h]3$', enpass)):
            return False
        # halfmovecounter starts at 0 and increments every non-capture non-pawn-advance move; movenum starts at 1 and increments after each black move. 
        if int(halfmovecounter) < 0 or int(turnnum) < 0 or int(halfmovecounter) >= 2 * int(turnnum):
            return False
        return True


    def to_FEN_board(self):
        '''Export current board position as FEN board string'''
        row_strings = []
        for rank_idx in range(7,-1,-1):
            currently_counting_empty_squares = False
            empty_square_count = 0
            row_string = ''
            for sq in self.board_array[rank_idx,:]:
                if sq == Board.EMPTY_SQUARE:
                    if not currently_counting_empty_squares:
                        currently_counting_empty_squares = True
                        empty_square_count = 1
                    else: 
                        empty_square_count +=1
                else:
                    # non-empty square
                    if currently_counting_empty_squares:
                        # Complete the empty square count
                        currently_counting_empty_squares = False
                        row_string += '%i' % empty_square_count
                    # add piece from current square
                    row_string += sq
            if currently_counting_empty_squares:
                row_string += '%i' % empty_square_count
            row_strings.append(row_string)
        # Assemble rows into one long string with slashes between rows
        FEN_board_string = '/'.join(row_strings)
        return FEN_board_string
    
  
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

def sillyDude():
    dude = choice(['Mike', 'Bryan'])
    print("Is " + dude + " silly?:")
    def backline():        
        print(' ' * messagelen, end='')
        print('\r', end='')

    for __ in range(50):
        compute = random()
        message = "Computing... " + str(compute)
        messagelen = len(message)
        time.sleep(compute/10)
        print(message, end='')
        backline()
    backline()
    # Put it this way: if silly were a something, and Mike was a something els, he'd be somethinging the first something to some outrageous extent.
    #mikeThing = 
    #sillyThing = 
    #verb = 
    #extent = 
    print("Yes. Quite." if compute else "No. Not at all. Why do you ask?")


# Prep the dictionary
class Lexicon:
    def __init__(self, lexfile='subtlex.txt.gz'):
        '''
        Initialize a Lexicon object for use in the game.
        '''
        with gzip.open(lexfile, 'rb') as f:
            self.lex = pd.read_csv(f, sep='\t')[['Word', 'Dom_PoS_SUBTLEX']]
        self.lex.columns = ['word', 'pos']
        self.lex.pos = [str(x).lower() for x in self.lex.pos.tolist()]
        # Store a list of all PsoS of the dictionary for validation
        self.lex = {x:self.lex.loc[self.lex.pos == x].word.tolist() for x in set(self.lex.pos)}
        
    def squawk_pos(self):
        '''
        Report which PsoS are represented in the dictionary
        '''
        return {key:len(self.lex[key]) for key in self.lex.keys()}

    def spew(self, pos: str) -> str:
        '''
        Spew out a random word of a given part-of-speech

        :param str pos: a part-of-speech labeled in the lexicon
        :return str bleh: a random word of the given POS
        '''
        bleh = choice(self.lex[pos])
        return bleh


class Loudmouth:
    '''
    Loudmouth'll be the class that implements commenting methods.
    '''
    def __init__(self):
        self.noggin = Lexicon()

    def propound(self, template: str):
        '''
        Propound takes a template of the form
        "This {noun} is a {adverb} {adjective} {noun}."
        and inserts random words from the relevant classes.
        '''
        fill = [x.strip("{}") for x in re.findall('\{.+?\}', template)]
        template = re.sub("\{.*?\}", "{}", template)
        self.noggin.squawk_pos()
        print(template.format(*[self.noggin.spew(x) for x in fill]))


def run_me_if_i_am_the_main_file():
    
    # Prepare the loudmouth
    me = Loudmouth()

    # This function is called if you run "python rlm.py"
    print('I am running!!!')
    # Create a board with no inputs
    startingBoard = Board()
    print('Board array generated from no inputs: \n%s'%(str(startingBoard.board_array)))
    me.propound("{interjection}! I haven't been {adverb} implemented yet. What kind of {noun} do you {verb} me to {verb}? {noun}?!?")
    # Test FEN conversion function
    FEN_board_string = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
    board_array_from_FEN = Board.convert_FEN_to_board_array(FEN_board_string)
    print('Board array generated from FEN board string "%s": \n%s'%(FEN_board_string, board_array_from_FEN))
    me.propound("If {noun}s were {noun}s, man, you'd {adverb} {verb} {determiner} {noun}!")
    # Create a board from a different FEN-type string
    FEN_board_string_2 = "rnbqkbnr/pp1ppppp/8/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2" # after 1. e4 c5; 2. Nf3 
    otherBoard = Board(FEN_board_string_2)
    print('Board array generated from FEN board string "%s": \n%s'%(FEN_board_string_2, str(otherBoard.board_array)))
    me.propound("There once was a {noun} named {name} from a {adjective} {noun}. Anyway, {pronoun} {adverb} {verb}s.")
    # Create a board from an existing board array
    board_array_from_FEN[4,4] = 'Q' # add a white queen at e5
    boardFromArray = Board(board_array_from_FEN)
    print('Board array generated from array: \n%s'%(str(boardFromArray.board_array)))
    me.propound("Don't forget to {adverb} {verb} your {noun} {preposition} {determiner} {adjective} {noun}. Otherwise, you know, your {noun} might {verb}.")

    # Print the board object directly
    print('Board object printed directly:')
    print(boardFromArray)
    # Ask and answer critical question
    sillyDude()


def run_him_if_i_am_not_the_main_file():
    print("Interesting; you thought it'd be a good idea to import a random-move-playing chess engine from some other application. How droll!")

if __name__ == '__main__':
    run_me_if_i_am_the_main_file()
else:
    run_him_if_i_am_not_the_main_file()
