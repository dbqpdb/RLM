#!/usr/bin/python
# RLM.py
#
# The python implementation of the Random Legal Move chess-playin', sass talkin', ... thing 
#
# 
versionNumber = 0.20 # legal move generation may be working!

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
    # In the terminal, the unicode glyphs actually look reversed, so:

    def __init__(self, board_position=None, piece_list=None):
        '''
        Constructor for Board class.  Optional board_position input allows construction
        from a given position.  board_position can be supplied as a numpy array of single 
        characters (which is what Board uses internally, or as an FEN-style board position
        string. Alternatively, a list of Piece objects can be supplied, and the board
        constructed by placing each piece based on its 'current_square' property
        : param board_position: a board position, specified as ndarray or FEN string
        : param piece_list: a list of Piece objects to place on an empty board
        '''
        
        self.pieces = ['P', 'R', 'N', 'B', 'Q', 'K', 'p', 'r', 'n', 'b', 'q', 'k']
        self.glyphs = ['♟︎', '♜', '♞', '♝', '♛', '♚', '♙', '♖', '♘', '♗', '♕', '♔']
        self.glyphmap = dict(zip(self.pieces, self.glyphs))
        self.use_glyphs = True

        #print('running init...')
        if board_position is None and piece_list is None:
            # default to standard starting position
            b = np.array([Board.EMPTY_SQUARE]*64).reshape((8,8))
            b[0,:] = [piece for piece in ['R','N','B','Q','K','B','N','R']] # RNBQKBNR
            b[1,:] = ['P']*8
            b[6,:] = ['p']*8
            b[7,:] = [piece for piece in ['r','n','b','q','k','b','n','r']]
            self.board_array = b
        elif board_position is not None:
            # a board_position was supplied, check if it's valid 
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
        elif piece_list is not None:
            # Make board from pieces
            b = np.array([Board.EMPTY_SQUARE]*64).reshape((8,8))
            for piece in piece_list:
                file_idx, rank_idx = self.square_name_to_array_idxs(piece.current_square)
                b[rank_idx, file_idx] = piece.char  # NB that indexing into numpy array is rank,file whereas everywhere else we use file,rank
            self.board_array = b

    
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
    IDX_TO_FILE_DICT = {
        0: 'a',
        1: 'b',
        2: 'c',
        3: 'd',
        4: 'e',
        5: 'f',
        6: 'g',
        7: 'h',
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
            return self.board_array[rank_idx, file_idx] # NB that indexing into numpy array is rank,file whereas everywhere else we use file,rank
        
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
            self.board_array[rank_idx, file_idx] = new_value # NB that indexing into numpy array is rank,file whereas everywhere else we use file,rank

    @classmethod
    def square_name_to_array_idxs(cls, square_name):
        '''This function should handle interpreting square names in pretty much any 
        sensible way we can think of.  Here are some thoughts of how it might make sense to call
        this:
        'a3' - a two-character string, a letter for the file and a number for the rank
        ['a','3'] - two one-character strings, a letter for the file and number for the rank
        [0, 2] - two integers, zero-based, these are indices into the board_array (but in opposite order; file, rank instead of rank, file)
        ['1', '3'] - two one-character strings, a number for the file and a number for the rank (one-based, not zero-based)
        We'll need to decide as we carry on whether the non-string inputs should be allowed and if so, whether they should be
        file, rank, (consistent with other inputs order) or rank, file (consistent with board_array index order).  
        Returns file, rank.  If either can't be interpreted or are off board, that index is returned as None
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
            if rank_idx < 0 or rank_idx > 7:
                rank_idx = None # off board
        except:
            # Conversion failed
            rank_idx = None
        
        return file_idx, rank_idx


    def copy(self):
        '''Return a copy of the existing board'''
        board_copy = Board(board_position=self.board_array )
        return board_copy

    def move(self, source_square_name, destination_square_name):
        '''Moves whatever piece is on the source square to the destination square.
        Throws an error if the source square is empty. Returns the contents of the 
        destination square (might be handy for capture processing). Square names 
        are processed by square_name_to_array_idxs(), so any format that function 
        can handle is fine for square names.
        NOTE that this currently does not update any Piece objects, only the board representation!!
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
        and a list of black pieces. (Note that these are single characters, not Piece objects)'''
        pieces = [piece for piece in self.board_array.ravel() if not (piece==Board.EMPTY_SQUARE)]
        white_pieces = [piece for piece in pieces if piece==piece.upper()]
        black_pieces = [piece for piece in pieces if piece==piece.lower()]
        return white_pieces, black_pieces

    @classmethod
    def is_same_square(cls, square_name_1, square_name_2):
        # Returns True if square name 1 and 2 refer to the same board location, even if they are in different formats
        # If not, or if either is None, returns False
        if square_name_1 is None or square_name_2 is None:
            return False
        else:
            # Standardize and compare
            sq1 = cls.square_name_to_array_idxs(square_name_1)
            sq2 = cls.square_name_to_array_idxs(square_name_2)
            return sq1==sq2

    @classmethod
    def square_rank_str(cls, square_idxs):
        # Returns the rank number as a single character string
        return str(int(square_idxs[1]))

    @classmethod
    def square_file_lett(cls, square_idxs):
        # Returns the file letter as a single character string
        file_idx = square_idxs[0]
        file_lett = Board.IDX_TO_FILE_DICT[file_idx]
        return file_lett

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
            row_string = make_row_string(rank_num, row)
            # Substitute glyphs for letters if requested...
            if self.use_glyphs:
                for piece, glyph in self.glyphmap.items():
                    row_string = row_string.replace(piece, glyph)
            board_string += row_string
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
    

    def find_king_square(self, color):
        ''' Should return the square of the king of the given color (color should start 
        with 'w' or 'b', case insensitive, representing white or black). Square is returned as 
        algebraic string'''
        color_letter = color[0].lower()
        if color_letter == 'w':
            K_str = 'K'
        elif color_letter == 'b':
            K_str = 'k'
        #
        rank_idx_tuple, file_idx_tuple = np.where(self.board_array == K_str)
        square_str = Board.IDX_TO_FILE_DICT[file_idx_tuple[0]] + str(rank_idx_tuple[0] + 1)
        return square_str

  
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



    @classmethod
    def square_to_alg_name(cls, square_name):
        '''Convert any square representation to algebraic square name, i.e. letter file followed by 1-based rank'''
        sq_arr = cls.square_name_to_array_idxs(square_name) # standardize
        alg_name = cls.IDX_TO_FILE_DICT[sq_arr[0]] + "%i" % (sq_arr[1] + 1) # convert
        return alg_name


class Move:
    '''Should handle having an internal representation of moves and converting to various output
    representations 
    '''
    def __init__(self, char, starting_square, destination_square, captured_piece=None, is_castling=False, promotion_piece=None, is_en_passant_capture=False, new_en_passant_square=None):
        ''' Move representation keeps track of everything needed to relate to moves. 
        '''
        self.single_char = char
        self.starting_square = Board.square_name_to_array_idxs(starting_square) # standardize to array idxs
        self.destination_square = Board.square_name_to_array_idxs(destination_square)# standardize to array idxs
        self.captured_piece = captured_piece
        self.is_castling = is_castling
        self.promotion_piece = promotion_piece
        self.is_en_passant_capture = is_en_passant_capture
        self.new_en_passant_square = new_en_passant_square


    def is_capture(self):
        return not (self.captured_piece is None)

    def is_promotion(self):
        return not (self.promotion_piece is None)

    def to_tuple(self):
        # For debugging, this is a way to return the move in the internal format which is used in initialization
        move_tuple = (self.single_char, self.starting_square, self.destination_square, self.captured_piece, self.is_castling, self.promotion_piece, self.is_en_passant_capture, self.new_en_passant_square)
        return move_tuple

    def to_long_algebraic(self, use_figurine=False, note_ep=False):
        '''Long algebraic includes starting and destination square'''
        if use_figurine:
            p = self.PIECE_TO_FIGURINE_DICT[self.single_char]
        else:
            p = self.single_char.upper()
        start_sq = self.square_to_string(self.starting_square)
        dest_sq = self.square_to_string(self.destination_square)
        if self.is_castling:
            # figure out if kingside or queenside
            if self.destination_square[0]> self.starting_square[0]:
                move_string = 'O-O' # kingside
            else:
                move_string = 'O-O-O' # queenside
        else:
            cap_str = '' if self.captured_piece is None else 'x'
            prom_str = '' if self.promotion_piece is None else '='+self.promotion_piece.upper()
            move_string = p + start_sq + cap_str + dest_sq + prom_str
            if self.is_en_passant_capture and note_ep:
                move_string += 'e.p.' #add notation that this capture is en passant
        return move_string
    

    def to_short_algebraic(self, board):
        # Same as long algebraic except drop destination square
        # TODO: actually, this should have a lot more logic so it includes elements of starting square if necessary
        # TODO: hmm, to do this, we actually need the board, because that's what we need to resolve ambiguities
        p = self.single_char
        start_sq = self.square_to_string(self.starting_square)
        dest_sq = self.square_to_string(self.destination_square)
        if self.is_castling:
            # figure out if kingside or queenside
            if self.destination_square[0]> self.starting_square[0]:
                move_string = 'O-O' # kingside
            else:
                move_string = 'O-O-O' # queenside
        else:
            cap_str = '' if self.captured_piece is None else 'x'
            prom_str = '' if self.promotion_piece is None else '='+self.promotion_piece.upper()
            move_string = p + start_sq + cap_str + dest_sq + prom_str
        return move_string
        
    # Currently, this is duplicated in the Board class, could revisit to explore whether it should be reworked to just appear one place or whether this is more convenient
    IDX_TO_FILE_DICT =  {
        0: 'a',
        1: 'b',
        2: 'c',
        3: 'd',
        4: 'e',
        5: 'f',
        6: 'g',
        7: 'h',
    }
    PIECE_TO_FIGURINE_DICT = { # using named unicode code point
        'P': '\N{WHITE CHESS PAWN}',
        'N': '\N{WHITE CHESS KNIGHT}',
        'B': '\N{WHITE CHESS BISHOP}',
        'R': '\N{WHITE CHESS ROOK}',
        'Q': '\N{WHITE CHESS QUEEN}',
        'K': '\N{WHITE CHESS KING}',
        'p': '\N{BLACK CHESS PAWN}',
        'n': '\N{BLACK CHESS KNIGHT}',
        'b': '\N{BLACK CHESS BISHOP}',
        'r': '\N{BLACK CHESS ROOK}',
        'q': '\N{BLACK CHESS QUEEN}',
        'k': '\N{BLACK CHESS KING}',
    }


    def __str__(self):
        '''String representation of Move class.'''
        return self.to_long_algebraic() # just use long algebraic for now

    def __repr__(self):
        '''String representation for Move objects (this one shows up for example in lists)'''
        return 'MoveObject.['+str(self)+']'

    @classmethod
    def square_to_string(cls, sq):
        '''Convert array indices to string'''
        # should this handle non-array index square representations also?
        file_letter = cls.IDX_TO_FILE_DICT[sq[0]]
        rank_number = '%i'%(sq[1]+1)
        return file_letter+rank_number

    @classmethod
    def parse_move_without_game(cls, entered_move, white_is_moving=True, make_assumptions=False):
        ''' This function tries to extract as much information as possible from an entered move text string,
        parsing it into move elements.  It keeps track of what move elements are known, what remain unknown,
        and what have some partial information (e.g. a piece was captured, but it wasn't specified which).
        The goal is to be able to use the extracted information to choose the correct, fully specified Move
        from a list of legal Move objects generated from the Game state, AND to be able to explain why there
        is no match if there is no match (or how the matches differ if there are multiple matches)
        This function returns a dict with the following keys: 
        ['single_char','starting_file', 'starting_rank','destination_square',
        'captured_piece','is_castling','promotion_piece','is_en_passant_capture',
        'new_en_passant_square']
        The values will be either "unknown" if the move element cannot be determined from the entered move,
        or "not_None" if the move element was determined to be not None but couldn't be further specified (this
        is possible for captured_piece and promotion_piece), or else it will be the known value of that move
        element.  
        In order to get the piece capitalization parts correct, to determine squares if castling, and key ranks
        for pawns, it is necessary to know who is moving (white or black). The argument "white_is_moving" is 
        treated as boolean throughout and if evaluates to False, then black is considered to be moving. 
        The 'make_assumptions' argument controls whether the moving piece is assumed to be a pawn if no moving
        piece is specified. In general, this should probably be True if we wanted to guess in the abstract what
        a person most likely meant, but it should probably be False if we are going to use a Game legal move 
        list to narrow down what they could have meant.  In that case it is better to leave the piece as unknown
        and see what the known move elements match.  Since the plan is to mostly use this function to compare
        with legal move lists, the default is False. 
        '''
        black_is_moving = not white_is_moving
        kingside_castling_patt = re.compile(r"^\s*([oO0])-\1\s*")
        queenside_castling_patt = re.compile(r"^\s*([oO0])-\1-\1\s*")
        no_dest_capture_patt = re.compile(r"""
            ^\s*
            (?P<moving_piece>[KQRBNPkqrbnp]) # pieces which can capture
            x
            (?P<captured_piece>[QRBNPqrbnp]) # pieces which can be captured
            [+]? # check indicator (optional and ignored)
            \s*$
            """, re.VERBOSE) # Matches moves like RxB with no square information
        normal_move_patt = re.compile(r"""
            \s*                             # ignore any leading whitespace
            (?P<piece_char>[KQRBNPkqrbnp])? # piece character, if present (optional for pawns)
            (?P<starting_file>[a-h])?(?P<starting_rank>[1-8])? # any elements of the source square, if present
            (?P<capture_indicator>[xX][QRBNqrbn]?)?        # capture indicator, if present (this is always optional, but we could use it to catch user error if they try to capture an empty square)
            (?P<dest_square>[a-h][1-8])     # destination square (the only non-optional part of the move for this pattern)
            ( (?P<promotion_indicator>=)    # pawn promotion is indicated by = sign
                (?P<promotion_piece>[QRBNqrbn]) # promotion piece character
            )?  # promotion indicator and piece (required for pawn promotion, required to be absent for all other moves)
            (?P<ep_capture_indicator>e[.]?p[.]?)? # optional ep or e.p. to indicate en passant capture (always optional but could use to catch user errors)
            [+]? # check indicator (optional and ignored)      
            \s*$                            # Ignore any trailing whitespace
            """, re.VERBOSE)

        move_elements = ['single_char','starting_file', 'starting_rank','destination_square','captured_piece','is_castling','promotion_piece','is_en_passant_capture','new_en_passant_square']
        move_elem_dict = {}
        for e in move_elements:
            move_elem_dict[e] = 'unknown'
        notNone  = "not_None"
        msg = 'Other Messages:\n'
        # Queenside castling (queenside first because kingside pattern will match queenside castling)
        if queenside_castling_patt.match(entered_move):
            # Queenside castling
            move_elem_dict['is_castling'] = True
            move_elem_dict['captured_piece'] = None
            move_elem_dict['promotion_piece'] = None
            move_elem_dict['is_en_passant_capture'] = False
            move_elem_dict['new_en_passant_square'] = None
            if white_is_moving:
                move_elem_dict['single_char'] = 'K'
                move_elem_dict['starting_file'] = 'e'
                move_elem_dict['starting_rank'] = '1'
                move_elem_dict['destination_square'] = 'c1'
            elif black_is_moving:
                move_elem_dict['single_char']  = 'k'
                move_elem_dict['starting_file'] = 'e'
                move_elem_dict['starting_rank'] = '8'
                move_elem_dict['destination_square'] = 'c8'
        # Kingside castling
        elif kingside_castling_patt.match(entered_move):
            move_elem_dict['is_castling'] = True
            move_elem_dict['captured_piece'] = None
            move_elem_dict['promotion_piece'] = None
            move_elem_dict['is_en_passant_capture'] = False
            move_elem_dict['new_en_passant_square'] = None
            if white_is_moving:
                move_elem_dict['single_char'] = 'K'
                move_elem_dict['starting_file'] = 'e'
                move_elem_dict['starting_rank'] = '1'
                move_elem_dict['destination_square'] =  'g1'
            elif black_is_moving:
                move_elem_dict['single_char']  = 'k'
                move_elem_dict['starting_file'] = 'e'
                move_elem_dict['starting_rank'] = '8'
                move_elem_dict['destination_square'] =  'g8'
        elif no_dest_capture_patt.match(entered_move):
            # can tell moving piece, captured piece, and know that new_en_passant_square should be None
            m = no_dest_capture_patt.match(entered_move)
            single_char = m.group('moving_piece')
            captured_piece = m.group('captured_piece')
            move_elem_dict['single_char'] = single_char.upper() if white_is_moving else single_char.lower()
            move_elem_dict['captured_piece'] = captured_piece.lower() if white_is_moving else captured_piece.upper()
            move_elem_dict['new_en_passant_square'] = None # a capture cannot generate a new ep square
            move_elem_dict['is_castling'] = False
            if single_char.lower()!='p' or captured_piece.lower()!='p':
                move_elem_dict['is_en_passant_capture'] = False # only pawn take pawn could be ep capture
            if single_char.lower()!='p':
                move_elem_dict['promotion_piece'] = None # non-pawns can't promote
            elif captured_piece.lower()=='p':
                move_elem_dict['promotion_piece'] = None # if you captured a pawn you can't be promoting, because an enemy pawn can't be on the final rank
        elif normal_move_patt.match(entered_move):
            move_elem_dict['is_castling'] = False
            m = normal_move_patt.match(entered_move)
            destination_square = m.group('dest_square') # this is the only non-optional part of the match, this must be present if we are in this branch
            move_elem_dict['destination_square'] = destination_square
            single_char = m.group('piece_char') # may be None
            starting_rank = m.group('starting_rank') # may be None
            if starting_rank is not None:
                move_elem_dict['starting_rank'] = starting_rank
            starting_file = m.group('starting_file') # may be None
            if starting_file is not None:
                move_elem_dict['starting_file'] = starting_file
            capture_indicator = m.group('capture_indicator') # may be x or x<piece> or None
            promotion_indicator = m.group('promotion_indicator')
            promotion_piece = m.group('promotion_piece') # may be None
            ep_capture_indicator = m.group('ep_capture_indicator') # may be None
            
            # Piece_char?
            if single_char is None and make_assumptions:
                # Assume pawn 
                single_char = 'P' if white_is_moving else 'p'
                msg += 'assumed "P" for missing piece character\n'
            if single_char is not None:
                single_char = single_char.upper() if white_is_moving else single_char.lower()
                move_elem_dict['single_char'] = single_char
            # Captured piece?
            if capture_indicator is not None:
                if  len(capture_indicator)==2:
                    captured_piece = capture_indicator[1].lower() if white_is_moving else capture_indicator[1].upper()
                    move_elem_dict['captured_piece'] = captured_piece
                else:
                    move_elem_dict['captured_piece'] = notNone
                    msg += 'we know there was a capture (captured piece not None), but not what piece was captured\n'
            # Promotion piece?
            if single_char and single_char.lower() != 'p':
                # if piece is known and not a pawn, can't be promotion
                move_elem_dict['promotion_piece'] = None # non-pawns can't promote
            elif destination_square[1] != '8' and destination_square[1] !='1':
                # no matter what the piece (known or unknown), if not going to rank 1 or 8 can't be promoting
                move_elem_dict['promotion_piece'] = None
            elif single_char and single_char.lower() == 'p':
                # pawn moving to last rank, must involve promotion!
                if promotion_piece is not None:
                    move_elem_dict['promotion_piece'] = promotion_piece
                else:
                    move_elem_dict['promotion_piece'] = notNone
                    msg += "promotion_piece is not None, but we don't know what it should be\n"
            else:
                # single_char is None, and destination_square is on first or last rank
                # Promotion state is unknown, could be a pawn promoting or could be a non-pawn not promoting.
                # However, if the user specified a promotion piece, then safe to assume unspecified piece is 
                # a pawn and that promotion is taking place. Otherwise don't assume either way
                if promotion_piece is not None:
                    move_elem_dict['promotion_piece'] = promotion_piece
                    move_elem_dict['single_char'] = 'P' if white_is_moving else 'p'

            # E.P. Capture? and/or New EP Square?
            if single_char and single_char.lower() != 'p':
                # non-pawn moving piece
                move_elem_dict['is_en_passant_capture'] = False # can't be ep capture if moving piece is not a pawn
                move_elem_dict['new_en_passant_square'] = None # non-pawn moves can't create ep squares
            elif single_char and single_char.lower() == 'p':
                # moving piece IS a pawn
                if ep_capture_indicator is not None:
                    move_elem_dict['is_en_passant_capture'] = True # if moving piece is a pawn 
                    if capture_indicator is not None and len(capture_indicator)==2:
                        # captured piece already assigned and marked known
                        pass
                    else:
                        move_elem_dict['captured_piece'] = 'P' if white_is_moving else 'p'
                    move_elem_dict['new_en_passant_square'] = None # ep captures can't create new ep squares
                # Otherwise, the only way to know an ep square creation state is to know the moving piece and the starting and destination squares
                if starting_file is not None and starting_rank is not None:
                    if starting_rank=='2' and destination_square[1]=='4':
                        new_en_passant_square = destination_square[0]+'3'
                    elif starting_rank=='7' and destination_square[1]=='5':
                        new_en_passant_square = destination_square[0]+'6'
                    else:
                        new_en_passant_square = None
                    move_elem_dict['new_en_passant_square'] = new_en_passant_square
            else:
                # Moving piece is unknown, might be a pawn, might not
                # However, if the destination square is not on the proper rank, it
                # cannot possibly be an ep capture
                if (white_is_moving and destination_square[1] != '6') or (black_is_moving and destination_square[1] != '3'):
                    move_elem_dict['is_en_passant_capture'] = False
                elif starting_rank and ((white_is_moving and starting_rank != '5') or (black_is_moving and starting_rank != '4')):
                    # Even if destination rank is correct for ep capture, we can still rule it out if the starting rank 
                    # is not correct for possible ep capture
                    move_elem_dict['is_en_passant_capture'] = False

                # Likewise, if the destination square is not on the proper rank, it
                # cannot possibly create a new ep square
                if (white_is_moving and destination_square[1] !='4') or (black_is_moving and destination_square[1] != '5'):
                    move_elem_dict['new_en_passant_square'] = None
                elif starting_rank and ((white_is_moving and starting_rank != '2') or (black_is_moving and starting_rank !='7')):
                    # Even if destination square is the right rank, if the starting square isn't the right rank, then 
                    # it is impossible to generate a new ep square
                    move_elem_dict['new_en_passant_square'] = None

        # Conditional tree traversed, let's take a look at the results
        print("Move Elements")
        for key, value in move_elem_dict.items():
            print("%s: %s"%(key, str(value)))
        print(msg)

        # Could have a dict where move element names are keys, and all initially have value of 'unknown'
        # Then could fill in with actual value or with 'notNone', or leave as 'unknown'
        # Then, for unpacking, can check if value is 'unknown', 'notNone', or something else (means known)
        # TODO: could add reason_dict with move element keys and reasons as values (i.e. "because only pawns can promote", or "because castling can't cause captures")
        return move_elem_dict

    @classmethod
    def find_matches_to_partial_move(cls, partial_move_dict, move_list):
        ''' Find all possible matches where every known or partially known element of partial_move_dict 
        is consistent with a Move object on the given move_list. partial_move_dict should be the 
        output of parse_move_without_game().  
        '''
        unk = 'unknown'
        notNone = 'not_None'
        pmd = partial_move_dict # save typing
        matched_moves = []
        for move in move_list:
            # Check each field
            if (pmd['single_char']==unk or (move.single_char == pmd['single_char'])
                and (pmd['starting_file']==unk or (Board.square_file_lett(move.starting_square) == pmd['starting_file']))
                and (pmd['starting_rank']==unk or (Board.square_rank_str(move.starting_square) == pmd['starting_rank']))
                and (pmd['destination_square']==unk or (Board.square_to_alg_name(move.destination_square) == pmd['destination_square']))
                and (pmd['captured_piece']==unk or (move.captured_piece == pmd['captured_piece']) or (pmd['captured_piece']==notNone and move.captured_piece is not None)) 
                and (pmd['is_castling']==unk or (move.is_castling == pmd['is_castling']))
                and (pmd['promotion_piece']==unk or (pmd['promotion_piece']==notNone and move.promotion_piece is not None) or (move.promotion_piece == pmd['promotion_piece']))
                and (pmd['is_en_passant_capture']==unk or (pmd['is_en_passant_capture'] == move.is_en_passant_capture))
                and (pmd['new_en_passant_square']==unk or (pmd['new_en_passant_square'] == move.new_en_passant_square))
                ):
                matched_moves.append(move)
        return matched_moves

    
    @classmethod
    def parse_entered_move(entered_move, game=None, legal_move_list=None):
        '''Parse human-entered move string to a Move object'''
        ''' 
        Need to determine:
        * piece character
        * source square
        * destination square
        * captured_piece (by inspection of dest square?)
        * is_castling 
        * promotion_piece
        * is_en_passant_capture
        * new_en_passant_square (if two square pawn move)
        *
        Some of these would require a Game object to determine, especially if
        the user uses an abbreviated move format. Legal move list might be helpful for 
        narrowing down possibilities. Given a Game object, the legal move list could be generated if not given. 

        Examples we might need to parse:
        e4 (pawn on e file which can reach e4, could be on e2 or e3)
        exd5 (pawn on e file captures whatever piece is on d5)
        Rxc1 (rook which can reach c1 captures whatever is on c1)
        RxBc1 (rook which can reach c1 captures a bishop on c1)
        Rc1 (rook which can reach c1 moves to or captures whatever is c1)
        Rac1 (Rook on a1 moves to c1 (to disambiguate from another rook which can reach c1))
        R1c1 (rook on first rank moves to c1 (to disambiguate from, e.g. a rook on c3 which could also reach c1))
        o-o or O-O or 0-0 (kingside castling using letter o or numeral zero)
        RxB (whatever rook can capture a bishop does so, look through legal move list for one which matches, request clarification if ambiguous)
        Nb1c3 (easiest form, has source and destination squares and piece name)
        '''

        kingside_castling_patt = re.compile(r"^\s*([oO0])-\1\s*")
        queenside_castling_patt = re.compile(r"^\s*([oO0])-\1-\1\s*")
        no_dest_capture_patt = re.compile(r"""
            ^\s*
            (?P<moving_piece>[KQRBNPkqrbnp]) # pieces which can capture
            x
            (?P<captured_piece>[QRBNPqrbnp]) # pieces which can be captured
            [+]? # check indicator (optional and ignored)
            \s*$
            """, re.VERBOSE) # Matches moves like RxB with no square information
        normal_move_patt = re.compile(r"""
            \s*                             # ignore any leading whitespace
            (?P<piece_char>[KQRBNPkqrbnp])? # piece character, if present (optional for pawns)
            (?P<source_square>[a-h]?[1-8])? # any elements of the source square, if present
            (?P<capture_indicator>x[QRBNqrbn]?)?        # capture indicator, if present (this is always optional, but we could use it to catch user error if they try to capture an empty square)
            (?P<dest_square>[a-h][1-8])     # destination square (the only non-optional part of the move for this pattern)
            ( (?P<promotion_indicator>=)    # pawn promotion is indicated by = sign
              (?P<promotion_piece>[QRBNqrbn]) # promotion piece character
            )?  # promotion indicator and piece (required for pawn promotion, required to be absent for all other moves)
            (?P<ep_capture_indicator>e[.]?p[.]?) # optional ep or e.p. to indicate en passant capture (always optional but could use to catch user errors)
            [+]? # check indicator (optional and ignored)      
            \s*$                            # Ignore any trailing whitespace
            """, re.VERBOSE)

        # Determine side to move from either the game or the list of legal moves
        if game is not None:
            side_to_move = game.side_to_move[0]
        elif legal_move_list is not None and len(legal_move_list)>0:
            if legal_move_list[0].single_char==legal_move_list[0].single_char.upper():
                side_to_move = 'w'
            else:
                side_to_move = 'b'
        else: 
            # Can't yet determine side to move
            side_to_move = None #unsure

        msg = None
        # Queenside castling (queenside first because kingside pattern will match queenside castling)
        if queenside_castling_patt.match(entered_move):
            # Queenside castling
            if side_to_move == 'w':
                move = Move('K','e1', 'c1', is_castling=True)
            elif side_to_move == 'b':
                move = Move('k','e8', 'c8', is_castling=True)
            elif side_to_move is None:
                move = None
                msg = "Move parses as queenside castling, but without a Game object or a legal move list, it was impossible to guess which side was moving!"
        # Kingside castling
        elif kingside_castling_patt.match(entered_move):
            if side_to_move == 'w':
                move = Move('K', 'e1', 'g1', is_castling=True)
            elif side_to_move == 'b':
                move = Move('k', 'e8', 'g8', is_castling=True)
            elif side_to_move is None:
                move = None
                msg = "Move parses as kingside castling, but without a Game object or a legal move list, it was impossible to guess which side was moving!"
        # Abbreviated capture moves (like RxB)
        elif no_dest_capture_patt.match(entered_move):
            # We will need to use the legal move list to narrow down what the user could mean, the entered move may be ambiguous
            m = no_dest_capture_patt.match(entered_move)
            moving_piece = m.group('moving_piece')
            captured_piece = m.group('captured_piece')
            if legal_move_list is not None:
                if side_to_move == 'w':
                    moving_piece = moving_piece.upper()
                    captured_piece = captured_piece.lower()
                elif side_to_move == 'b':
                    moving_piece = moving_piece.lower()
                    captured_piece = captured_piece.upper()
                # Narrow down by moving piece and captured piece
                possible_moves = [m for m in legal_move_list if m.single_char == moving_piece and m.captured_piece == captured_piece]
                if len(possible_moves)==0:
                    move = None
                    msg = "There does not seem to be a legal move where your piece '%s' captures an enemy piece '%s'!"%(moving_piece, captured_piece)
                elif len(possible_moves)==1:
                    # One possible match, assume this is the move intended
                    move = possible_moves[0]
                else:
                    # Multiple possible moves
                    move = None
                    msg = "Your move, %s, is ambiguous, which of the following do you mean: %s"
                    for m in possible_moves[1:]:
                        msg += ',or %s'%(m.to_long_algebraic())
                    msg += '?\n'
            else:
                # No move list available
                move = None
                msg = "An abbreviated capture move, such as you entered, can't be parsed without a non-empty list of legal moves!"  
        # Normal moves (minimally including a destination square)
        elif normal_move_patt.match(entered_move):
            m = normal_move_patt.match(entered_move)
            piece_char = m.group('piece_char') # may be None
            source_square = m.group('source_square')
            capture_indicator = m.group('capture_indicator')
            dest_square = m.group('dest_square') # this is the only non-optional part of the match, this must be present if we are in this branch
            promotion_indicator = m.group('promotion_indicator')
            promotion_piece = m.group('promotion_piece')
            # There are two approaches we could take here... build the move as far as possible from the entered input, THEN use the legal move list 
            # to narrow down any ambiguities, OR, we could start from the legal move list, narrow it down to those with the correct destination square
            # and then compare from there...
            if legal_move_list is not None:
                possible_legal_moves = [m for m in legal_move_list if Board().is_same_square(m.destination_square, dest_square)]
            if piece_char is None: 
                if source_square is None:
                    # No piece char and no source square, impossible to disambiguate without the legal moves list
                    if legal_move_list is not None:
                        # Try to determine full move by matching destination square alone. 
                        if len(possible_legal_moves)==0:
                            move = None
                            msg = "Your entered move, %s, omits the moving piece and it's starting square. There appear to be no legal moves which have %s as a destination square"%(entered_move, dest_square)
                        elif len(possible_legal_moves)==1:
                            move = possible_legal_moves[0]
                        else:
                            move = None
                            msg = "Your entered move, %s, omits the moving piece and it's starting square. There appear to be multiple legal moves which have %s as a destination square, please disambiguate"%(entered_move, dest_square)
                            # OR could assume pawn move here...
                    else: # no legal move list available
                        move = None
                        msg = "Your entered move, %s, omits the moving piece and \nit's starting square.  In the absence of a game or legal move list, \nI can't guess what all the move characteristics would be."%(entered_move) 
                else:
                    # piece_char is none, but at least one element of source square is provided
                    # This section needs to determine the piece char and the full source square (if only partial is provided)
                    if len(source_square)==2:
                        # full source square is provided, we can supply the piece by looking on the board if we have a Game
                        if game is not None:
                            piece_char = game.board[source_square]
                            if piece_char == Board.EMPTY_SQUARE:
                                return None, 'Your entered move starts from %s, but there is no piece on that square!'%(source_square)
                        elif legal_move_list is not None:
                            # look through legal moves for one with the correct destination square 
                            if len(possible_legal_moves)==0:
                                move = None
                                msg = "Your entered move, %s, indicates a destination square of %s and omits an indication of the moving piece.\nHowever, there are no legal moves to that destination square!"%(entered_move, dest_square)
                                return move, msg
                            elif len(possible_legal_moves)==1:
                                only_legal_move = possible_legal_moves[0]
                                if capture_indicator is not None and not only_legal_move.is_capture():
                                    move = None
                                    msg = "You indicated a capture in your move, but there is no piece to capture on %s!"%(dest_square)
                                else:
                                    # No other important way the user could have entered a conflicting move, just use the only legal move
                                    move = only_legal_move 
                                    return move, msg
                            elif len(possible_legal_moves)>1:
                                # Multiple legal moves to the destination square, use the one which comes from the given source square
                                # (possible exception is pawn promotion, where there could be multiple moves with the same source and destination square, just different promotion pieces)
                                moves_with_correct_starting_square = [m for m in possible_legal_moves if Board().is_same_square(m.source_square, source_square)]
                                if len(moves_with_correct_starting_square)==0:
                                    move = None
                                    msg = "Your entered move, %s, indicates a destination square of %s and a\n source square of %s, but there don't appear to be any legal moves from and to those squares!"%(entered_move,dest_square,source_square)
                                elif len(moves_with_correct_starting_square)==1:
                                    move = moves_with_correct_starting_square[0]
                                else: # more than one legal move with same source and destination squares (must be pawn promotion)
                                    if promotion_piece is None:
                                        move = None
                                        msg = "Your entered move, %s, matches multiple legal moves, did you forget to supply a promotion piece (e.g. =Q)?"%(entered_move)
                                    else:
                                        # Find the move with the matching promotion piece (disregarding case)
                                        moves_with_matching_promotion = [m for m in moves_with_correct_starting_square if m.promotion_piece.upper()==promotion_piece.upper()]
                                        if len(moves_with_matching_promotion)==0:
                                            # I don't think this case should actually be reachable... (matching source and destination, promotion piece specified, there should always be one match)
                                            move = None
                                            msg = "Your entered move, %s, seems to indicate pawn promotion to '%s', but that move does not appear to be a legal move."%(entered_move, promotion_piece)
                                        elif len(moves_with_matching_promotion)==1:
                                            move = moves_with_matching_promotion[0]
                                        else: 
                                            move = None
                                            msg = "Your entered move, %s, matches multiple legal moves, \nthough I'm not sure how that's possible since you've specified a source square (%s), \ndestination square (%s), and promotion piece (%s)."%(entered_move, source_square, dest_square, promotion_piece)
                        else:
                            # game and legal move list and piece character not provided, but source and destination squares provided
                            # Should we force assumption of pawn move in this case? I think we need to report it as not parseable
                            move = None
                            msg = "Your entered move, %s, can't be parsed into a full Move object because you have omitted the moving piece character, and without a game or legal move list, it is impossible to deduce the color or type of piece moving."%(entered_move)
                    elif len(source_square)==1:
                        # piece char is none, and only one element (the file or the rank) is provided, definitely need to narrow stuff down
                        if legal_move_list is None:
                            move=None
                            msg = "Your entered move, %s, can't be parsed without a game or legal move list, because it is missing the piece character and part of the source square."%(entered_move)
                        else: # legal move list is not None
                            # Try to find a match from the possible_legal_moves list
                            # (this is trickier because we only have a partial indicator of the source square, either the file or the rank, but not both)
                            file_is_known = source_square in 'abcdefABCDEF'
                            rank_is_known = source_square in '12345678'
                            if file_is_known:
                                moves_with_matching_file = [m for m in possible_legal_moves if Board.square_file_lett(m.starting_square)==source_square.lower()]
                                if len(moves_with_matching_file)==0:
                                    move=None
                                    msg = "Your entered move, %s, is missing both piece information and full starting square information. \nThere does not appear to be any legal move going from the %s-file to %s."%(entered_move, source_square, dest_square)
                                elif len(moves_with_matching_file)==1:
                                    move = moves_with_matching_file[0]
                                else: # len >1
                                    move = None
                                    msg = "Your entered move, %s, is not sufficient to disambiguate among the possible legal moves. \nYou may need to fully specify the starting square or a promotion piece."%(entered_move)
                            elif rank_is_known:
                                moves_with_matching_rank = [m for m in possible_legal_moves if Board().square_rank_str(m.starting_square)==source_square]
                                if len(moves_with_matching_rank)==0:
                                    move = None
                                    msg = "Your entered move, %s, is missing both piece information and full starting square information. \nThere does not appear to be any legal move going from ranks %s to %s."%(entered_move, source_square, dest_square)
                                elif len(moves_with_matching_rank)==1:
                                    move = moves_with_matching_rank[0]
                                else: # len > 1
                                    move = None
                                    msg = "Your entered move, %s, is not sufficient to disambiguate among the possible legal moves. \nYou may need to fully specify the starting square or a promotion piece."%(entered_move)
                            else:
                                move = None
                                msg = "No piece char, source square SAID it partially matched, but neither file nor rank appears to be known at this point. Not sure what's gone wrong."
            else: # piece_char is not None  
                # Can now use piece character to help narrow down choices when there is ambiguity
                if source_square is None:
                    # Have piece character but no source square, need to disambiguate using move list
                    correct_piece_moves = [m for m in possible_legal_moves if m.char.upper()==piece_char.upper()]
                    if len(correct_piece_moves)==0:
                        move = None
                        msg = "Your entered move, %s, omits the starting square. There appear to be no '%s' pieces which can legally move to %s, so we can't parse your move."%(entered_move, piece_char, dest_square)
                    elif len(correct_piece_moves)==1:
                        move = correct_piece_moves[0]
                    else: # len>1
                        move = None
                        msg = "Your entered move, %s, omits the starting square.  There appear to be multiple '%s' pieces which can legally move to %s, so you need to provide more information to disambiguate!"%(entered_move, piece_char, dest_square)
                else: # Piece char and source square are both not None
                    if len(source_square)==2:
                        # source square is fully specified, as well as piece and destination square should be ready to 
                        pass

             

        
  
        return move, msg # None if couldn't parse?, TODO: maybe add msg about why if we can figure that out?
    # important test case: Rb1xb5 (meaning Rook takes piece on b5, but might be read as Rb1 takes a bishop (xb) but then unable to parse the destination square)
    #move_tuple = (
    # self.single_char, # could assume pawn if not specified and no game or move list
    # self.starting_square, # if unspec or partially spec, can't guess w/o game or legal move list
    # self.destination_square, # can't guess w/o game or legal move list 
    # self.captured_piece, # can't tell unless capture indicator and piece specified with capture indicator
    # self.is_castling, # obvious from entered move, it's either castling or not
    # self.promotion_piece, # if dest square is not on first or last rank, then None, If single_char is not P or p, then None.  Otherwise, can't be guessed at all, must be specified
    # self.is_en_passant_capture,  # can be filled in if ep capture indicator is given, otherwise assume false
    # self.new_en_passant_square)  # can be filled in if source and dest square given and  


    @classmethod
    def is_on_move_list(cls, move, move_list):
        # Returns true if given move is on given move list
        for list_move in move_list:
            if list_move == move:
                return True
        return False

    def __eq__(self, move_to_match):
        # Returns true if self and move_to_match represent the same move in all respects
        if (self.single_char == move_to_match.single_char and
            self.starting_square == move_to_match.starting_square and
            self.destination_square == move_to_match.destination_square and
            self.captured_piece == move_to_match.captured_piece and
            self.promotion_piece == move_to_match.promotion_piece and
            self.is_en_passant_capture == move_to_match.is_en_passant_capture and
            self.new_en_passant_square == self.new_en_passant_square):
            return True
        else:
            return False

        

class Player:
    ''' Parent class for players
    '''
    def __init__(self, color=None):
        self.set_color(color)
    
    def set_color(self, color):
        if color is None:
            self.color = None
        elif color[0].lower()=='w':
            self.color = 'w'
        elif color[0].lower()=='b':
            self.color = 'b'
        else:
            raise Exception('Invalid color')

    def choose_move(self, game, legal_moves_list):
        '''Placeholder which subclasses should implement, needs to return a Move object'''
        pass

    def is_valid_move(self, move, legal_move_list):
        # Checks if move matches one on legal move list
        pass # Maybe should be a Move function??? Maybe want Game object too?

class RLMPlayer (Player):
    ''' Class to encapsulate RLM player behaviors
    '''
    def choose_move(self, game, legal_moves_list):
        # RLM player generates the list of possible legal moves, and chooses a random one off the list
        return random.choice(legal_moves_list)

class HumanPlayer (Player):
    ''' Class to handle interaction with human player during a game (mostly requesting a move)
    '''
    def choose_move(self, game, legal_moves_list):
        '''Prompt the human player to enter a move'''
        valid_move_entered = False
        while not valid_move_entered:
            entered_move = input("What is your move?\nEnter move: ") # TODO make this better
            # Convert entered move to Move object
            partial_move_dict = Move.parse_move_without_game(entered_move, white_is_moving=(game.side_to_move=='w'))
            matching_moves = Move.find_matches_to_partial_move(partial_move_dict, legal_moves_list)
            if len(matching_moves)==1:
                move = matching_moves[0]
                valid_move_entered = True
                msg = 'Your move is %s, got it!'%(move.to_long_algebraic())
            elif len(matching_moves)==0:
                msg = 'Your entered move did not match any legal moves... try again!\n'
                # TODO this can be much improved!!  We could identify the move with the closest match, ask them if they 
                # meant that, we can explain what move elements could not be matched, etc. 
            else:
                # More than 1 legal move matched all the information they supplied, let's offer them a choice...
                move_str_list = [m.to_long_algebraic() for m in matching_moves]
                msg = 'Your entered move was consistent with %i legal moves, one of the following would be less ambiguous:\n'
                for m in move_str_list:
                    msg += m + '\n'
                msg += 'Try again!\n'
            print(msg)
        return move
    

class NRLMPlayer (Player):
    '''Non-Random Legal Move Player.  Chooses moves in a non-random way (currently just the first move on the legal move list)
    '''
    def choose_move(self, game, legal_moves_list):
        return legal_moves_list[0]


class GameController:
    '''
    Class to manage game flow. Should handle gathering player info, setting up game,
    prompting players for moves, calling comment generation routines, orchestrating
    post-game processes (e.g. saving to PGN).  Game state should be held in a Game 
    object, board state in a Board object.  
    '''
    '''
    Move generation is complete, what would we need to add to have a playable game?
    * Interface with human player (prompts, move validation)
    * Record game history
    * Recognize checkmate and stalemate and handle game end
    '''

    def start_new_game(self):
        '''Start a new game'''
        # Ask about playing game
        start_game_answer = input('Hey there, do you want to play a game of chess?\n(Y/n): ')
        if len(start_game_answer)>0 and start_game_answer[0].lower()=='n':
            print("Fine!! I'll play myself then!! You can watch.")
            white_player = RLMPlayer()
            black_player = RLMPlayer()
        else: 
            # Choose colors
            side_answer = input('Would you like to play as white or black?\n(W/b): ')
            if len(side_answer)>0 and side_answer[0].lower()=='b':
                print("OK, I'll play as white!")
                white_player = RLMPlayer()
                black_player = HumanPlayer()
            else:
                print("OK, I'll play as black!")
                black_player = RLMPlayer()
                white_player = HumanPlayer()
        # Initialize game and force normal starting position for now...
        game = Game()
        game.set_board(Board()) # defaults to normal starting position
        game.set_players(white_player, black_player)

        print("Here is the starting position:")
        game.show_board()

        # The game loop
        game_is_over = False
        legal_moves = game.get_moves_for()
        while not game_is_over:
            if game.side_to_move[0] == 'w':
                move = white_player.choose_move(game, legal_moves)
            else:
                move = black_player.choose_move(game, legal_moves)
            # Carry out chosen move and update game
            game.make_move(move)
            #TODO: record move history here
            game.show_board()
            # To see if game is over, check if there are legal moves (if there aren't any, it's either stalemate or checkmate)
            legal_moves = game.get_moves_for()
            if len(legal_moves)==0:
                game_is_over = True # checkmate or stalemate
                # Need to find if the side to move's king is currently in check
                if game.side_to_move=='w':
                    K = [p for p in game.white_pieces if isinstance(p, King)][0]
                    game_over_msg = 'CHECKMATE!! Black wins!' if K.is_in_check() else "STALEMATE!!  It's a draw!"
                else:
                    k = [p for p in game.black_pieces if isinstance(p, King)][0]
                    game_over_msg = 'CHECKMATE!! White wins!' if k.is_in_check() else "STALEMATE!!  It's a draw!"
            elif game.half_moves_since >= 100: # TODO: check if this should be > or >=
                game_is_over = True
                game_over_msg = "DRAW!! That's 50 moves with no captures or pawn moves!"

        # The game has ended...
        print(game_over_msg)
        print("Thanks for playing!")





class Game:
    '''Class to hold a game state.  Game state includes everything in an FEN, plus
    a unique GameID.  Probably makes sense for it to keep track of everything that
    would go into a PGN too (player names, game history, location, event, site)
    '''
    def __init__(self, ep_square = None):
        self.ep_square = ep_square
        self.castling_state = ['K','Q','k','q'] # TODO: currently just a placeholder which allows all castling options
        self.side_to_move = 'w' # 'w' or 'b' for White or Black
        self.move_counter = 1 # move counter to increment after each Black move
        self.half_moves_since = 0 # counter for half moves since last pawn move or capture
        self.white_pieces = []
        self.black_pieces = []
        self.board = None # This needs to be initialized before we can really play a game, but let's start with a placeholder which indicates it's not initialized
        self.white_player = None
        self.black_player = None


    def copy(self):
        game_copy = Game()
        game_copy.ep_square = self.ep_square
        game_copy.castling_state = self.castling_state
        game_copy.side_to_move = self.side_to_move
        game_copy.white_pieces = self.white_pieces
        game_copy.black_pieces = self.black_pieces
        game_copy.board = self.board.copy() # make a copy of the board, don't reference same board
        # NOTE: Any need to copy Players? (not yet, but consider)
        return game_copy


    def set_board(self, board):
        self.board = board
        self.initialize_pieces_from_board(board)

    def set_players(self, white_player, black_player):
        self.white_player = white_player
        self.black_player = black_player

    def show_board(self):
        '''Print board string (could also be configured to call a graphical displayer once we've worked that out)'''
        print(self.board)

    def make_move(self, move):
        '''Update board, pieces, and game state based on move.  
        NOTE that this updates the game's Board object and replaces the Piece objects
        This may need to be changed in the future if piece objects got more complex and
        were storing something like a move history, or anything like that. '''

        # Need to update both the moving Piece object, and the Board object
        board = self.board
        start_sq = move.starting_square
        dest_sq = move.destination_square
        # Update Board with move
        board.move(start_sq, dest_sq) # this always happens
        # Handle special cases of moves, where more happens than just moving from start to dest
        if move.is_castling:
            # Also need to move rook
            if board.is_same_square(dest_sq,'g1'): # white kingside castling
                board.move('h1','f1')
            elif board.is_same_square(dest_sq, 'c1'): # white queenside castling
                board.move('a1','d1')
            elif board.is_same_square(dest_sq, 'g8'): # black kingside castling
                board.move('h8','f8')
            elif board.is_same_square(dest_sq, 'c8'): # black queenside castling
                board.move('a8','d8')
            else:
                raise Exception("Move said it was castling move, but didn't move to g or c file, instead moved to '%s'" % board.square_to_alg_name(dest_sq) )
            # Also need to update castling options (no longer allowed, can't castle twice)
            if move.single_char=='K': # white
                self.set_castling_state('K', False)
                self.set_castling_state('Q', False)
            else:
                self.set_castling_state('k', False)
                self.set_castling_state('q', False)
        elif move.is_en_passant_capture:
            # Also need to remove captured pawn from board
            board[move.destination_square[0], move.starting_square[1]] = Board.EMPTY_SQUARE
        # Moving the king invalidates castling on both sides
        elif move.single_char=='K':
            self.set_castling_state('K', False)
            self.set_castling_state('Q', False)
        elif move.single_char=='k':
            self.set_castling_state('k', False)
            self.set_castling_state('q', False)
        # Moving a rook off it's starting square disables castling on that side
        elif move.single_char=='R':
            if board.is_same_square(move.starting_square, 'h1'):
                self.set_castling_state('K', False)
            elif board.is_same_square(move.starting_square, 'a1'):
                self.set_castling_state('Q', False)
        elif move.single_char=='r':
            if board.is_same_square(move.starting_square, 'h8'):
                self.set_castling_state('k', False)
            elif board.is_same_square(move.starting_square, 'a8'):
                self.set_castling_state('q', False)

        # Update the game list of pieces from the updated board (existing pieces are discarded)
        self.initialize_pieces_from_board(board) # this makes the board the master representation

        # There are several housekeeping things we only really need to do if this is a real move (rather than imagined)
        # This is indicated by the change_side_to_move flag: if true, this is a real move, if not, it's imagined
        #if change_side_to_move:
        self.move_counter = self.move_counter+1 if self.side_to_move == 'b' else self.move_counter # increment if black just moved
        if move.captured_piece is not None or move.single_char.upper()=='P':
            # reset if capture or pawn move
            self.half_moves_since = 0
        else:
            self.half_moves_since += 1
        # Change side to move
        self.side_to_move = 'b' if self.side_to_move=='w' else 'w' # toggle side to move between w and b
        # Update game ep square
        self.ep_square = move.new_en_passant_square

  
    def set_white_to_move(self):
        self.side_to_move = 'w'

    def set_black_to_move(self):
        self.side_to_move = 'b'

    def initialize_pieces_from_board(self, board):
        '''Generate Piece objects from the given Board object and assign to white and black piece lists'''
        white_pieces = []
        black_pieces = []
        for rank_idx in range(8):
            for file_idx in range(8):
                sq = (file_idx, rank_idx)
                piece_char = board[sq]
                piece = Piece.piece_from_char_and_square(piece_char, sq, self)
                if piece is not None:
                    if piece.is_white():
                        white_pieces.append(piece)
                    else:
                        black_pieces.append(piece)
        self.white_pieces = white_pieces
        self.black_pieces = black_pieces

    def set_castling_state(self, castling_char, bool):
        '''Set a particular kind of castling (indicated by castling char) to enabled or disabled (indicated by bool)'''
        castling_state = self.castling_state
        if bool:
            # enable
            if castling_char not in castling_state:
                castling_state += castling_char # add to enable
        else:
            # disable
            castling_state = [s for s in castling_state if not s==castling_char]
        # Reorder 
        self.castling_state = [s for s in 'KQkq' if s in castling_state]    

    def get_castling_state(self, is_white):
        '''Returns a tuple of two booleans indicating whether the game state permits
        castling kingside and queenside. If is_white is true, then the reported 
        permissions are for white, otherwise they are for black'''
        if is_white:
            kingside_allowed = True if 'K' in self.castling_state else False
            queenside_allowed = True if 'Q' in self.castling_state else False
        else:
            kingside_allowed = True if 'k' in self.castling_state else False
            queenside_allowed = True if 'q' in self.castling_state else False
        return kingside_allowed, queenside_allowed

    def get_moves_for(self, other_side=False, allow_own_king_checked=False):
        '''This function should get all possible moves in the current game
        state.  If other_side is False (default) then moves are generated for 
        the color which is next to move. If other_side is True, then moves are
        generated for the color which is not next to move. If allow_own_king_checked
        is False (default), then moves which would lead to the moving side's king
        being in check are pruned as illegal.  If allow_own_king_checked is True,
        then the full move list is returned without being pruned in this way.  This
        option is necessary because the procedure for figuring out if one side is 
        in check relies on generating moves for the other side ignoring whether such
        moves would leave themselves in check.  For example, a pinned bishop can 
        still give check, but a pinned bishop's moves will all be pruned if we 
        cut out those leading to check. 
        
        Note that move lists generated with allow_own_king_checked will omit 
        castling moves even if they are legal.  This is done for two reasons. First,
        they can't be capture moves, so they aren't relevant for determining whether
        the other side is currently in check. Second, they're costly to calculate and 
        involve checking for check, so they would needlessly complicate things. Since
        they're complicated and unnecessary, they are left out. 
        '''
        moves = []
        # Loop over the pieces which are of the color to move, generating moves for each one
        if (self.side_to_move =='w' and not other_side) or (self.side_to_move=='b' and other_side):
            pieces_to_move = self.white_pieces
        else:
            pieces_to_move = self.black_pieces
        
        for p in pieces_to_move:
            moves.extend(p.get_moves(allow_own_king_checked=allow_own_king_checked))
        return moves

class Piece:
    '''Superclass of all chess pieces. All pieces have a name, a one-character
    abbreviation, a color, a current square they are on, and a board they are on
    '''
    def __init__(self, name, char, color, current_square, game): 
        self.name = name
        self.char = char
        self.color = color
        self.current_square = current_square
        self.game = game
    
    def get_moves(self, allow_own_king_checked=False):
        # Method to return list of legal moves. Subclasses must provide implementation.
        # Should return a list of moves.  If allow_own_king_checked is False, these
        # moves are pruned to remove moves that would leave the board in a state where the 
        # same-color king is checked by the enemy. The allow_own_king_checked flag will be 
        # set to True when implementing the is_in_check function, because in that case we
        # need to account for possible moves even if they would leave their king in check.
        # For example, one King cannot move into check by an enemy Bishop, even if that
        # enemy Bishop is pinned to their own King.
        pass

    def is_white(self, color=None):
        if color is None:
            color = self.color  
        if color[0].lower() == 'w':
            return True
        else:
            return False

    def is_black(self):
        return not self.is_white()

    def is_enemy(self, other):
        # Return true if other represents the opposite color piece as self. "other" should be a 
        # one-character string representing the name of a piece. If a string like '-' is passed in
        # which is unchanged by uppercasing or lowercasing, is_enemy returns False
        if other is None:
            # other is probably the contents of a square off the board, (e.g. board[-1,-1] is None)
            return False 
        other_is_white = other==other.upper() and other != other.lower()
        other_is_black = other==other.lower() and other != other.upper()
        return (self.is_white() and other_is_black) or (self.is_black() and other_is_white)

    def is_friend(self, other):
        # Return true if other represents the same color piece as self. "other" should be a 
        # one-character string representing the name of a piece. If a string like '-' is passed in
        # which is unchanged by uppercasing or lowercasing, is_friend returns False. If other is None,
        # returns False.
        if other is None: 
            return False 
        other_is_white = other==other.upper() and other != other.lower()
        other_is_black = other==other.lower() and other != other.upper()
        return (self.is_white() and other_is_white) or (self.is_black() and other_is_black)

    @classmethod
    def piece_from_char_and_square(cls, piece_char, square, game):
        '''Create a Piece object of the appropriate subclass given a single character
        representation and a current square'''
        # color square game
        assert piece_char in 'KQRBNPkqrbnp'+Board.EMPTY_SQUARE, 'Piece character must be one of "KQRBNPkqrbnp" (or empty square character)!'
        if piece_char==Board.EMPTY_SQUARE:
            return None #don't generate a Piece object
        if piece_char.upper()==piece_char:
            color = 'w'
        else:
            color = 'b'
        upper_piece_char = piece_char.upper()
        if upper_piece_char=='K':
            piece = King(color, square, game)
        elif upper_piece_char=='Q':
            piece =  Queen(color, square, game)
        elif upper_piece_char=='R':
            piece = Rook(color, square, game)
        elif upper_piece_char=='B':
            piece = Bishop(color, square, game)
        elif upper_piece_char=='N':
            piece = Knight(color, square, game)
        elif upper_piece_char=='P':
            piece = Pawn(color, square, game)
        return piece
        

        

class KQRBN_Piece (Piece):
    '''Superclass of all non-pawn pieces. These pieces can be characterized by 
    a move pattern plus a flag indicating whether they can repeat a move. Class 
    provides implementations of get_single_move() and get_ray_moves()'''
    def __init__(self, single_moves, ray_move_flag):
        self.single_moves = single_moves
        self.ray_move_flag = ray_move_flag

    def get_single_move(self, dx, dy):
        '''Given an offset from the current piece position, this function will return None if the
        move represented by that offset would take the piece off the board or onto a friendly piece.
        If the offset would take the piece onto an empty square or an enemy piece, a long form 
        algebraic string of the move will be returned (including piece name, source square, optional
        capture 'x', and destination square). 
        Returned move format is changing to 
        move = (piece character, (startingFileIdx, startingRankIdx), 
                (destFileIdx, destRankIdx), 
                capturedPiece or None, castlingBoolean, promotionPiece or None,
               )
        '''
        board = self.game.board
        current_file_idx, current_rank_idx = board.square_name_to_array_idxs(self.current_square) # TODO consider whether this should be stored or input rather than looked up repeatedly
        new_file_idx = current_file_idx + dx
        new_rank_idx = current_rank_idx + dy
        destination_occupant = board[new_file_idx, new_rank_idx]
        if destination_occupant is None or self.is_friend(destination_occupant):
            # Destination is off the board or is a friendly piece, move is invalid
            return None
        elif destination_occupant == Board.EMPTY_SQUARE:
            # Destination is currently empty, move is provisionally valid
            captured_piece = None
            candidate_move = Move(self.char, self.current_square, (new_file_idx, new_rank_idx)) # no other special features (no castling, promotion, captured piece, ep capture, or new ep square)
            return candidate_move
        elif self.is_enemy(destination_occupant):
            # Destination is occupied by an enemy piece, capture is provisionally valid
            captured_piece = destination_occupant
            candidate_move = Move(self.char, self.current_square, (new_file_idx, new_rank_idx), captured_piece=captured_piece) # no other special features (no castling, promotion, ep capture, or new ep square)
            return candidate_move
        else:
            raise Exception('Destination occupant appears to be none of the expected outcomes: enemy, friend, empty, or off board!')
        
    def get_ray_moves(self, dx, dy):
        ''' Return list of potentially valid moves obtainable by repeating the single move represented by dx dy over and over
        until hitting a friendly piece, an enemy piece, or falling off the board edge'''
        candidate_moves = []
        iteration_counter = 1
        max_ray_length = 10
        for iteration_counter in range(1, max_ray_length+1):
            candidate_move = self.get_single_move(iteration_counter*dx, iteration_counter*dy)
            if candidate_move is None:
                # offset takes you into a friendly piece or off the board, no more valid moves are possible
                return candidate_moves
            elif candidate_move.is_capture():
                # possible move is a capture; this one should be included, but we shouldn't look for any further than this
                candidate_moves.append(candidate_move)
                return candidate_moves
            else:
                # candidate move is onto empty square, OK to keep looking further along the ray
                candidate_moves.append(candidate_move)
        raise Exception("The ray should have terminated by now... but it hasn't")

        
    def get_moves(self, allow_own_king_checked=False):
        '''This function is responsible for generating all possibly legal moves of the piece, 
        optionally filtered to remove moves that result in board positions which leave or put
        their own king in check. 
        "Possibly legal" because some moves will depend on the game state and not just on board
        state. '''
        provisional_moves = []
        board = self.game.board
        
        if not self.ray_move_flag:
            # No ray moves, only single moves
            for dx,dy  in self.single_moves:
                candidate_move = self.get_single_move(dx, dy)
                if candidate_move is not None:
                    provisional_moves.append(candidate_move)                     
        else:
            # Ray moves are allowed
            for dx,dy in self.single_moves:
                candidate_moves = self.get_ray_moves(dx, dy)
                provisional_moves.extend(candidate_moves)

        if not allow_own_king_checked:
            # Filter out moves which put or leave our King in check
            king_square = board.find_king_square(self.color)
            our_king = King(self.color, king_square, self.game)
            moves = [move for move in provisional_moves if not our_king.is_in_check_after_move(move)]
        else:
            moves = provisional_moves

        # How to handle special rules about King moves?  Could the King call this get_moves, then implement it's 
        # own additional code to handle castling-related move generation and move pruning?

        # Return the final list of moves
        return moves


class King (KQRBN_Piece):
    def __init__(self, color, square, game=None):
        char = 'K' if self.is_white(color) else 'k'
        Piece.__init__(self, name='King', char=char, color=color, current_square=square, game=game)
        single_moves = [ [dx,dy] for dx in [-1,0,1]  for dy in [-1,0,1] ]
        single_moves.remove([0,0])
        ray_move_flag = False
        KQRBN_Piece.__init__(self, single_moves, ray_move_flag)

    def get_moves(self, allow_own_king_checked=False):
        # The king also needs it's own implementation of get_moves, because castling cannot be handled by single or ray moves
        # Start by gathering normal moves using superclass
        provisional_moves = KQRBN_Piece.get_moves(self, allow_own_king_checked=allow_own_king_checked)
        # Consider adding castling related moves
        # In order for castling to be legal:
        # * The game castling state has to allow it (i.e. contain "K" to permit white king-sided castling)
        # * The King and Rook must be on starting squares with only empty squares between
        # * The King must not be in check after castling is complete
        # * The square the King moves through must not be attacked
        # * The King must not be in check now

        # Skip consideration of castling if doing the abbreviated move generation (i.e. if allow_own_king_checked is True)
        if not allow_own_king_checked:
            kingside_allowed_by_state, queenside_allowed_by_state = self.game.get_castling_state(self.color) 
            kingside_allowed_by_position, queenside_allowed_by_position = self.get_castling_allowed_by_position() 
            kingside_allowed_by_check, queenside_allowed_by_check = self.get_castling_allowed_by_check() # TODO: write this function

            kingside_allowed = kingside_allowed_by_state and kingside_allowed_by_position and kingside_allowed_by_check
            queenside_allowed = queenside_allowed_by_state and queenside_allowed_by_position and queenside_allowed_by_check
            if kingside_allowed:
                provisional_moves.append(self.get_kingside_castle_move())
            if queenside_allowed:
                provisional_moves.append(self.get_queenside_castle_move())
        return provisional_moves


    def get_kingside_castle_move(self):
        # needs to be updated if move format changes!
        board = self.game.board
        if self.is_white():
            dest = board.square_name_to_array_idxs('g1')
        else:
            dest = board.square_name_to_array_idxs('g8')
        return Move(self.char, self.current_square, dest, is_castling=True) # no other special features (no promotion, captured piece, ep capture, or new ep square)

    def get_queenside_castle_move(self):
        # needs to be updated if move format changes!
        board = self.game.board
        if self.is_white():
            dest = board.square_name_to_array_idxs('c1')
        else:
            dest = board.square_name_to_array_idxs('c8')
        return Move(self.char, self.current_square, dest, is_castling=True)

    
    def get_castling_allowed_by_position(self):
        # Castling is allowed by the position if the king and rook are on starting squares and 
        # intervening squares are empty
        board = self.game.board
        if self.is_white():
            if board['e1']=='K':
                # Kingside
                if board['f1']==Board.EMPTY_SQUARE and board['g1']==Board.EMPTY_SQUARE and board['h1']=='R':
                    kingside_allowed = True
                else:
                    kingside_allowed = False
                if board['d1']==Board.EMPTY_SQUARE and board['c1']==Board.EMPTY_SQUARE and board['b1']==Board.EMPTY_SQUARE and board['a1']=='R':
                    queenside_allowed = True
                else:
                    queenside_allowed = False
        else: # black
            if board['e8']=='k':
                # Kingside
                if board['f8']==Board.EMPTY_SQUARE and board['g8']==Board.EMPTY_SQUARE and board['h8']=='r':
                    kingside_allowed = True
                else:
                    kingside_allowed = False
                if board['d8']==Board.EMPTY_SQUARE and board['c8']==Board.EMPTY_SQUARE and board['b8']==Board.EMPTY_SQUARE and board['a8']=='r':
                    queenside_allowed = True
                else:
                    queenside_allowed = False
        return kingside_allowed, queenside_allowed
       
    def get_castling_allowed_by_check(self):
        # This function must return two boolean values indicating whether the king would be in check 
        # after castling or would be moving through check while castling, or is currently in check.
        board = self.game.board

        current_file_idx, current_rank_idx = board.square_name_to_array_idxs(self.current_square)

        other_side_moves = self.game.get_moves_for(other_side=True, allow_own_king_checked=True)
        other_side_dest_squares = [move.destination_square for move in other_side_moves] 
        
        if (current_file_idx, current_rank_idx) in other_side_dest_squares:
            # Currently in check, castling is not allowed to either side
            kingside_allowed, queenside_allowed = False, False
        else:
            # Consider Kingside
            if ((current_file_idx+1, current_rank_idx) in other_side_dest_squares) or ((current_file_idx+2, current_rank_idx) in other_side_dest_squares):
                kingside_allowed = False # either moving into check or through check
            else:
                kingside_allowed = True # not in check, moving through check, or ending in check
            # Consider Queenside
            if ((current_file_idx-1, current_rank_idx) in other_side_dest_squares) or ((current_file_idx-2, current_rank_idx) in other_side_dest_squares):
                queenside_allowed = False # either moving into check or through check
            else:
                queenside_allowed = True # not in check, moving through check, or ending in check
        return kingside_allowed, queenside_allowed


    def is_in_check_after_move(self, move):
        '''Imagines making the given move, then evaluates whether in check in the
        resulting board position. Should be careful to not to alter the game board position
        permanently, this is an imagined move, not yet an actual move.'''
        temp_game = self.game.copy() # make a copy of the game to imagine move
        temp_game.make_move(move) # make the move in the game copy
        other_side_moves = temp_game.get_moves_for(allow_own_king_checked=True)
        other_side_dest_squares = [move.destination_square for move in other_side_moves]
        for other_side_dest in other_side_dest_squares:
            if temp_game.board[other_side_dest]==self.char:
                # The other side has a piece which can move to a board location which is 
                # occupied by the same character as self.char.  Therefore, the King would be 
                # in check after the proposed move. 
                return True
        # If no other side piece could potentially move to the king's square, then he must not be in check
        return False
        

    def is_in_check(self):
        '''Should return a true if this king is in check, false otherwise.
        In order to do this, we need to know if any of the other side's pieces
        could capture this king in one move, regardless of whether that move would 
        expose their own king to check.  One way to do this would be to generate 
        all possible moves for the other side, unfiltered by check status.  Another
        way would be to start from this king, and look out to see whether any pieces
        are in a position to attack it. Both approaches are kind of messy.  In general, 
        we do need to filter out moves which would expose our own king to check, '''
        other_side_moves = self.game.get_moves_for(other_side=True, allow_own_king_checked=True)
        other_side_dest_squares = [move.destination_square for move in other_side_moves]
        current_file_idx, current_rank_idx = self.game.board.square_name_to_array_idxs(self.current_square)
        if (current_file_idx, current_rank_idx) in other_side_dest_squares:
            in_check = True
        else: 
            in_check = False
        return in_check


class Queen (KQRBN_Piece):
    def __init__(self, color, square, game=None):
        char = 'Q' if self.is_white(color) else 'q'
        Piece.__init__(self, name='Queen', char=char, color=color, current_square=square, game=game)
        single_moves = [ [dx,dy] for dx in [-1,0,1]  for dy in [-1,0,1] ]
        single_moves.remove([0,0])
        ray_move_flag = True
        KQRBN_Piece.__init__(self, single_moves, ray_move_flag)

class Rook (KQRBN_Piece):
    def __init__(self, color, square, game=None):
        char = 'R' if self.is_white(color) else 'r'
        Piece.__init__(self, name='Rook', char=char, color=color, current_square=square, game=game)
        single_moves = [ [ 1,  0],
                         [-1,  0],
                         [ 0,  1],
                         [ 0, -1] ]
        ray_move_flag = True
        KQRBN_Piece.__init__(self, single_moves, ray_move_flag)
class Bishop (KQRBN_Piece):
    def __init__(self, color, square, game=None):
        char = 'B' if self.is_white(color) else 'b'
        Piece.__init__(self, name='Bishop', char=char, color=color, current_square=square, game=game)
        single_moves = [ [dx, dy] for dx in [-1,1] for dy in [-1,1] ]
        ray_move_flag = True
        KQRBN_Piece.__init__(self, single_moves, ray_move_flag)
class Knight (KQRBN_Piece):
    def __init__(self, color, square, game=None):
        char = 'N' if self.is_white(color) else 'n'
        Piece.__init__(self, name='Knight', char=char, color=color, current_square=square, game=game)
        single_moves = [[-1,  2], 
                        [ 1,  2],
                        [ 2,  1], 
                        [ 2, -1], 
                        [ 1, -2], 
                        [-1, -2], 
                        [-2, -1], 
                        [-2, 1]]
        ray_move_flag = False
        KQRBN_Piece.__init__(self, single_moves, ray_move_flag)
class Pawn (Piece):
    '''Class encapulating pawn behaviors'''
    def __init__(self, color, square, game=None):
        char = 'P' if self.is_white(color) else 'p'
        Piece.__init__(self, name='Pawn', char=char, color=color, current_square=square, game=game)
    
    def get_moves(self, allow_own_king_checked=False):
        '''This needs to generate all possible moves for this pawn.
        Ignoring check, possible moves are:
        * One square forward if that square is empty
        * Two squares forward if on initial square and both squares are empty
        * One square diagonal forward if that square has an enemy piece OR if it is an ep square
        '''
        move_candidates = [] # to hold moves
        board = self.game.board
        
        if self.is_white():
            home_rank_idx = 1
            move_dir = 1
        else: 
            home_rank_idx = 6
            move_dir = -1
        
        current_file_idx, current_rank_idx = board.square_name_to_array_idxs(self.current_square)
        forward_sq = (current_file_idx, current_rank_idx + move_dir)
        forward_two_sq = (current_file_idx, current_rank_idx + 2*move_dir)
        diag_east_sq = (current_file_idx + 1, current_rank_idx + move_dir)
        diag_west_sq = (current_file_idx - 1, current_rank_idx + move_dir)
        if current_rank_idx == home_rank_idx:
            # On home rank, may be possible to move two squares
            if board[forward_sq]==Board.EMPTY_SQUARE and board[forward_two_sq]==Board.EMPTY_SQUARE:
                # OK to move 2 squares (this move would generate an ep square)
                move_candidate = Move(self.char, self.current_square, forward_two_sq, new_en_passant_square=forward_sq) 
                move_candidates.append(move_candidate)
        if self.is_white() and (current_rank_idx + move_dir == 7):
            would_be_promoting = True
            promotion_piece_list = ['Q','R','B','N']
        elif self.is_black() and (current_rank_idx + move_dir == 0):
            would_be_promoting = True
            promotion_piece_list = ['q','r','b','n']
        else:
            would_be_promoting = False
        if board[forward_sq] == Board.EMPTY_SQUARE:
            if would_be_promoting:
                # Promoting!
                for pp in promotion_piece_list:
                    move_candidate = Move(self.char, self.current_square, forward_sq, promotion_piece=pp)
                    move_candidates.append( move_candidate )
            else: 
                # Moving forward one square
                move_candidates.append( Move(self.char, self.current_square, forward_sq) )

        if self.game.ep_square is not None:
            ep_square = board.square_name_to_array_idxs(self.game.ep_square) #standardize
        else:
            ep_square = None
        # Check diagonal moves for captures
        for dest in [diag_east_sq, diag_west_sq]:
            if self.is_enemy(board[dest]):
                captured_piece = board[dest]
                if would_be_promoting:
                    # Promoting!
                    for pp in promotion_piece_list:
                        move_candidates.append( Move( self.char, self.current_square, dest, captured_piece=captured_piece, promotion_piece=pp ) )
                else: 
                    # Capturing
                    move_candidates.append( Move( self.char, self.current_square, dest, captured_piece=captured_piece) )
            elif ep_square is not None and dest==ep_square:
                # En passant capture!
                captured_piece = board[dest[0], current_rank_idx] # current rank and destination file should have the pawn to capture
                assert captured_piece.lower()=='p', 'En passant capture should only possibly capture pawns, but captured piece is "%s"' % (captured_piece)
                move_candidates.append( Move( self.char, self.current_square, dest, captured_piece=captured_piece, is_en_passant_capture=True) )
                # TODO: make sure that board.move() and game.make_move() handle ep capture correctly.  It's the only case where the captured piece isn't on the destination square

        if not allow_own_king_checked:
            # Filter out moves which put or leave our King in check
            king_square = board.find_king_square(self.color)
            our_king = King(self.color, king_square, self.game)
            moves = [move for move in move_candidates if not our_king.is_in_check_after_move(move)]
        else:
            moves = move_candidates
        
        return moves


        



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


class TestRLM:
    '''This class should contain unit tests for all RLM components'''
    def __init__(self):
        # Do we need to do anything on start-up?
        pass # I don't think so

    def run_all_tests(self):
        # Run all unit tests.  Whenever you create a new test, add a call to it here
        try:
            self.test_board_generation_from_piece_list_1()
            print('Test: test_board_generation_from_piece_list_1 PASSED')
        except Exception as e:
            print('Test: test_board_generation_from_piece_list_1 FAILED with error message: "%s"' % (str(e)))
        try: 
            self.test_move_generation_1()
            print('Test: test_move_generation_1 PASSED')
        except Exception as e:
            print('Test: test_move_generation_1 FAILED with error message "%s"' % (str(e)))

        try:
            self.test_move_generation_2()
            print('Test: test_move_generation_2 PASSED')
        except Exception as e:
            print('Test: test_move_generation_2 FAILED with error message "%s"' % (str(e)))
        
        try:
            self.test_pawn_moves_1()
            print('Test: test_pawn_moves_1 PASSED')
        except Exception as e:
            print('Test: test_pawn_moves_1 FAILED with error message "%s"' % (str(e)))
        

    def test_board_generation_from_piece_list_1(self):
        # Very simple test of board generation from list of pieces, just two kings
        K = King('w', 'e1') # white King on e1
        k = King('b', 'e8') # black King on e8
        b = Board(piece_list=[K,k]) # generate board
        assert b['e1']=='K', "There should be a white king on e1, but there isn't"
        assert b['e8']=='k', "There should be a black king on e8, but there isn't"
        assert list(b.board_array.ravel()).count(Board.EMPTY_SQUARE)==62, "There should be 62 empty squares, but there are %i"%(list(b.board_array.ravel()).count(Board.EMPTY_SQUARE))
        return True

    def test_move_generation_1(self):
        # Very simple test of basic move generation
        K = King('w', 'e1') # white King on e1
        k = King('b', 'e8') # black King on e8
        b = Board(piece_list=[K,k]) # generate board
        g = Game()
        g.set_board(b)
        g.set_white_to_move()
        # Test white
        white_moves = g.get_moves_for()
        white_move_strs = [move.to_long_algebraic() for move in white_moves]
        assert len(white_moves)==5, "There should be 5 possible white moves from this position, but there are %i"%(len(white_moves))
        expected_moves = ['Ke1e2', 'Ke1d1', 'Ke1d2', 'Ke1f2', 'Ke1f1']
        for move in white_move_strs:
            assert move in expected_moves, "Move '%s' was produced but not expected!"%(move)
        # Test black
        g.set_black_to_move()
        black_moves = g.get_moves_for()
        black_move_strs = [move.to_long_algebraic() for move in black_moves]
        expected_moves = ['Ke8e7', 'Ke8d8', 'Ke8d7', 'Ke8f7', 'Ke8f8']
        for move in black_move_strs:
            assert move in expected_moves, "Move '%s' was produced but not expected!"%(move)
        return True

    def test_move_generation_2(self):
        '''More complex test of move generation.  Still exclude pawns, but include all other piece types.
        Should include castling, blocking of castling through check, an absolute pin, blocking of 
        moving into check, anything else?
        position is: 
          +-------------------------------+
        8 | r | - | - | - | k | - | - | r |
          |---|---|---|---|---|---|---|---|
        7 | - | b | - | - | - | - | - | - |
          |---|---|---|---|---|---|---|---|
        6 | - | - | - | - | - | - | n | - |
          |---|---|---|---|---|---|---|---|
        5 | - | - | - | - | - | Q | - | B |
          |---|---|---|---|---|---|---|---|
        4 | - | - | - | - | - | - | - | - |
          |---|---|---|---|---|---|---|---|
        3 | - | - | - | - | - | N | - | - |
          |---|---|---|---|---|---|---|---|
        2 | - | - | - | - | - | - | - | - |
          |---|---|---|---|---|---|---|---|
        1 | R | - | - | - | K | - | - | R |
          +-------------------------------+
            a   b   c   d   e   f   g   h

        '''
        piece_list = [King('w','e1'), Rook('w','h1'), Rook('w','a1'),
                        Knight('w','f3'), Bishop('w','h5'), Queen('w','f5'),
                        King('b','e8'), Rook('b','h8'), Rook('b','a8'),
                        Knight('b','g6'), Bishop('b','b7')]
        b = Board(piece_list=piece_list)
        g = Game()
        g.set_board(b)
        g.set_white_to_move()
        white_moves = g.get_moves_for()
        white_move_strs = [move.to_long_algebraic() for move in white_moves]
        # White has lots of moves, including castling to either side
        assert 'O-O' in white_move_strs, "Castling kingside ('O-O') should be among allowed moves for White, but didn't make it into the list of moves!"
        assert 'O-O-O' in white_move_strs, "Castling queenside ('O-O-O') should be among allowed moves for White, but didn't make it into the list of moves!"
        # BLACK
        g.set_black_to_move()
        black_moves = g.get_moves_for()
        black_move_strs = [move.to_long_algebraic() for move in black_moves]
        # Black also has lots of moves, but castling should be blocked: queenside because moving into check, kingside because caslting through check
        assert 'O-O' not in black_move_strs, "Castling kingside should not be among allowed moves for Black, because the white Q is attacking the square the king would move through, but it is on the list of moves anyway!"
        assert 'O-O-O' not in black_move_strs, "Castling queenside should not be among allowed moves for Black, because the white Q is attacking the square the king would move into, but it is on the list of moves anyway!"
        into_check_moves = ['Ke8d7', 'Ke8f8', 'Ke8f7']
        for move_str in black_move_strs:
            assert move_str not in into_check_moves, "Tried to move into check with %s!" % (move_str)
            assert "N" not in [m[0] for m in black_move_strs], "Tried to move pinned knight with %s" % (move_str)
        # Can add many more checks here, but this is probably good to start
        return True

    def test_pawn_moves_1(self):
        '''Test all the kinds of pawn moves on a simplified board, including:
        * 2 square move
        * 1 square move
        * capture to either side diagonally
        * promotion (to all possibiliites)
        * capture promotion
        Negative tests:
        * Don't move backwards
        * Don't capture forwards
        * Don't capture backwards and diagonally
        '''
        piece_list = [King('w', 'e1'), # just so W has a King
                     Pawn('w', 'f7'), # pawn can promote on f8 and capture and promote on g8
                     Pawn('w', 'a2'), # pawn can go to a3 or a4
                     Pawn('w', 'b5'), # pawn can capture ep on c6
                     Pawn('w', 'b6'), # blocks b5 pawn from moving forward, can move to b7
                     Pawn('w', 'h2'), # blocked by K on h3, can capture N on g3
                     King('b', 'h3'), # blocking h2 pawn
                     Knight('b','g3'), # can be captured by h2 pawn
                     Pawn('b', 'c5'), # pawn can be captured ep on c6
                     Rook('b', 'g8'), # can be captured by f7 pawn
                     ]
        ep_square = 'c6'
        g = Game()
        b = Board(piece_list=piece_list)
        print("Board for testing pawn moves:")
        print(b)
        g.set_board(b)
        g.set_white_to_move()
        g.ep_square = b.square_name_to_array_idxs(ep_square) # standardize representation
        # Get legal moves
        moves = g.get_moves_for()
        move_strs = [move.to_long_algebraic(note_ep=True) for move in moves]
        # Check results
        some_expected_moves = ['Pf7f8=Q', 'Pf7xg8=N', 'Pb5xc6e.p.', 'Pb6b7', 'Ph2xg3','Pa2a4', 'Pa2a3']
        unexpected_moves = ['Pf7f8', 'Pb5b6', 'Pa2xb3', 'Pa2b3', 'Pa2b4', 'Ph2xh3','Ph2h3']

        for move in some_expected_moves:
            assert move in move_strs, "Expected move %s not found in actual moves!" % (move)
        for move in unexpected_moves:
            assert move not in move_strs, "Unexpected move %s found in actual moves!" % (move)

        return True


    




def run_me_if_i_am_the_main_file():
    
    # Run the test I'm working on right now!
    TestRLM().test_pawn_moves_1()
    
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
    #sillyDude()

    print('Testing move generation and Piece objects...')
    g = Game()
    # Create pieces to place on board
    K = King('w', 'e1') # white king on e1
    k = King('b', 'e8') # black king on e8
    b = Board(piece_list=[K, k]) # create board from list of placed pieces
    g.set_board(b) # Associate board with Game object
    moves = g.get_moves_for() # get moves for the side to move (white by default)
    move_strings = [str(move) for move in moves] # make string (long algebraic) representations of each move
    print('List of possible moves:')
    print(move_strings)

    # Run all unit tests
    TestRLM().run_all_tests()




def run_him_if_i_am_not_the_main_file():
    print("Interesting; you thought it'd be a good idea to import a random-move-playing chess engine from some other application. How droll!")

if __name__ == '__main__':
    run_me_if_i_am_the_main_file()
else:
    run_him_if_i_am_not_the_main_file()
