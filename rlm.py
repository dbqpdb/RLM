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
        print('running init...')
        assert not (board_position is not None and piece_list is not None), 'Only one of board_position and piece_list can be specified when initializing a Board object; you specified both'
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
        and a list of black pieces. (Note that these are single characters, not Piece objects)'''
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
        file_idx_tuple, rank_idx_tuple = np.where(self.board_array == K_str)
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
    def to_long_algebraic(cls, piece_character, current_file_idx, current_rank_idx, new_file_idx, new_rank_idx, capture_flag=False):
        ''' Convert a piece character and a set of board indices to a long algebraic move string'''
        cur_file = cls.IDX_TO_FILE_DICT[current_file_idx]
        cur_rank = str(current_rank_idx + 1)
        capture_str = 'x' if capture_flag else ''
        dest_file = cls.IDX_TO_FILE_DICT[new_file_idx]
        dest_rank = str(new_rank_idx + 1)

        long_algebraic_move = piece_character + cur_file + cur_rank + capture_str + dest_file + dest_rank
        return long_algebraic_move


class GameController:
    '''
    Class to manage game flow. Should handle gathering player info, setting up game,
    prompting players for moves, calling comment generation routines, orchestrating
    post-game processes (e.g. saving to PGN).  Game state should be held in a Game 
    object, board state in a Board object.  
    '''
class Game:
    '''Class to hold a game state.  Game state includes everything in an FEN, plus
    a unique GameID.  Probably makes sense for it to keep track of everything that
    would go into a PGN too (player names, game history, location, event, site)
    '''
    def __init__(self, ep_square = None):
        self.ep_square = ep_square
        self.castling_state = 'kqKQ' # TODO: currently just a placeholder which allows all castling options
        self.side_to_move = 'w'
        self.white_pieces = []
        self.black_pieces = []
        self.board = None # This needs to be initialized before we can really play a game, but let's start with a placeholder which indicates it's not initialized

    def set_board(self, board):
        self.board = board
        self.initialize_pieces_from_board(board)

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

class MovesGenerator:
    ''' Class to generate a list of possible moves, given a game state
    [I don't know if there's really any reason to make this a class. It seemed like
    a separate set of functionalities than a board or game or player or piece, but on
    the other hand doesn't really seem like it needs to store any data at all, possibly 
    just house methods, which is maybe an OK thing for a class to do?]
    '''

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
        other_is_white = other==other.upper() and other != other.lower()
        other_is_black = other==other.lower() and other != other.upper()
        return (self.is_white() and other_is_black) or (self.is_black() and other_is_white)

    def is_friend(self, other):
        # Return true if other represents the same color piece as self. "other" should be a 
        # one-character string representing the name of a piece. If a string like '-' is passed in
        # which is unchanged by uppercasing or lowercasing, is_friend returns False
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
        new_rank_idx = current_file_idx + dy
        castling_boolean = False # castling is not handled by get_single_move(), so this is always false in moves generated by it
        promotion_piece = None # pawn promotion is not handled by get_single_move(), so this is always None in moves generated by it
        destination_occupant = board[new_file_idx, new_rank_idx]
        if destination_occupant is None or self.is_friend(destination_occupant):
            # Destination is off the board or is a friendly piece, move is invalid
            return None
        elif destination_occupant == Board.EMPTY_SQUARE:
            # Destination is currently empty, move is provisionally valid
            captured_piece = None
            candidate_move = (self.char, (current_file_idx, current_rank_idx), (new_file_idx, new_rank_idx), captured_piece, castling_boolean, promotion_piece) 
            return candidate_move
        elif self.is_enemy(destination_occupant):
            # Destination is occupied by an enemy piece, capture is provisionally valid
            captured_piece = destination_occupant
            candidate_move = (self.char, (current_file_idx, current_rank_idx), (new_file_idx, new_rank_idx), captured_piece, castling_boolean, promotion_piece) 
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
            if candidate_moves is None:
                # offset takes you into a friendly piece or off the board, no more valid moves are possible
                return candidate_moves
            elif self.is_capture(candidate_move):
                # possible move is a capture; this one should be included, but we shouldn't look for any further than this
                candidate_moves.append(candidate_move)
                return candidate_moves
            else:
                # candidate move is onto empty square, OK to keep looking further along the ray
                candidate_moves.append(candidate_move)
        raise Exception("The ray should have terminated by now... but it hasn't")


    def is_capture(self, move_string):
        # Convenience method for checking if a move string looks like a capture
        return True if 'x' in move_string else False

        
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
            moves = [move for move in provisional_moves if not our_king.is_in_check()]
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
        provisional_moves = KQRBN_Piece.get_moves(self)
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


    def get_kingside_castle_move(self):
        # needs to be updated if move format changes!
        board = self.game.board
        start = board.square_name_to_array_idxs(self.current_square)
        captured = None
        castling = True
        promotion_piece = None
        if self.is_white():
            dest = board.square_name_to_array_idxs('g1')
        else:
            dest = board.square_name_to_array_idxs('g8')
        move = (self.char, start, dest, captured, castling, promotion_piece)
        return move

    def get_queenside_castle_move(self):
        # needs to be updated if move format changes!
        board = self.game.board
        start = board.square_name_to_array_idxs(self.current_square)
        captured = None
        castling = True
        promotion_piece = None
        if self.is_white():
            dest = board.square_name_to_array_idxs('c1')
        else:
            dest = board.square_name_to_array_idxs('c8')
        move = (self.char, start, dest, captured, castling, promotion_piece)
        return move

    
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

        other_side_moves = self.game.get_moves_for(is_white=not self.is_white(), allow_own_king_checked=True)
        other_side_dest_squares = [move[2] for move in other_side_moves] 
        
        if (current_file_idx, current_rank_idx) in other_side_dest_squares:
            # Currently in check, castling is not allowed to either side
            kingside_allowed, queenside_allowed = False, False
        else:
            # Consider Kingside
            if ((current_file_idx+1, current_rank_idx) in other_side_dest_squares()) or ((current_file_idx+2, current_rank_idx) in other_side_dest_squares()):
                kingside_allowed = False # either moving into check or through check
            else:
                kingside_allowed = True # not in check, moving through check, or ending in check
            # Consider Queenside
            if ((current_file_idx-1, current_rank_idx) in other_side_dest_squares()) or ((current_file_idx-2, current_rank_idx) in other_side_dest_squares()):
                queenside_allowed = False # either moving into check or through check
            else:
                queenside_allowed = True # not in check, moving through check, or ending in check
        return kingside_allowed, queenside_allowed



    def is_in_check(self, board=None):
        '''Should return a true if this king is in check, false otherwise.
        In order to do this, we need to know if any of the other side's pieces
        could capture this king in one move, regardless of whether that move would 
        expose their own king to check.  One way to do this would be to generate 
        all possible moves for the other side, unfiltered by check status.  Another
        way would be to start from this king, and look out to see whether any pieces
        are in a position to attack it. Both approaches are kind of messy.  In general, 
        we do need to filter out moves which would expose our own king to check, '''
        other_side_moves = self.game.get_moves_for(other_side=True, allow_own_king_checked=True)
        other_side_dest_squares = [move[2] for move in other_side_moves]
        current_file_idx, current_rank_idx = board.square_name_to_array_idxs(self.current_square)
        if (current_file_idx, current_rank_idx) in other_side_dest_squares:
            in_check = True
        else: 
            in_check = False
        return in_check


class Queen (KQRBN_Piece):
    def __init__(self, color, square, game):
        char = 'Q' if self.is_white(color) else 'q'
        Piece.__init__(self, name='Queen', char=char, color=color, current_square=square, game=game)
        single_moves = [ [dx,dy] for dx in [-1,0,1]  for dy in [-1,0,1] ]
        single_moves.remove([0,0])
        ray_move_flag = True
        KQRBN_Piece.__init__(self, single_moves, ray_move_flag)

class Rook (KQRBN_Piece):
    def __init__(self, color, square, game):
        char = 'R' if self.is_white(color) else 'r'
        Piece.__init__(self, name='Rook', char=char, color=color, current_square=square, game=game)
        single_moves = [ [ 1,  0],
                         [-1,  0],
                         [ 0,  1],
                         [ 0, -1] ]
        ray_move_flag = True
        KQRBN_Piece.__init__(self, single_moves, ray_move_flag)
class Bishop (KQRBN_Piece):
    def __init__(self, color, square, game):
        char = 'B' if self.is_white(color) else 'b'
        Piece.__init__(self, name='Bishop', char=char, color=color, current_square=square, game=game)
        single_moves = [ [dx, dy] for dx in [-1,1] for dy in [-1,1] ]
        ray_move_flag = True
        KQRBN_Piece.__init__(self, single_moves, ray_move_flag)
class Knight (KQRBN_Piece):
    def __init__(self, color, square, game):
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
    def __init__(self, color, square, game):
        char = 'P' if self.is_white(color) else 'p'
        self.game = game # pawns unlike other pieces need access to the game state (for e.p. square only), not just the board
        board = game.board
        Piece.__init__(self, name='Pawn', char=char, color=color, current_square=square, game=game)
    
    def get_moves(self):
        ep_square = self.game.ep_square



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
    #sillyDude()

    print('Testing move generation and Piece objects...')
    g = Game()
    K = King('w', 'e1')
    k = King('b', 'e8')
    b = Board(piece_list=[K, k])
    g.set_board(b)
    g.get_moves_for()


def run_him_if_i_am_not_the_main_file():
    print("Interesting; you thought it'd be a good idea to import a random-move-playing chess engine from some other application. How droll!")

if __name__ == '__main__':
    run_me_if_i_am_the_main_file()
else:
    run_him_if_i_am_not_the_main_file()
