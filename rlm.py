#!/usr/bin/python3
# RLM.py
#
# The python implementation of the Random Legal Move chess-playin', sass talkin', ... thing
#
#
from __future__ import annotations

versionNumber = 0.40 # basic gameplay is now possible!

import numpy as np
import re
import sys
import random
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
        # Returns the rank number as a single character string (one-based, not zero-based)
        return str(int(square_idxs[1])+1)

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
                    move_elem_dict['promotion_piece'] = promotion_piece.upper() if white_is_moving else promotion_piece.lower()
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
            if (    (pmd['single_char']==unk or (move.single_char == pmd['single_char']))
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
    def parse_entered_move(cls, entered_move, white_is_moving, legal_moves_list):
        # Parses entered text move, and returns the set of legal moves which is 
        # consistent with entered info
        partial_move_dict = cls.parse_move_without_game(entered_move, white_is_moving)
        matched_moves = cls.find_matches_to_partial_move(partial_move_dict, legal_moves_list)
        return matched_moves


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
    """Parent class for players. Subclasses must implement `choose_move`."""

    def __init__(self, color: str | None = None):
        self.set_color(color)

    def set_color(self, color: str | None) -> None:
        """Set this player's color to 'w', 'b', or None (case-insensitive)."""
        if color is None:
            self.color = None
        elif color[0].lower()=='w':
            self.color = 'w'
        elif color[0].lower()=='b':
            self.color = 'b'
        else:
            raise Exception('Invalid color')

    def choose_move(self, game: Game, legal_moves_list: list[Move]) -> Move | None:
        """Pick a move from `legal_moves_list`. Subclasses must implement."""
        pass

    def is_valid_move(self, move: Move, legal_move_list: list[Move]):
        """Check if `move` is on `legal_move_list`. Not yet implemented — may move to Move."""
        pass

class RLMPlayer (Player):
    """Random Legal Move player — picks uniformly from the legal moves list."""

    def choose_move(self, game: Game, legal_moves_list: list[Move]) -> Move:
        chosen_move = random.choice(legal_moves_list)
        print('RLM player played %s'%chosen_move.to_long_algebraic())
        return chosen_move

class HumanPlayer (Player):
    """Prompts a human at the terminal for moves."""

    def choose_move(self, game: Game, legal_moves_list: list[Move]) -> Move:
        """Loop until the user enters something that matches exactly one legal move."""
        valid_move_entered = False
        while not valid_move_entered:
            entered_move = input("What is your move?\nEnter move: ")
            partial_move_dict = Move.parse_move_without_game(entered_move, white_is_moving=(game.side_to_move=='w'))
            matching_moves = Move.find_matches_to_partial_move(partial_move_dict, legal_moves_list)
            if len(matching_moves)==1:
                move = matching_moves[0]
                valid_move_entered = True
                msg = 'Your move is %s, got it!'%(move.to_long_algebraic())
            elif len(matching_moves)==0:
                # TODO #15: improve mismatch feedback — closest match, which fields conflict, etc.
                msg = 'Your entered move did not match any legal moves... try again!\n'
            else:
                move_str_list = [m.to_long_algebraic() for m in matching_moves]
                msg = 'Your entered move was consistent with %i legal moves, one of the following would be less ambiguous:\n'%len(matching_moves)
                for m in move_str_list:
                    msg += m + '\n'
                msg += 'Try again!\n'
            print(msg)
        return move


class NRLMPlayer (Player):
    """Non-Random Legal Move player — picks the first move on the legal list. Used in tests."""

    def choose_move(self, game: Game, legal_moves_list: list[Move]) -> Move:
        return legal_moves_list[0]


class GameController:
    """Top-level game flow: gather players, run the move loop, detect end-of-game.

    Game state lives in `Game`, board state in `Board`. Post-game tasks
    (e.g. PGN export) belong here too once they exist.
    """

    def start_new_game(self) -> None:
        """Prompt for participants, then run the main game loop to completion."""
        start_game_answer = input('Hey there, do you want to play a game of chess?\n(Y/n): ')
        if len(start_game_answer)>0 and start_game_answer[0].lower()=='n':
            print("Fine!! I'll play myself then!! You can watch.")
            white_player = RLMPlayer()
            black_player = RLMPlayer()
        else:
            side_answer = input('Would you like to play as white or black?\n(W/b): ')
            if len(side_answer)>0 and side_answer[0].lower()=='b':
                print("OK, I'll play as white!")
                white_player = RLMPlayer()
                black_player = HumanPlayer()
            else:
                print("OK, I'll play as black!")
                black_player = RLMPlayer()
                white_player = HumanPlayer()
        game = Game()
        game.set_board(Board())  # default starting position
        game.set_players(white_player, black_player)

        print("Here is the starting position:")
        game.show_board()

        game_is_over = False
        legal_moves = game.get_moves_for()
        while not game_is_over:
            if game.side_to_move[0] == 'w':
                move = white_player.choose_move(game, legal_moves)
            else:
                move = black_player.choose_move(game, legal_moves)
            game.make_move(move)
            game.show_board()

            # End-of-game detection: no legal moves → checkmate or stalemate.
            legal_moves = game.get_moves_for()
            if len(legal_moves)==0:
                game_is_over = True
                if game.side_to_move=='w':
                    K = [p for p in game.white_pieces if isinstance(p, King)][0]
                    game_over_msg = 'CHECKMATE!! Black wins!' if K.is_in_check() else "STALEMATE!!  It's a draw!"
                else:
                    k = [p for p in game.black_pieces if isinstance(p, King)][0]
                    game_over_msg = 'CHECKMATE!! White wins!' if k.is_in_check() else "STALEMATE!!  It's a draw!"
            elif game.half_moves_since >= 100:  # TODO: verify off-by-one for 50-move rule
                game_is_over = True
                game_over_msg = "DRAW!! That's 50 moves with no captures or pawn moves!"

        print(game_over_msg)
        print("Thanks for playing!")
        move_hist_ans = input("Shall I print the move history for this game?\n[Y/n]:")
        if not (move_hist_ans and move_hist_ans[0].lower()=='n'):
            game.print_move_history()
            
            

        





class Game:
    """Holds a single game's full state.

    State includes everything you'd find in a FEN (board, side to move,
    castling rights, en passant square, halfmove counter, fullmove
    counter) plus the players, the move history, and a Board object
    holding the live position. Eventually should also carry the metadata
    that goes into a PGN (player names, event, site, etc.).
    """

    def __init__(self, ep_square: SquareName | None = None):
        self.ep_square = ep_square
        # Bug #35: castling rights aren't derived from FEN. Placeholder hardcodes full rights.
        self.castling_state = ['K','Q','k','q']
        self.side_to_move = 'w'
        self.move_counter = 1
        self.half_moves_since = 0
        self.white_pieces: list = []
        self.black_pieces: list = []
        self.board: Board | None = None
        self.white_player: Player | None = None
        self.black_player: Player | None = None
        self.move_history: list[Move] = []


    def copy(self):
        game_copy = Game()
        game_copy.ep_square = self.ep_square
        game_copy.castling_state = self.castling_state.copy()
        game_copy.side_to_move = self.side_to_move
        game_copy.white_pieces = self.white_pieces.copy()
        game_copy.black_pieces = self.black_pieces.copy()
        game_copy.board = self.board.copy() # make a copy of the board, don't reference same board
        # NOTE: Any need to copy Players? (not yet, but consider)
        game_copy.move_history = self.move_history.copy()
        return game_copy


    def set_board(self, board: Board) -> None:
        """Attach a Board to this Game and (re)build the piece lists."""
        self.board = board
        self.initialize_pieces_from_board(board)

    def set_players(self, white_player: Player, black_player: Player) -> None:
        self.white_player = white_player
        self.black_player = black_player

    def show_board(self) -> None:
        """Print the current board state."""
        print(self.board)

    def print_move_history(self) -> None:
        """Print the full move history in approximate PGN format."""
        hist_str = 'Move History:\n'
        for idx, move in enumerate(self.move_history):
            if idx % 2 == 0:
                # white move opens a numbered pair
                hist_str += "%i. %s  "%((idx/2+1), move.to_long_algebraic(use_figurine=True, note_ep=True))
            else:
                # black move closes the pair
                hist_str += "%s\n" % (move.to_long_algebraic(use_figurine=True, note_ep=True))
        print(hist_str)

    def make_move(self, move: Move) -> None:
        """Apply `move` to the game: update board, piece lists, and counters.

        Replaces the Piece objects entirely (rebuilt from the board). If
        Piece state ever needs to persist (e.g. per-piece move history),
        this method needs to change. Handles castling rook movement,
        en-passant captures, promotion piece replacement, and updates
        castling rights based on king/rook moves.
        """
        board = self.board
        start_sq = move.starting_square
        dest_sq = move.destination_square
        board.move(start_sq, dest_sq)

        if move.is_castling:
            # Also move the rook to its post-castle square.
            if board.is_same_square(dest_sq,'g1'):
                board.move('h1','f1')
            elif board.is_same_square(dest_sq, 'c1'):
                board.move('a1','d1')
            elif board.is_same_square(dest_sq, 'g8'):
                board.move('h8','f8')
            elif board.is_same_square(dest_sq, 'c8'):
                board.move('a8','d8')
            else:
                raise Exception("Move said it was castling move, but didn't move to g or c file, instead moved to '%s'" % board.square_to_alg_name(dest_sq) )
            if move.single_char=='K':
                self.set_castling_state('K', False)
                self.set_castling_state('Q', False)
            else:
                self.set_castling_state('k', False)
                self.set_castling_state('q', False)
        elif move.is_en_passant_capture:
            # The captured pawn sits on the destination file but starting rank.
            board[move.destination_square[0], move.starting_square[1]] = Board.EMPTY_SQUARE
        elif move.single_char=='K':
            # King moves invalidate castling on both sides.
            self.set_castling_state('K', False)
            self.set_castling_state('Q', False)
        elif move.single_char=='k':
            self.set_castling_state('k', False)
            self.set_castling_state('q', False)
        elif move.single_char=='R':
            # Rook leaving its starting square disables castling on that side.
            if board.is_same_square(move.starting_square, 'h1'):
                self.set_castling_state('K', False)
            elif board.is_same_square(move.starting_square, 'a1'):
                self.set_castling_state('Q', False)
        elif move.single_char=='r':
            if board.is_same_square(move.starting_square, 'h8'):
                self.set_castling_state('k', False)
            elif board.is_same_square(move.starting_square, 'a8'):
                self.set_castling_state('q', False)
        elif move.promotion_piece is not None:
            # Match the case of the moving pawn.
            board[move.destination_square] = move.promotion_piece.upper() if move.single_char==move.single_char.upper() else move.promotion_piece.lower()

        # Bug #34: castling rights aren't revoked when a rook is captured on its starting square.
        # Rebuild piece objects from the (updated) board — board is the master representation.
        self.initialize_pieces_from_board(board)

        self.move_counter = self.move_counter+1 if self.side_to_move == 'b' else self.move_counter
        if move.captured_piece is not None or move.single_char.upper()=='P':
            self.half_moves_since = 0  # reset on capture or pawn move
        else:
            self.half_moves_since += 1
        self.side_to_move = 'b' if self.side_to_move=='w' else 'w'
        self.ep_square = move.new_en_passant_square
        self.move_history.append(move)


    def set_white_to_move(self) -> None:
        self.side_to_move = 'w'

    def set_black_to_move(self) -> None:
        self.side_to_move = 'b'

    def initialize_pieces_from_board(self, board: Board) -> None:
        """Rebuild `white_pieces` / `black_pieces` from `board`'s current state."""
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

    def set_castling_state(self, castling_char: str, bool: bool) -> None:
        """Toggle one castling permission on or off (e.g. 'K' for white kingside)."""
        castling_state = self.castling_state
        if bool:
            if castling_char not in castling_state:
                castling_state += castling_char
        else:
            castling_state = [s for s in castling_state if not s==castling_char]
        # Keep canonical KQkq order.
        self.castling_state = [s for s in 'KQkq' if s in castling_state]

    def get_castling_state(self, is_white: bool) -> tuple[bool, bool]:
        """Return `(kingside_allowed, queenside_allowed)` for the requested side."""
        if is_white:
            kingside_allowed = 'K' in self.castling_state
            queenside_allowed = 'Q' in self.castling_state
        else:
            kingside_allowed = 'k' in self.castling_state
            queenside_allowed = 'q' in self.castling_state
        return kingside_allowed, queenside_allowed

    def get_moves_for(self, other_side: bool = False, allow_own_king_checked: bool = False) -> list[Move]:
        """Generate all moves for one color in the current position.

        Args:
            other_side: If False (default), generate for the side to move.
                If True, generate for the side NOT to move.
            allow_own_king_checked: If False (default), filter out moves
                that would leave the moving side's king in check. If True,
                return the unfiltered list — needed because the check
                detector itself generates the *other* side's moves
                ignoring whether they'd be self-checks (a pinned bishop
                can still give check).

        When `allow_own_king_checked=True`, castling moves are omitted.
        They can't be captures (so they don't matter for check detection),
        and computing their legality involves nested check tests that
        would make this expensive and circular.
        """
        moves = []
        if (self.side_to_move =='w' and not other_side) or (self.side_to_move=='b' and other_side):
            pieces_to_move = self.white_pieces
        else:
            pieces_to_move = self.black_pieces
        for p in pieces_to_move:
            moves.extend(p.get_moves(allow_own_king_checked=allow_own_king_checked))
        return moves

class Piece:
    """Superclass of all chess pieces.

    Each piece has a name, a single-character abbreviation (case carries
    color: uppercase white, lowercase black), a color, a current square,
    and a reference to its containing Game.
    """

    def __init__(self, name: str, char: PieceChar, color: str, current_square: SquareName, game: Game | None):
        self.name = name
        self.char = char
        self.color = color
        self.current_square = current_square
        self.game = game

    def get_moves(self, allow_own_king_checked: bool = False) -> list[Move]:
        """Return all legal moves for this piece. Subclasses override.

        If `allow_own_king_checked` is False (default), moves that would
        leave or place the moving side's king in check are filtered out.
        If True, the unfiltered list is returned — used internally by
        `is_in_check`, which needs to consider attacks even from pinned
        pieces.
        """
        pass

    def is_white(self, color: str | None = None) -> bool:
        """Return True iff `color` (or self.color if None) is white."""
        if color is None:
            color = self.color
        return color[0].lower() == 'w'

    def is_black(self) -> bool:
        return not self.is_white()

    def is_enemy(self, other: str | None) -> bool:
        """Return True iff `other` is a piece of the opposite color.

        `other` is a single-character piece string. Returns False for
        None (off-board) or for characters that aren't case-sensitive
        piece letters (e.g. '-').
        """
        if other is None:
            return False
        other_is_white = other==other.upper() and other != other.lower()
        other_is_black = other==other.lower() and other != other.upper()
        return (self.is_white() and other_is_black) or (self.is_black() and other_is_white)

    def is_friend(self, other: str | None) -> bool:
        """Return True iff `other` is a piece of the same color. False for None."""
        if other is None:
            return False
        other_is_white = other==other.upper() and other != other.lower()
        other_is_black = other==other.lower() and other != other.upper()
        return (self.is_white() and other_is_white) or (self.is_black() and other_is_black)

    @classmethod
    def piece_from_char_and_square(cls, piece_char: PieceChar, square: SquareName, game: Game | None) -> Piece | None:
        """Build the right Piece subclass from a single-character name.

        Returns None for the empty-square char.
        """
        assert piece_char in 'KQRBNPkqrbnp'+Board.EMPTY_SQUARE, 'Piece character must be one of "KQRBNPkqrbnp" (or empty square character)!'
        if piece_char==Board.EMPTY_SQUARE:
            return None
        color = 'w' if piece_char.upper()==piece_char else 'b'
        upper_piece_char = piece_char.upper()
        if upper_piece_char=='K':
            piece = King(color, square, game)
        elif upper_piece_char=='Q':
            piece = Queen(color, square, game)
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
    """Superclass for K, Q, R, B, N — non-pawn pieces.

    All of these can be described by a list of `(dx, dy)` offsets plus a
    flag for whether the offset is repeated until blocked (Q, R, B) or
    not (K, N). This class provides shared `get_single_move` and
    `get_ray_moves` helpers; subclasses just set the move pattern.
    """

    def __init__(self, single_moves: list, ray_move_flag: bool):
        self.single_moves = single_moves
        self.ray_move_flag = ray_move_flag

    def get_single_move(self, dx: int, dy: int) -> Move | None:
        """Return a Move for offset `(dx, dy)`, or None if the destination is off-board or friendly.

        Captures and quiet moves both return a populated Move; only
        same-color landing or off-board returns None.
        """
        board = self.game.board
        current_file_idx, current_rank_idx = board.square_name_to_array_idxs(self.current_square)
        new_file_idx = current_file_idx + dx
        new_rank_idx = current_rank_idx + dy
        destination_occupant = board[new_file_idx, new_rank_idx]
        if destination_occupant is None or self.is_friend(destination_occupant):
            return None  # off-board or friendly piece
        elif destination_occupant == Board.EMPTY_SQUARE:
            return Move(self.char, self.current_square, (new_file_idx, new_rank_idx))
        elif self.is_enemy(destination_occupant):
            return Move(self.char, self.current_square, (new_file_idx, new_rank_idx), captured_piece=destination_occupant)
        else:
            raise Exception('Destination occupant appears to be none of the expected outcomes: enemy, friend, empty, or off board!')

    def get_ray_moves(self, dx: int, dy: int) -> list[Move]:
        """Repeatedly apply `(dx, dy)` until blocked, returning all moves on that ray.

        Stops at the first friendly piece or board edge (excluded), or at
        the first enemy piece (included as a capture).
        """
        candidate_moves = []
        max_ray_length = 10
        for iteration_counter in range(1, max_ray_length+1):
            candidate_move = self.get_single_move(iteration_counter*dx, iteration_counter*dy)
            if candidate_move is None:
                return candidate_moves  # hit friendly or off-board
            elif candidate_move.is_capture():
                candidate_moves.append(candidate_move)
                return candidate_moves  # captures terminate the ray
            else:
                candidate_moves.append(candidate_move)
        raise Exception("The ray should have terminated by now... but it hasn't")

        
    def get_moves(self, allow_own_king_checked: bool = False) -> list[Move]:
        """Generate all provisionally legal moves for this piece.

        "Provisional" because game-state-dependent rules (e.g. castling
        rights) aren't applied here; the King subclass extends this for
        castling-specific logic.

        Filters out self-check moves unless `allow_own_king_checked=True`.
        """
        provisional_moves = []
        board = self.game.board

        if not self.ray_move_flag:
            for dx, dy in self.single_moves:
                candidate_move = self.get_single_move(dx, dy)
                if candidate_move is not None:
                    provisional_moves.append(candidate_move)
        else:
            for dx, dy in self.single_moves:
                provisional_moves.extend(self.get_ray_moves(dx, dy))

        if not allow_own_king_checked:
            king_square = board.find_king_square(self.color)
            our_king = King(self.color, king_square, self.game)
            return [m for m in provisional_moves if not our_king.is_in_check_after_move(m)]
        return provisional_moves


class King (KQRBN_Piece):
    """King: single-square moves in all 8 directions, plus castling."""

    def __init__(self, color: str, square: SquareName, game: Game | None = None):
        char = 'K' if self.is_white(color) else 'k'
        Piece.__init__(self, name='King', char=char, color=color, current_square=square, game=game)
        single_moves = [[dx, dy] for dx in [-1, 0, 1] for dy in [-1, 0, 1]]
        single_moves.remove([0, 0])
        KQRBN_Piece.__init__(self, single_moves, ray_move_flag=False)

    def get_moves(self, allow_own_king_checked: bool = False) -> list[Move]:
        """Overrides Piece.get_moves to add castling.

        Castling is legal iff: castling rights are present in the game
        state, king and rook are on their starting squares with empty
        squares between, the king is not currently in check, the square
        moved through is not attacked, and the destination square is
        not attacked. Skipped entirely when `allow_own_king_checked=True`
        (cheaper and not needed for check detection).
        """
        provisional_moves = KQRBN_Piece.get_moves(self, allow_own_king_checked=allow_own_king_checked)
        if not allow_own_king_checked:
            kingside_allowed_by_state, queenside_allowed_by_state = self.game.get_castling_state(self.color)
            kingside_allowed_by_position, queenside_allowed_by_position = self.get_castling_allowed_by_position()
            kingside_allowed_by_check, queenside_allowed_by_check = self.get_castling_allowed_by_check()

            if kingside_allowed_by_state and kingside_allowed_by_position and kingside_allowed_by_check:
                provisional_moves.append(self.get_kingside_castle_move())
            if queenside_allowed_by_state and queenside_allowed_by_position and queenside_allowed_by_check:
                provisional_moves.append(self.get_queenside_castle_move())
        return provisional_moves


    def get_kingside_castle_move(self) -> Move:
        """Return the castling Move object for this king's kingside castle."""
        board = self.game.board
        dest = board.square_name_to_array_idxs('g1' if self.is_white() else 'g8')
        return Move(self.char, self.current_square, dest, is_castling=True)

    def get_queenside_castle_move(self) -> Move:
        """Return the castling Move object for this king's queenside castle."""
        board = self.game.board
        dest = board.square_name_to_array_idxs('c1' if self.is_white() else 'c8')
        return Move(self.char, self.current_square, dest, is_castling=True)


    def get_castling_allowed_by_position(self) -> tuple[bool, bool]:
        """Return `(kingside_ok, queenside_ok)` based on board layout only.

        Requires king on starting square, rook on its corner, and all
        squares between them empty.
        """
        board = self.game.board
        if self.is_white():
            if board['e1']=='K':
                kingside_allowed = (
                    board['f1']==Board.EMPTY_SQUARE and board['g1']==Board.EMPTY_SQUARE and board['h1']=='R'
                )
                queenside_allowed = (
                    board['d1']==Board.EMPTY_SQUARE and board['c1']==Board.EMPTY_SQUARE and
                    board['b1']==Board.EMPTY_SQUARE and board['a1']=='R'
                )
            else:
                kingside_allowed = queenside_allowed = False
        else:
            if board['e8']=='k':
                kingside_allowed = (
                    board['f8']==Board.EMPTY_SQUARE and board['g8']==Board.EMPTY_SQUARE and board['h8']=='r'
                )
                queenside_allowed = (
                    board['d8']==Board.EMPTY_SQUARE and board['c8']==Board.EMPTY_SQUARE and
                    board['b8']==Board.EMPTY_SQUARE and board['a8']=='r'
                )
            else:
                kingside_allowed = queenside_allowed = False
        return kingside_allowed, queenside_allowed

    def get_castling_allowed_by_check(self) -> tuple[bool, bool]:
        """Return `(kingside_ok, queenside_ok)` based on check status.

        Castling is disallowed on a side if the king is currently in check
        or if either intermediate square is attacked by the opponent.
        """
        board = self.game.board
        current_file_idx, current_rank_idx = board.square_name_to_array_idxs(self.current_square)
        other_side_moves = self.game.get_moves_for(other_side=True, allow_own_king_checked=True)
        other_side_dest_squares = [move.destination_square for move in other_side_moves]

        if (current_file_idx, current_rank_idx) in other_side_dest_squares:
            return False, False  # currently in check
        kingside_allowed = not (
            (current_file_idx+1, current_rank_idx) in other_side_dest_squares or
            (current_file_idx+2, current_rank_idx) in other_side_dest_squares
        )
        queenside_allowed = not (
            (current_file_idx-1, current_rank_idx) in other_side_dest_squares or
            (current_file_idx-2, current_rank_idx) in other_side_dest_squares
        )
        return kingside_allowed, queenside_allowed


    def is_in_check_after_move(self, move: Move) -> bool:
        """Return True iff the moving side's king would be in check after `move`.

        Works on a copy of the game so the live state is unaffected. See
        #42 for the perf cost of the copy-per-candidate-move pattern.
        """
        temp_game = self.game.copy()
        temp_game.make_move(move)
        other_side_moves = temp_game.get_moves_for(allow_own_king_checked=True)
        other_side_dest_squares = [m.destination_square for m in other_side_moves]
        for other_side_dest in other_side_dest_squares:
            if temp_game.board[other_side_dest]==self.char:
                return True
        return False


    def is_in_check(self) -> bool:
        """Return True iff this king is currently in check.

        Detects check by generating the opponent's moves with
        `allow_own_king_checked=True` (so pinned attackers are included)
        and checking whether any can reach this king's square.
        """
        other_side_moves = self.game.get_moves_for(other_side=True, allow_own_king_checked=True)
        other_side_dest_squares = [move.destination_square for move in other_side_moves]
        current_file_idx, current_rank_idx = self.game.board.square_name_to_array_idxs(self.current_square)
        return (current_file_idx, current_rank_idx) in other_side_dest_squares


class Queen (KQRBN_Piece):
    """Queen: ray moves in all 8 directions."""

    def __init__(self, color: str, square: SquareName, game: Game | None = None):
        char = 'Q' if self.is_white(color) else 'q'
        Piece.__init__(self, name='Queen', char=char, color=color, current_square=square, game=game)
        single_moves = [[dx, dy] for dx in [-1, 0, 1] for dy in [-1, 0, 1]]
        single_moves.remove([0, 0])
        KQRBN_Piece.__init__(self, single_moves, ray_move_flag=True)

class Rook (KQRBN_Piece):
    """Rook: ray moves in the 4 cardinal directions."""

    def __init__(self, color: str, square: SquareName, game: Game | None = None):
        char = 'R' if self.is_white(color) else 'r'
        Piece.__init__(self, name='Rook', char=char, color=color, current_square=square, game=game)
        single_moves = [[1, 0], [-1, 0], [0, 1], [0, -1]]
        KQRBN_Piece.__init__(self, single_moves, ray_move_flag=True)

class Bishop (KQRBN_Piece):
    """Bishop: ray moves in the 4 diagonal directions."""

    def __init__(self, color: str, square: SquareName, game: Game | None = None):
        char = 'B' if self.is_white(color) else 'b'
        Piece.__init__(self, name='Bishop', char=char, color=color, current_square=square, game=game)
        single_moves = [[dx, dy] for dx in [-1, 1] for dy in [-1, 1]]
        KQRBN_Piece.__init__(self, single_moves, ray_move_flag=True)

class Knight (KQRBN_Piece):
    """Knight: 8 fixed L-shaped offsets, no ray."""

    def __init__(self, color: str, square: SquareName, game: Game | None = None):
        char = 'N' if self.is_white(color) else 'n'
        Piece.__init__(self, name='Knight', char=char, color=color, current_square=square, game=game)
        single_moves = [
            [-1,  2], [ 1,  2], [ 2,  1], [ 2, -1],
            [ 1, -2], [-1, -2], [-2, -1], [-2,  1],
        ]
        KQRBN_Piece.__init__(self, single_moves, ray_move_flag=False)


class Pawn (Piece):
    """Pawn — handled separately because its legal moves are direction-dependent and asymmetric."""

    def __init__(self, color: str, square: SquareName, game: Game | None = None):
        char = 'P' if self.is_white(color) else 'p'
        Piece.__init__(self, name='Pawn', char=char, color=color, current_square=square, game=game)

    def get_moves(self, allow_own_king_checked: bool = False) -> list[Move]:
        """Generate all pawn moves: forward 1, forward 2 from home rank, diagonal captures, en passant, promotions.

        Filters self-check moves unless `allow_own_king_checked=True`.
        En-passant generation is skipped when `allow_own_king_checked=True`
        because in that path we're computing the non-moving side's moves,
        and any EP square belongs to the side currently to move.
        """
        move_candidates = []
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

        # Two-square move from home rank — creates an en-passant target.
        if current_rank_idx == home_rank_idx:
            if board[forward_sq]==Board.EMPTY_SQUARE and board[forward_two_sq]==Board.EMPTY_SQUARE:
                move_candidates.append(Move(self.char, self.current_square, forward_two_sq, new_en_passant_square=forward_sq))

        # Promotion rank check.
        if self.is_white() and (current_rank_idx + move_dir == 7):
            would_be_promoting = True
            promotion_piece_list = ['Q', 'R', 'B', 'N']
        elif self.is_black() and (current_rank_idx + move_dir == 0):
            would_be_promoting = True
            promotion_piece_list = ['q', 'r', 'b', 'n']
        else:
            would_be_promoting = False

        # Forward one square (with optional promotion).
        if board[forward_sq] == Board.EMPTY_SQUARE:
            if would_be_promoting:
                for pp in promotion_piece_list:
                    move_candidates.append(Move(self.char, self.current_square, forward_sq, promotion_piece=pp))
            else:
                move_candidates.append(Move(self.char, self.current_square, forward_sq))

        if self.game.ep_square is not None and not allow_own_king_checked:
            ep_square = board.square_name_to_array_idxs(self.game.ep_square)
        else:
            ep_square = None

        # Diagonal captures (with optional promotion or en passant).
        for dest in [diag_east_sq, diag_west_sq]:
            if self.is_enemy(board[dest]):
                captured_piece = board[dest]
                if would_be_promoting:
                    for pp in promotion_piece_list:
                        move_candidates.append(Move(self.char, self.current_square, dest, captured_piece=captured_piece, promotion_piece=pp))
                else:
                    move_candidates.append(Move(self.char, self.current_square, dest, captured_piece=captured_piece))
            elif ep_square is not None and dest==ep_square:
                # EP capture: captured pawn is on the destination file but moving pawn's rank.
                captured_piece = board[dest[0], current_rank_idx]
                assert captured_piece.lower()=='p', 'En passant capture should only possibly capture pawns, but captured piece is "%s"' % (captured_piece)
                move_candidates.append(Move(self.char, self.current_square, dest, captured_piece=captured_piece, is_en_passant_capture=True))

        if not allow_own_king_checked:
            king_square = board.find_king_square(self.color)
            our_king = King(self.color, king_square, self.game)
            return [m for m in move_candidates if not our_king.is_in_check_after_move(m)]
        return move_candidates


        



def sillyDude():
    dude = random.choice(['Mike', 'Bryan'])
    print("Is " + dude + " silly?:")
    def backline():        
        print(' ' * messagelen, end='')
        print('\r', end='')

    for __ in range(50):
        compute = random.random()
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
        bleh = random.choice(self.lex[pos])
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
        
    def test_entered_move_processing(self):
        #  Test a variety of entered moves in constructed board positions and make sure
        #  moves are interpreted properly
        # Set up a board we can use for tests
        K = King('w', 'e1') # so white king can castle
        k = King('b', 'f7')
        R1 = Rook('w', 'a1') # white king can castle
        R2 = Rook('w', 'h1') # so white king can castle
        r1 = Rook('b', 'a8')
        r2 = Rook('b', 'h8')
        P1 = Pawn('w', 'b7') # able to promote and capture-promote
        p1 = Pawn('b', 'c5') # pawn which could be ep captured
        P2 = Pawn('w', 'd5') # pawn which do ep capture on c6

        b = Board(piece_list = [K,k,R1,R2,r1,r2,P1,p1,P2])
        g = Game()
        g.set_board(b)
        g.set_white_to_move()
        g.ep_square = 'c6'
        legal_moves_list = g.get_moves_for()
        
        # Test pawn promotion
        entered_move = 'b8=Q'
        matching_moves = Move.parse_entered_move(entered_move, white_is_moving=g.side_to_move=='w', legal_moves_list=legal_moves_list)
        expected_matching_moves = [Move('P', 'b7','b8', promotion_piece='Q')]
        assert(len(matching_moves)==len(expected_matching_moves), "There should be exactly %i matching move(s), but %i were found!"%(len(expected_matching_moves), len(matching_moves)) )
        entered_move = 'bxa8=N'
        entered_move = 'bxa8' # ambiguous because it doesn't specify promotion piece
        entered_move = 'bxR'# THIS IS TRICKY!!  In this position, it means b pawn takes R on a8, but it is ambiguous with bishop x Rook
        # Test ep capture
        entered_move = 'dxc6'
        entered_move = 'd5xc6'
        entered_move = 'dxc6ep'
        entered_move = 'dxc6 ep'
        entered_move = 'dxc6 e.p.'
        entered_move = 'c6'
        entered_move = 'c6 e.p.'
        # Test castling
        # Test different move styles
        # Test ambiguous move case
        # Test illegal move
        entered_move = 'Pf6xc6 e. p. '

        return True

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
    TestRLM().test_entered_move_processing()

    # Try playing a game!
    gc = GameController()
    gc.start_new_game()
    
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
    me.propound("If {noun} were {noun}, man, you'd {adverb} {verb} {determiner} {noun}!")
    # Create a board from a different FEN-type string
    FEN_board_string_2 = "rnbqkbnr/pp1ppppp/8/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2" # after 1. e4 c5; 2. Nf3 
    otherBoard = Board(FEN_board_string_2)
    print('Board array generated from FEN board string "%s": \n%s'%(FEN_board_string_2, str(otherBoard.board_array)))
    me.propound("There once was a {noun} named {name} from a {adjective} {noun}. Anyway, {pronoun} {adverb} {verb}.")
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
