#!/usr/local/bin/perl
## I'm adding comments to the original code to try to explain as much as possible
## what is happening.  These new comments will all start with two # signs to distinguish
## them from pre-existing comments. I am going to refrain from changing the code on this
## branch for as long as I possibly can :)
##
## The top line of the file, as I recall, makes it executable in some shell contexts
## by telling the shell where to find the perl interpreter executable.  I don't think
## it is necessary if you run it with the perl command. 
## 
## "use" statements in Perl incorporate code from other Perl modules (at least roughly)
use warnings;
use strict; ## makes it so that all local variables have to be declared with "my"
use vars '$separator', '$userside','$enginename'; ## declares these three variable names to be global within this package
use Benchmark; ## the Benchmark module is used for timing, it's used below to report how long moves took
$enginename = "RLMv0.96"; # making a change here for testing branch commit
$separator = "turkeyburp"; ## I think we use this as a unique separator string below (I'll verify and come back later)

print "Welcome to the RLM Engine. Would you like to play a game of chess? (yep/nope): ";
my $input = <>; ## This gets keyboard input from the terminal and puts it in the variable $input
my ($fen, $correct); ## This declares two variables without assigning anything to them
if($input =~ /y/i) ## In Perl, this means compare the string in $input with the pattern "y" (case insensitive), and if there is a match, return true
{       print "\nWould you like to play from the normal starting position? (yep/nope): ";
        $input = <>;
        if($input =~ /y/i) ## True if user typed something with a "y"
        {       $fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";  ## This is the FEN (Forsyth-Edwards Notation) for the normal starting position
        } ## Go read about FEN somewhere, it's pretty accessible, it's almost like reading the board left to right and top to bottom :)
        else ## if the user didn't type something with a "y"
        {       print "\nOkay. Please enter the FEN for the position from which you would like to play:\n";
                chomp($fen = <>); ## chomp removes the trailing newline character from the user's input
                if(&validfen($fen)) ## this is supposed to check if the position the user entered is actually a valid chess position (but the &validfen currently just always returns true because this is actually kind of hard to check)
                {       print &showboard($fen)."\nIs this correct? (yep/nope): ";  ## show the user the position they entered and ask if it is correct
                        chomp($correct = <>);  ## get the user's response 
                }
                while(($correct =~ /n/i) or (!&validfen($fen))) ## we can't proceed until there is a valid board position and the user has OK'd it
                {       if(!&validfen($fen))
                        {       print "That's not a valid FEN. Try again or type \"start\" to begin at the starting position.\n";
                        }
                        else
                        {       print "Okay. Try again with another FEN or type \"start\" to begin at the starting position.\n";
                        }
                        chomp($fen = <>); ## get another board position
                        if($fen =~ /s/i)  ## check if the user typed something with an "s" (present in "start" but not in any valid FEN)
                        {       $fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
                        }
                        if(&validfen($fen))
                        {       print &showboard($fen)."\nIs this correct? (yep/nope): "; ## print board position, ask if correct
                                chomp($correct = <>); ## get user's answer
                        }
                }
        }
}
else  ## if user didn't say yes to playing chess
{       print "In that case, I suggest twiddling your thumbs until you ARE ready to play chess. Good day to you!";
        exit; ## exit program
}
print "\nWould you like to play the white side or the black side?\n";
$input = <>; ## get user's response
if($input =~ /w/i) ## if user's response has a "w", they chose white
{       $userside = "w";  ## this is the variable that keeps track of whether the user is white, black, or not playing
        print "\nWonderful, I enjoy playing black!\n"
}
elsif($input =~ /b/i) ## if user's repsonse has a "b" (and no "w") they chose black
{       $userside = "b";
        print "\nWicked cool! I simply adore playing white!\n";
}
else  ## if user's response lacks a "w" or a "b", then the RLM will play both sides of the board
{       print "Aw, to heck with you! I'll play myself!!\n";
        $userside = "none"; ## this is how we represent that the user isn't playing either side
}
print "Should I record the moves of this game in a PGN file? (yep/nope):";
$input = <>; ## get user response to whether there should be a PGN record of the game
my $pgnflag = 0; ## initialize this to false. we'll change it to true if the user has said yes
my ($filename,$username,$site,$white,$black,$date,$tmpfilename); ## declare several variables without setting them
my $setupflag = 0; ## initalize to false.  This variable is to track whether the starting position is not the normal starting position
if ($input =~ /y/i) ## check if user response about PGN file contains a "y", if so, we need to set up the PGN file
{       print "What file would you like to record to?\nFilename: ";
        chomp($filename = <>); ## gather user response for name of pgn file
        if ($filename !~ /\.\w+/) ## check if the filename has an extension (a period followed by one or more letters)
        {       $filename = $filename . ".pgn"; ## if not, add a .pgn extension
        }
        $tmpfilename = "$filename.tmp";  ## Make a temporary pgn file with the same name but also .tmp on the end. This is to maintain a distinction between a partially written file and a finalized one. If you are appending to a PGN record of games, you wouldn't want to corrupt the whole thing with a broken pgn.
        open TMPPGNHANDLE, ">$tmpfilename"; ## This creates the temp pgn file, and opens it for writing. Printing to TMPPGNHANDLE will write into this file
        open REALPGNHANDLE, ">>$filename"; ## Creates the real pgn file and opens it for appending (not sure why). Printing to REALPGNHANDLE will write into this file
        ## TMPPGNHANDLE and REALPGNHANDLE are made global variables here, a quirky (and probably bad practice) thing allowed by Perl. I found this out looking at documentation for "open"
        ## The next section of code sets up the top of the PGN file (location, date, players, starting position if non-standard)
        unless ($userside eq "none") ## This is a funny perl conditional, it's the same as if ($userside ne "none"); {eq is the "equals" operator for strings, ne is the "not equal" operator}
        {       print "What do they call you?\nName: ";
                chomp($username = <>); ## get user's name, store in $username
        }
        print "Where can I find you?\nCurrent Location: ";
        chomp($site = <>); ## location of user
        print TMPPGNHANDLE "\n\n[Event \"RLM Game\"]\n[Site \"$site\"]\n"; ## Write the first few lines to the temp PGN file
        my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime(time); ## get the current time from the computer
        $date = join(".",$year+1900,$mon+1,$mday); ## Assemble the date in the format YYYY.MM.DD
        print TMPPGNHANDLE "[Date \"$date\"]\n[Round \"-\"]\n"; ## Write the date to the temp PGN file
        ## The next section sorts out the player names
        if ($userside eq "w")
        {       $white = $username;
                $black = $enginename;
        }
        elsif ($userside eq "b")
        {       $white = $enginename;
                $black = $username;
        }
        else
        {       $white = $enginename;
                $black = $enginename;
        }
        print TMPPGNHANDLE "[White \"$white\"]\n[Black \"$black\"]\n"; ## write player names to temp PGN
        ## $fen has the starting position, the next line checks if it matches the standard starting position
        if ($fen ne "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1") 
        {       print TMPPGNHANDLE "[SetUp \"1\"]\n[FEN \"$fen\"]\n"; ## If not standard, write the starting FEN to the temp PGN file
                $setupflag = 1; ## This flag being 1 (true) means that the game started from a non-standard position
        }
        print TMPPGNHANDLE "[Result \"*\"]\n"; ## This is what you write as the result for an unfinished game
        $pgnflag = 1; ## This flag being 1 (true) means that the game is being recorded to a PGN file
} ## end of if for PGN file set up.  We don't need an else because there's nothing to do if the "if" wasn't true
       
## Tell the user how to enter their moves, including some examples
print "\nWhen entering moves during the game, please indicate the piece to move, its origin square, and destination square. You may indicate a capture (with an \"x\") or check (with a \"+\") if you'd like, for example the following are all valid moves:\nBc1f4, e2e4, pc2c4, qa1xh8+, g7g8=q\n\n";
print &showboard($fen); ## This shows the starting board position (so that the user can look at it when deciding on their move)
my $usermove; ## declare variable to hold the user's chosen move
my $move; ## variable to hold the current move (whether the user's or not).
## The next line processes the initial position $fen by calling the subroutine named &processfen, and puts the results in several variables. 
## Feel free to jump down to the section a couple hundred lines below which says "sub processfen", where this subroutine is defined
my ($okcastle,$enpassant,$movessince,$totalmoves,$side2move,@restofstuff) = &processfen($fen);
## If Black is moving first and we're recording a PGN, we need to print the move number followed by 3 dots (as the placeholder for white's missing move). That just comes from the standard for PGN files. 
if ($pgnflag and $setupflag and $side2move eq "b")  
{       print TMPPGNHANDLE "$totalmoves. ... ";
}
##
## This marks the end of the set-up portion of the code, and the beginning of the game play
##
my $gameover = 0;  ## a flag to indicate whether the game is over, intialized to false
while(!$gameover)  ## loop until the game is marked over by changing $gameover to true
{ ## beginning of game while loop. Each pass through the loop corresponds to one move by one of the players
## From here to the end of the while loop should probably be indented, but we may have decided it pushed the text too far over to the right...
my $movestarttime = new Benchmark;  ## This is used to time how long moves take
#my $board = showboard($fen);
#print "Old Position:\n\n$board\n\n";
#my ($okcastle,$enpassant,$movessince,$totalmoves,$side2move,@restofstuff) = &processfen($fen);

## A chess game is automatically drawn if 50 full moves (50 moves by each side) have elapsed without a 
## pawn move or a capture. So, every move, we need to check whether this has happened, and the game needs 
## to end immediately if so. 
if ($movessince >= 100) ## $movessince counts half-moves since the last pawn move or capture, so it needs to get to 100 to trigger the automatic draw 
{       print "The game is drawn because both sides have just been running around like idiots and more than 50 moves have elapsed without a pawn move or capture, for crying out loud!\n\n";
        if ($pgnflag) ## this is true if the user requested a PGN output
        {       &writeresult("draw",$tmpfilename,$filename); ## The &writeresult subroutine writes the given result to the PGN file
        }
        exit;  ## this ends the RLM program
}
my $checkflag = &incheck($okcastle,$enpassant,@restofstuff); ## Checks whether the current player is in check
# Call the subroutine which makes the moves list!! ## Note, this list is of all possible moves of the current player's pieces, irrespective of check, en pessant, or castling.
my @curmoveslist = &makemoveslist($checkflag,$okcastle,$enpassant,@restofstuff);
#print "Current moves list is: @curmoveslist\n\n";
my @cmlalg = &cart2alg(@curmoveslist); ## translates the current list of moves from cartesian coordinates to algebraic notation.
#print "Current moves are: \n@cmlalg\n\n";
my @legalmoveslist; ## list to hold all legal moves
foreach my $move (@cmlalg){
        my $newfen = &makenewfen($move, $fen);
        my ($okcastle,$enpassant,$movessince,$totalmoves,$side2move,@newrestofstuff) = &processfen($newfen);
        #print "gargling \$newfen enpassant is $enpassant\n";
        my $switch = 0;
        my (@ouch,@gotcha);
        foreach my $pos (@newrestofstuff) {
                if ($pos eq $separator) {
                        $switch = 1;
                }
                else {
                        if (!$switch) {
                                push @gotcha, $pos;
                        }
                        else {
                                push @ouch, $pos;
                        }
                }
        }
        if (!&incheck($okcastle,$enpassant,@ouch,$separator,@gotcha)){
                push (@legalmoveslist, $move);
        }
}
@legalmoveslist = &garglelegalcastle(@legalmoveslist);  # remove castling if you'd be castling through check
my @legalmoveslist_alg = &cart2alg(@legalmoveslist);
#print "Legal Moves List is: @legalmoveslist_alg\n\n";
#print "The en passant square is $enpassant\n";
if ($#legalmoveslist_alg == -1){
        if (&incheck($okcastle,$enpassant,@restofstuff)){
                print "That is checkmate! Good-bye!!\n\n";
                $gameover = 1;
                if($pgnflag)
                {       if($side2move eq "w")
                        {       &writeresult("white wins", $tmpfilename)
                        }
                        else
                        {       &writeresult("black wins", $tmpfilename)
                        }
                }
                exit;
        }
        else {
                print "I guess that is stalemate.";
                $gameover = 1;
                if($pgnflag)
                {       &writeresult("draw", $tmpfilename)
                }
                exit;
        }
}
if ($side2move eq $userside)
{       &prompttalk;
        #print "Go ahead, make my day!\n\nEnter move: ";
        print "Enter move: ";
        chomp ($usermove = <>);
        $usermove = &movegrinder($usermove);
        my (@grindermoves, @legalmoveslist_alg);
        @legalmoveslist_alg = &cart2alg(@legalmoveslist);
        foreach (@legalmoveslist_alg)
        {       push @grindermoves, &movegrinder($_);
        }
        my $nonLegalMoveCount = 0;
        while(!&onlist($usermove, @grindermoves))
        {       if ($nonLegalMoveCount==0)
                {       # First time entering a non-legal move for this move
                        print "\nTut tut! I'm sorry, but that was not a legal move. If you've queened, don't forget to include \"=Q\", etc. Please try again.\n\nEnter move: ";
                        chomp ($usermove = <>);
                        $usermove = &movegrinder($usermove);
                        $nonLegalMoveCount++;
                } 
                elsif ($nonLegalMoveCount==1)
                {       # user has now entered more than one non-legal move, let's give them some help!
                        print "\nWell now, you're obviously having trouble.  Here is a suggestion of a random legal move you could make: ";
                        my $rand = sprintf("%i",rand($#legalmoveslist_alg+1));
                        my $suggestedMove = $legalmoveslist_alg[$rand];
                        print "$suggestedMove";
                        print "\nWhat's your move?\nEnter move: ";
                        chomp ($usermove = <>);
                        $usermove = &movegrinder($usermove);
                        $nonLegalMoveCount++;
                }
                else
                {       # user has now failed at least twice trying to enter a legal move, time to provide all possible moves, and they can choose!
                        print "\nOK, you're clearly not getting this. Here are all the possible legal moves you could make:\n";
                        foreach (@grindermoves)
                        {       
                                print "$_\n";
                        }
                        print "\nEnter move: ";
                        chomp ($usermove = <>);
                        $usermove = &movegrinder($usermove);
                        $nonLegalMoveCount++;
                }
        }
        $move = $usermove;
        &sillytalk;
        sleep(4);
}
else
{
        my $rand = sprintf("%i",rand($#legalmoveslist_alg+1));
        $move = $legalmoveslist_alg[$rand];
        &wisdomtalk;
        print "$move\n\n";
        sleep(4);
        #print "I in my infinite wisdom, choose to play: $move\n\n";
}
my $newfen = &makenewfen($move,$fen);
print "The new board position is:\n\n" . &showboard($newfen);
$fen = $newfen;
($okcastle,$enpassant,$movessince,$totalmoves,$side2move,@restofstuff) = &processfen($fen);
if ($pgnflag)
{       my $pgnmove = &formatmove($move);
        if ($side2move eq "b")
        {       print TMPPGNHANDLE "$totalmoves. $pgnmove ";     #white just moved
        }
        else
        {       print TMPPGNHANDLE "$pgnmove ";  # black just moved
        }
}
my $moveendtime = new Benchmark;
my $movetime = timediff($moveendtime,$movestarttime);
print "\n\nThe time for this move was ",timestr($movetime)."\n\n";
}# end of while loop
# end of main function
#=============================================================#
#                       SUBROUTINES                           #
#=============================================================#
#===============================================================================
## This subroutine was planned for development, but hasn't happened. It's a big project, and we don't even necessarily want to police this. People may want to create constructed non-possible boards to play from.
sub validfen
{
return 1;
}
#===============================================================================
## this subroutine processes and regularizes move inputs.
sub movegrinder
{
my $move = shift;
if ($move =~ /(o-o(?:-o)?)/i)
{        return lc($1); ## regularize the case of castling moves
}
my $editmove;
$move =~ s/^(\w\d)/P$1/; ## if the move is lacking a piece identifier, add in "P" at the front as the piece id
$move =~ /(\w)?(\w\d)x?(\w\d)(=[bnrqBNRQ])?/; ## parens here form matching groups that the following variables then assign from; e.g. "(\w)?" is the first group, indicating the piece; (\w\d) is the second group, grabbing the location the piece is moving from, and so on.
my $piece = $1;
my $startsquare = $2;
my $endsquare = $3;
my $queen;
## this next bit just tests whether the 4th group matched anything, and if so, assigns the pawn promotion piece.
if(defined $4)
{       $queen=$4;
}else{
        $queen="";
}
## This next bit regularizes the user's input, converting to uppercase white pieces, and to lowercase for black pieces (fen convention). It's nice to give users some leeway, and then neaten up the output.
if($userside eq "w")
{       #$editmove = "\u$1$2$3\U$4";
        $editmove = "\u$piece$startsquare$endsquare\U$queen";
}
else
{       #$editmove = "\l$1$2$3\L$4";
        $editmove = "\l$piece$startsquare$endsquare\L$queen";
}
return $editmove;
}
#===============================================================================
sub formatmove
{# this subroutine was written to standardize the formatting of moves for output to PGN
# It's also intended to be extensible so that various output formats could be requested
# At the moment, it requires that all input moves have the piece name and all
my $move = shift;
my $format = shift;
$format = "alglongupper" unless defined $format;
# Standardize the move for pgn output
#if it's castling, just lowercase it and return it
if ($move =~ /(o-o(?:-o)?)/i)
{        return lc($1);
}
if ($format eq "alglongupper") # algebraic, long format (both squares), and uppercase piece names
{       $move = &cart2alg($move); #force to algebraic notation
        if ($move !~ /^(\w\d)/)
        {       $move = ucfirst($move);  #force piece name to uppercase
        }
        $move =~ s/^P//; # remove a leading capital P
        $move =~ s/(=[bnrq])/uc($1)/e;
}
elsif ($format eq "algshortupper") #algebraic, short format (only destination square), and uppercase piece names
{       $move = &cart2alg($move);
        if ($move !~ /^(\w\d)/)
        {       $move = ucfirst($move);  #force piece name to uppercase
        }
        $move =~ s/(\w)?(\w\d)(x?)(\w\d)(=[bnrqBNRQ])?/$1$3$4$5/;
}
else
{       die "Format \"$format\" not recognized by formatmove subroutine";
}
return $move;
}
#===============================================================================
sub showboard
{
my $dashrow = ("-" x 25)."\n";
my $wsq = "|><";
my $bsq = "|  ";
my $oddrow = (($wsq.$bsq) x 4)."|\n";
my $evenrow = (($bsq.$wsq) x 4)."|\n";
my $board = (($dashrow.$oddrow.$dashrow.$evenrow) x 4).$dashrow;
#print $board;
my (@list,$numrows,$index);
for (my $i = 0; $i<64; $i++){
        $numrows = sprintf("%i",$i/8);
        $index = 3*$i+28+28*$numrows;
        push @list, $index;
}
my $break = $_[0]; #"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
my @break = split(" ",$break);
my $poses = $break[0];
$poses =~ s|(\d)|0 x $1|eg;
$poses =~ s|/||g;
$poses =~ s|0| |g;
my @board = split("", $poses);
my @template = split("",$board);
for (my $puke = 0; $puke<64; $puke++) {
        if ($board[$puke] ne " ") {
                $template[$list[$puke]] = $board[$puke];
        }
}
$board = join("",@template);
my @rows = split("\n",$board);
my @labelrows = (1,3,5,7,9,11,13,15);
my $labelrownum = 8;
for (my $rownum = 0; $rownum<17; $rownum++){
        if (&onlist($rownum,@labelrows)) {
                $rows[$rownum] = join(" ",$labelrownum,$rows[$rownum]);
                $labelrownum--;
        }
        else {
                $rows[$rownum] = join(" "," ",$rows[$rownum]);
        }
}
$board = join("\n",@rows,"    A  B  C  D  E  F  G  H\n\n");
return $board;
}
#===============================================================================
## The &processfen subroutine takes in a game state, represented by a FEN string
## and processes it into its parts, returning where it is permissable to castle (in $okcastle),
## whether there is a possible en passant capture square ($enpassant), how many half moves
## since the the last pawn move or capture ($movessince), the total number of whole moves
## in the game ($totalmoves), whose turn it is to move ($side2move), the positions of 
## all the pieces of the player whose turn it is to move (@side2move), an arbitrary and unique
## separator ("turkeyblurp") (so we can find where to break up the list later), and the 
## positions of all the pieces of the other player (@adversary).
##
## As an overview of how it does this is, bring in the FEN string, split it into pieces
## where there are spaces in the FEN, this yields 6 pieces, the first of which is the board
## position and the rest of which represent other aspects of the game state (whose turn, allowed
## castling, e.p., moves since capture or pawn move, and total game moves).  Only the board position
## requires much further processing.  We want to turn it into a list of positions of the white
## and black pieces. This subroutine takes a few steps to get there.  We decided that we wanted 
## to represent positions with a cartesian coordinate, so 3rd row (from white's side), 5th column, which is 
## square e3 in algebraic chess notation, would be 53 in our cartesian notation (column # then row #).
## I think we did it this way because we figured numbers would be easier to work with than translating 
## back and forth to letters for the column.  
## The raw board position starts off in $poslist as something like "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
## Then we strip out the forward slashes so it becomes "rnbqkbnrpppppppp8888PPPPPPPPRNBQKBNR"
## Next, we replace anywhere with a digit by that many copies of the number "0", so this one would become "rnbqkbnrpppppppp00000000000000000000000000000000PPPPPPPPRNBQKBNR"
## Any valid FEN board position run through this process will now be exactly 64 characters long, one for each board square in order from a8-h8,then a7-h7, etc down to h1 (left to right, then down looking at a board as normally printed)
## Empty squares will have 0, and non-empty squares will have a letter representing what piece is on that square, lowercase for black, uppercase for white.
## That 64 character string is then split into a list of 64 individual characters (@possplit)
## Next, separately, a list of the corresponding cartesian coordinates for each square is constructed (as @cart), 
## by looping over row numbers from 8 to 1 (outer loop) and column numbers from 1 to 8 (inner loop).
## Finally, we loop over each element of the list of 64 individual characters in @possplit and examine each one.
## If the character is a "0", then we don't do anything with it. If the character is a lowercase letter (a black piece),
## then we grab its corresponding cartesian coordinate and make a combined string which is the letter followed by the column
## number and row number.  For example, in the standard starting position, the first character in the @possplit list will be
## a lowercase 'r'.  The corresponding first element in the list @cart is '18', meaning first column and 8th row. So, the combined
## string is 'r18', meaning a black rook on a8. That, string, 'r18' is then added to the list of black piece positions (@blackpos)
## Lastly, we actually need to know the set of piece positions for the person whose turn it is, and so far we just know
## the white piece positions and the black piece positions.  So, depending on the $side2move, we either put the
## white piece position list in @adversary or in @side2move, and the black piece position list in the other one. 
## When we spit out the large list of outputs, Perl does not not keep them grouped the way we put them in, Perl just
## makes one big flat list of them. Because of this, we insert the $separator ('turkeyburp') into the list between the
## @side2move position list and the @adversary position list. That way, when we are going through the big output list, we
## know that everything after 'turkeyburp' is the @adversary position list.  The first 5 listed outputs are all single elements
## so we know that we can just take those individually.  Then, we know that everything after those first 5 until we hit 'turkeyburp'
## is the @side2move position list. Without a unique separator, it would be more work to figure out where @side2move was supposed 
## to end, and @adversary was supposed to begin. 
sub processfen
{ ## everything inside these braces is part of the &processfen subroutine
## The next few lines are old comments and don't do anything.  They probably indicate that this code was once the beginning of play. 
#use warnings;
# print "Welcome to Mike and Dan's RLM engine. Please enter the complete FEN of the position from which you would like to play. Don't forget to put spaces between the six data sets. Use a dash for an empty castling or en passant entry. If you would like to play from the starting position, just type \"start\". Enjoy!\n\n\n";
# $fen = <>;
# chomp $fen;
# $fen =~ s|\s+| |g;
## @_ is the list of inputs given when &processfen was called.  This next line gets the first input and assigns it to $fen. (If there were any other inputs they would be ignored)
my ($fen) = @_;#"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"; ## this comment is an example FEN for reference
# split up the FEN into the various data sets
my @fenar = (split " ", $fen); ## split the string in $fen into a list of strings, wherever spaces are found
my ($poslist, $side2move, $okcastle, $enpassant, $movessince, $totalmoves) = @fenar; ## assign the 6 elements of the @fenar list  to 6 individual variables
#print "$poslist\n$side2move\n$okcastle\n$enpassant\n$movessince\n$totalmoves\n";
$poslist =~ s|/||g; ## strip out forward slashes
#print "$poslist\n";
$poslist =~ s|(\d)|0 x $1|eg; ## replace digits with the corresponding number of "0" characters
#print "$poslist\n";
my @possplit = (split "", $poslist); ## split the $poslist string into a list of individual characters
#print "@possplit \n\n";
my @cart = (); ## initialize an empty list to hold cartesian square coordinates in the same order they appear in FEN's
my ($row,$col,$pos);
for($row = 8; $row > 0; $row--) { ## loop over rows in the same order they appear in FEN's, counting down from 8
        for($col = 1; $col < 9; ++$col) { ## loop over columns, counting up 1 to 8
                $pos = $col.$row; ## combine column and row into single string
                push @cart, $pos; ## add the string to the list @cart
        }
}
my (@whitepos,@blackpos) = ();
my $posnum;
for ($posnum=0; $posnum<64; $posnum++){
        if ($possplit[$posnum] =~ /[A-Z]/){ ## if the $posnum'th entry in @possplit is a capital letter...
                push @whitepos, $possplit[$posnum].$cart[$posnum]; ## ...combine that letter with corresponding entry in @cart and add it to the list of white piece positions
        }
        elsif ($possplit[$posnum] =~ /[a-z]/){ ## if the $posnum'th entry in @possplit is a lowercase letter...
                push @blackpos, $possplit[$posnum].$cart[$posnum]; ## ...combine that letter with corresponding entry in @cart and add it to the list of black piece positions
        }
}
#print "@whitepos\n\n@blackpos";
my (@side2move,@adversary);
if ($side2move =~ /w/i) { ## if $side2move has a "w", then the white pieces can move, and the black pieces belong to the adversary 
        @side2move  = @whitepos;
        @adversary = @blackpos;
}
else { ## otherwise, the black pieces can move, and the white pieces belong to the adversary
        @side2move = @blackpos;
        @adversary = @whitepos;
}
return ($okcastle,$enpassant,$movessince,$totalmoves,$side2move,@side2move,$separator,@adversary) ## return the huge list of outputs
} # end of &processfen
#===============================================================================
sub makenewfen
{
# this subroutine should make a new FEN out of an old FEN and a move
my ($move,$oldfen) = @_;
#print "Move in makenewfen is $move\n";
# split up the FEN into the various data sets
my @fenar = (split " ", $oldfen);
my ($poslist, $side2move, $okcastle, $enpassant, $movessince, $totalmoves) = @fenar;
$poslist =~ s|/||g;
$poslist =~ s|(\d)|0 x $1|eg;   # replace numbers with equal number of zeros
my @possplit = (split "", $poslist);   #break into 64-element array of squares
my $captureflag = 0;
my $pawnmoveflag = 0;
my ($piece,$oldx,$oldy,$newx,$newy);
if ($move =~ /o-o/)
{       #print "Welcome to the world of castling!\n";
        my ($koldx,$knewx,$roldx,$rnewx,$rank,$ind_kold,$ind_knew,$ind_rold,$ind_rnew);
        $koldx = 5;
        if ($move eq "o-o")
        {       $knewx = 7;
                $roldx = 8;
                $rnewx = 6;
        }
        elsif ($move eq "o-o-o")
        {       $knewx = 3;
                $roldx = 1;
                $rnewx = 4;
        }
        if ($side2move eq "w")
        {       $rank = 1;
        }
        else
        {       $rank = 8;
        }
        $ind_kold = &cart2ind($koldx,$rank);
        $ind_knew = &cart2ind($knewx,$rank);
        $ind_rold = &cart2ind($roldx,$rank);
        $ind_rnew = &cart2ind($rnewx,$rank);
        $possplit[$ind_knew] = $possplit[$ind_kold];
        $possplit[$ind_kold] = 0;
        $possplit[$ind_rnew] = $possplit[$ind_rold];
        $possplit[$ind_rold] = 0;
}
else
{
        # Convert move to cartesian
        my $move_cart = &alg2cart($move);
        $move_cart =~ s/(\w\d\d)x?(\d\d).*/$1$2/;
        #print "$move, $move_cart\n\n";
        ($piece,$oldx,$oldy,$newx,$newy) = split("",$move_cart);
        #print  $piece,$oldx,$oldy,$newx,$newy,"\n\n";
        # Convert cartesian locations to subscripts into fen array poslist
        my $ind_old = &cart2ind($oldx,$oldy);
        my $ind_new = &cart2ind($newx,$newy);
        #print @possplit,"\n\n";
        $captureflag = 1 unless ($possplit[$ind_new] eq "0");
        $possplit[$ind_old] = 0;  # mark old square empty
        $possplit[$ind_new] = $piece; # replace new square location with new piece
        unless ($enpassant eq "-")
        {       my ($file,$rank) = split(//,$enpassant);
                my %a2c = ("a",1,"b",2,"c",3,"d",4,"e",5,"f",6,"g",7,"h",8);
                $file = $a2c{$file};
                if ($file==$newx and $rank==$newy and $piece =~ /p/i)
                {       #this is an en passant capture
                        #print "This is an en passant capture in the world of en passant";
                        my $elimx = $file;
                        my $elimy = $oldy;
                        my $elimandelimind = $elimx+(8-$elimy)*8-1;
                        $possplit[$elimandelimind] = 0;
                        $captureflag = 1;
                }
        }
        if ($piece =~ /p/i and ($newy==8 or $newy==1))
        {       # this pawn must be promoted
                $move =~ /=([bnrq])/i;
                my $promoteto;
                if ($side2move eq "w")
                {       $promoteto = uc($1);
                }
                else
                {       $promoteto = lc($1);
                }
                $possplit[$ind_new] = $promoteto;
        }
        if ($piece =~ /p/i)
        {       $pawnmoveflag = 1;
        }
}
# reassemble main part of fen
my $newposlist = join("",@possplit);
#print "$newposlist\n\n";
# add slashes
$newposlist =~ s|(.{8})(?=.)|$1/|g; #excellent, that looks like that works
#print $newposlist;
# replace 0s with number of 0s
$newposlist =~ s/(0+)/length($1)/eg;
#print $newposlist, "\n\n";
# time to modify the other FEN fields
# side to move should be switched
my $newside2move;
if ($side2move =~ /w/i){
        $newside2move = "b";
}
else{
        $newside2move = "w";
}
# Castling options
if($move =~ /o-o/ or $piece =~/k/i)
{       if($side2move eq "w")
        {       $okcastle =~ s/K|Q//g;
        }
        else
        {       $okcastle =~ s/k|q//g;
        }
}
elsif($piece eq "R" and $oldx == 1 and $oldy == 1)
{       $okcastle =~ s/Q//;
}
elsif($piece eq "R" and $oldx ==8 and $oldy == 1)
{       $okcastle =~ s/K//;
}
elsif($piece eq "r" and $oldx == 1 and $oldy == 8)
{       $okcastle =~ s/q//;
}
elsif($piece eq "r" and $oldx == 8 and $oldy == 8)
{       $okcastle =~ s/k//;
}
my $newokcastle;
if($okcastle =~ /[KQkq]/)
{       $newokcastle = $okcastle;
}
else
{       $newokcastle = "-";
}
# however, the rules here are that it should change if the king moves, or if one of the rooks moves
#en passant square
# should be set if the move was a pawn move and if it moved two squares
my $newenpassant;
#my $move_alg = &cart2alg($move);
if ($move =~ /P(.)2.4/){
        $newenpassant = $1.3;
}
elsif ($move =~ /p(.)7.5/){
        $newenpassant = $1.6;
}
else {
        $newenpassant = "-";
}
# moves since capture or pawn move
# mostly this just increments, but if this move was a pawn move or a capture, then it should be reset to 0
my $newmovessince;
if ($pawnmoveflag) { # pawn move
        $newmovessince = 0;
}
elsif($captureflag) { # it's a capture
        $newmovessince = 0;
}
else {
        $newmovessince = ++$movessince;
}
# total moves
# increments if black just moved
my $newtotalmoves;
if ($side2move eq "b"){
        $newtotalmoves = ++$totalmoves;
}
else {
        $newtotalmoves = $totalmoves;
}
# Put it all back together and return it
my $newfen = join(" ",$newposlist,$newside2move, $newokcastle, $newenpassant, $newmovessince, $newtotalmoves);
return $newfen;
}
#===============================================================================
sub incheck
{
# ouch = side to move which might be in check
# gotcha = other side which might be doing the checking
my $switch = 0;
my (@ouch,@gotcha);
my $okcastle = shift;
my $enpassant = shift;
foreach my $pos (@_) {
        if ($pos eq $separator) {
                $switch = 1;
        }
        else {
                if (!$switch) {
                        push @ouch, $pos;
                }
                else {
                        push @gotcha, $pos;
                }
        }
}
my $pretendnotcheck = 0;
#print "Making Incheck MovesList\n";
my @moveslist = &makemoveslist($pretendnotcheck,$okcastle,$enpassant,@gotcha,$separator,@ouch);
# where is our king?
my $ksquare;
foreach (@ouch){
        if (/k(.+)/i){
                $ksquare = $1;
                last;
        }
}
# extract destination squares for gotcha
foreach (@moveslist) {
        s/\w{3}x?(\d{2}).*/$1/;
}
return &onlist($ksquare,@moveslist);
} # end of incheck
#===============================================================================
sub makemoveslist
{ ## The makemoveslist function is critical.  It takes in piece positions for 
## both sides, as well as other information relevant for determining moves (whether
## the current side is in check, whether castling is disallowed by previous moves,
## and whether there is an en passant square which could be a capture target).
## The expected structure of inputs is, in order:  
## $checkflag - a 0 or 1 indicating whether the current player is in check (or, actually,
##     just whether the current player should be considered to be in check, the &incheck 
##     function uses this flag temporarily set to 0 even though it doesn't know yet whether
##     the player is in check). I'll have to figure out why when reviewing the &incheck function
## $okcastle - a string which indicates what castling options have not been disallowed by 
##     prior moves.  It is "KQkq" if both white and black could still castle to both kingside
##     and queenside, for example.  If white has moved his kingside rook, then kingside castling 
##     is no longer allowed, and the string would be "Qkq" instead. If neither side can castle
##     in either direction, the string is "-"
## $enpassant - If the previous move was a two-square pawn move, this variable is set to the
##     square the pawn skipped over. For the following move (and only that move), it is legal 
##     for that pawn to be captured on the e.p. square, so we need to keep track of it. It is 
##     the only case in chess where a capturing piece does not move onto the square the captured
##     piece was on. 
## @sidetomove_cart - After the $enpassant input, there is a list of piece positions for 
##     the side to move, then the $separator, then a list of piece positions for the side
##     which is not moving. The piece positions for the side which is moving are assembled 
##     into the list @sidetomove_cart.  These piece locations are expected to be in cartesian
##     form, i.e. piecename, column number, row number, like N53 for a knight on f3.
## $separator - the marker dividing the sides pieces
## @sidenotmoving_cart - After the separator, the piece positions for the side which isn't
##     moving are listed, also in cartesian form.  These are assembled into @sidenotmoving_cart
## 
## Once the inputs are ingested, the approach is to loop over the piece positions for the 
## side whose turn it is to move.  On each pass through the loop, one current piece position
## is considered, and all the possible legal moves are generated from that position, based 
## on the rules of chess for how that kind of piece moves.  We use the letter representing
## the piece (i.e. b or B for bishop) to look up the characteristics of how the piece moves,
## including what directions it can go, and whether it moves anywhere along a line (termed
## a "ray" move below) or just one square (or jump for a knight) (termed a "single" move).
## Pawns move and capture differently, and have a number of special rules, so their move type
## is termed "pawn" and handled separately. 
## 
## Once the move type and basic move is specified, then the possible moves are obtained by 
## calling other functions, namely &getraymoves, &getsinglemove, and &getpawnmoves. These 
## functions take in the basic move directions, find the actual destination squares which 
## correspond to those move possibilities, and return only those which are legal, by 
## discarding any destination squares which are 1) off the board, 2) already occupied by
## the side to move's pieces, or 3) blocked from accessing (for ray moves) by an intervening
## piece of either side's. 
## Each possible move deemed legal is added to the growing list of possible legal moves, 
## @moveslist.
## Lastly, it is considered whether castling to each side is a legal move, and should
## therefore be added to the list of legal moves. Note that this is a separate determination
## from the $okcastle input!  $okcastle just tells you if previous moves have disallowed
## castling of a particular type at all, not whether castling is legal in the current 
## board position.  The code as is looks like it prevents castling out of check and makes
## sure that all the squares between the king and rook are empty.  However, it does not
## look like it does anything to prevent castling THROUGH check, which is also against 
## the rules. It is somewhat possible that this is handled elsewhere, but I haven't seen 
## it yet if it is. 

## The following (old) comment is no longer accurate, it looks like castling and e.p. 
## captures are now handled.  
# The purpose of this function is to build a subroutine which takes in a list of
# piece positions and outputs, for each piece, a list of possible destination squares
# which would be legal moves (disregarding check, e.p. and castling for now), taking
# into account the locations of all other pieces.
my $switch = 0; ## flag to keep track of whether we have hit the $separator yet, initialized to false
my (@sidetomove_cart,@sidenotmoving_cart); ## declaring empty lists to fill later with piece positions
my $checkflag = shift; ## this takes the first input off the list of inputs and puts it in $checkflag
my $okcastle = shift; ## takes the first (remaining) input off the list of inputs and puts it in $okcastle
my $enpassant = shift; ## etc.
foreach my $pos (@_) { ## @_ is the list of inputs to the function, minus the 3 that have already been shifted off
        if ($pos eq $separator) { ## $pos holds the current input, which is either a piece position or the separator
                $switch = 1; ## we have hit the $separator!
        }
        else {
                if (!$switch) { ## if we haven't hit the separator yet...
                        push @sidetomove_cart, $pos; ## add the piece position to the list of this side's pieces
                }
                else { ## if we have already hit the separator...
                        push @sidenotmoving_cart, $pos; ## add the piece position to the list of the other side's pieces
                }
        }
}
## Originally we had a check here for whether the player is in check, but that involves figuring out
## what moves are available to the other player, which involves calling this function (&makemoveslist)
## Which would mean that &incheck would be called again, which would mean calling &makemoveslist,
## which would call &incheck, which would call &makemoveslist, and so on forever. Obviously, that 
## is a problem.  The solution we settled on was to make it so that &makemoveslist basically ignores
## check when considering move legality, and we then do a second pass through those moves and get rid 
## of those which don't pass an &incheck test if they were actually carried out.  It's not clear that
## this is the best approach, but it does avoid the infinite regress. 

#$checkflag = &incheck($okcastle,$enpassant,@sidetomove_cart,$separator,@sidenotmoving_cart);
#print "\n\nGot into makemoves list \n\n";
#print "@sidetomove_cart \n\n @sidenotmoving_cart\n\n";
my @moveslist = (); # start it as an empty list
# Convert to cartesian coordinates [PNBRQK][1-8][1-8]
#@sidetomove_cart = &alg2cart(@sidetomove_alg);
#@sidenotmoving_cart = &alg2cart(@nottomove_alg);
#print join(" ",(@sidetomove_cart,@sidenotmoving_cart,"\n"));

## This next section is one of the cleverer in the RLM code, if I do say so myself.  Instead of 
## handling the pieces completely separately, there is a main workhorse function &getsinglemove
## which ultimately handles all moves except castling and e.p. captures. 
## &getsinglemove can do this by accepting the starting square, a distance in columns and rows
## to a proposed destination square, and the full list of piece positions for both sides.  
## It returns two outputs, the first being a description of the proposed destination square
## as either "off board", "empty", "enemy", or "friend", and the second being the move string
## if it is a legal move, or undefined if it is not legal by reason of there being a friendly
## piece on the destination or if the destination is off the board. The type of move is completely
## characterized by the distance in columns and rows, so &getsinglemove works equally well for
## knight moves, king moves, or bishop moves.  &getraymove just repeatedly calls &getsinglemove
## with greater and greater distances until a move results in hitting a friendly piece, capturing
## an enemy piece, or going off the board, so bishop, queen, or rook moves are all ultimately
## handled by &getsinglemove. In a slightly trickier fashion, most pawn moves can also be determined
## using &getsinglemove outputs, and that is what &getpawnmoves does. 
## 
## Before we can call &getsinglemove (or &getraymoves or &getpawnmoves), we need to set up the 
## possible move directions, and whether the piece can move in rays or just in single moves, so
## that is what the whole top portion of the foreach loop below does. To understand how dx and 
## dy characterize move directions, consider the example of a rook.  A rook moves from its 
## present location up or down columns or left or right across rows.  Moving up means increasing
## its y coordinate while not changing its x coordinate, represented below by a dy of 1 and a
## dx of 0 (the "d" here is short for "change in", often represented by a delta, hence the "d").
## Moving to the right is increasing the x coordinate while not changing the y coordinate, a dx of
## 1 and a dy of 0.  Likewise moving left is dx=-1 and dy=0, and moving down is dx=0 and dy=-1. If 
## If you look below, these are the 4 pairs of dx and dy values listed for the rook.  They are 
## separated into two lists, but we are going to take each in order, so the first dx value is paired
## with the first dy value, then the second with the second, etc. So the dx,dy values are (0,1), (1,0),
## (-1,0), and (0,-1) for the rook. Correspondingly, for the Bishop, the dx,dy values are (1,1), (1,-1),
## (-1,-1), and (-1,1).  These represent diagonal movements because both x and y are changing at the same
## time; respectively, they are right-and-up, right-and-down, left-and-down, and left-and-up, which are 
## the 4 directions a bishop can move. The king and queen can move in all the directions of both the rook 
## and the bishop, so they have 8 pairings, and the only difference between them is that the queen can 
## move in rays, whereas the king moves just a single step. Knights also have 8 possible moves, but they 
## take two steps in one direction and then one in a different direction.  No problem, we just have to 
## construct the 8 legal (dx,dy) pairings for knights. 
# Define move patterns
# Loop over pieces
my (@dx,@dy,$movetype);
foreach my $curpiecepos (@sidetomove_cart) {
        my ($piecetype,$curx,$cury) = split(//,$curpiecepos); ## split B34 (a bishop on c4), e.g. into 'B','3','4'
        #print "$curpiecepos $curx $cury\n\n";
        #$curpiece =~ /^[PNBRQK]/i;
        #$piecetype = $&;
        if ($piecetype =~ /r/i) { # Rook
                @dx = (0,1,-1,0);
                @dy = (1,0,0,-1);
                $movetype = "ray";
        }
        elsif ($piecetype =~ /b/i) { # Bishop
                @dx = (1,1,-1,-1);
                @dy = (1,-1,-1,1);
                $movetype = "ray";
        }
        elsif ($piecetype =~ /q/i) { # Queen = R+B
                @dx = (0,1,-1,0,1,1,-1,-1);
                @dy = (1,0,0,-1,1,-1,-1,1);
                $movetype = "ray";
        }
        elsif ($piecetype =~ /n/i) { # Knight
                @dx = (-1,1,2,2,1,-1,-2,-2);
                @dy = (2,2,1,-1,-2,-2,-1,1);
                $movetype = "single";
        }
        elsif ($piecetype =~ /k/i) { # King (I actually forgot about the king!!)
                @dx = (-1,0,1,1,1,0,-1,-1);
                @dy = (1,1,1,0,-1,-1,-1,0);
                $movetype = "single"; # I should probably just say "single" for these
        }
        elsif ($piecetype =~ /p/i) { # Pawn
                # Very complicated, deal with later ## was dealt with, this comment is out of date
                $movetype = "pawn";
        }
        else {
                print "$curpiecepos \n";
                die "Unknown piece type \"$piecetype\" \n"; ## this error kills the game if somehow a piece got onto the board which was not represented by an upper or lowercase p,k,q,r,b, or n. 
        } # end of if structure setting up rays and movement types
        # Now call the appropriate routines for making the lists of moves
        my ($raynum,@addmoves);
        if ($movetype eq "ray") { # Move along a ray
                for ($raynum=0; $raynum<= $#dx; ++$raynum) { ## loops over the dx,dy pairings
                        @addmoves = &getraymoves($piecetype,$curx,$cury,$dx[$raynum],$dy[$raynum],@sidetomove_cart,$separator,@sidenotmoving_cart);
                        push @moveslist, @addmoves;  ## add returned moves to the @moveslist output list
                }
        }
        elsif ($movetype eq "single") { # Take single moves in each direction
                for ($raynum=0; $raynum<= $#dx; ++$raynum) { ## loop over the dx,dy pairings
                        my ($squaretype,$move) = &getsinglemove($piecetype,$curx,$cury,$dx[$raynum],$dy[$raynum],@sidetomove_cart,$separator,@sidenotmoving_cart);
                        if ($squaretype eq "enemy" or $squaretype eq "empty") { #add the move
                                push @moveslist, $move;
                        }
                }
        }
        elsif ($movetype eq "pawn") {   # Move like a pawn; forward and diagonal to capture, forward if empty,
                                        #forward two if both empty and on original square, promote if you get to the end
                                        # worry about adding en passant later ## This was handled, I believe
                #print "got to pawn moves \n";
                @addmoves = &getpawnmoves($enpassant,$piecetype,$curx,$cury,@sidetomove_cart,$separator,@sidenotmoving_cart);
                push @moveslist, @addmoves;
        } ## TODO: we should probably add an else clause here to catch possible errors in $movetype
} # end of piece loop

## TODO: we should decide whether $checkflag should be used at all in this function.  We are doing
## more complex check verification later, and &incheck is lying to &makemoveslist by using a pretend
## $checkflag, so it's not clear that this conditional is actually helpful.
# See whether castling should be added to movelist
if (not $checkflag) ## castling out of check is illegal, so only consider castling if you don't think you're in check
{       my ($square1,$square2,$square3,@castlechar,$dum); ## setting up variables to be used within this area
        #print "Welcome to the world of not being in check!\n";
        if ($sidetomove_cart[0] eq ucfirst($sidetomove_cart[0])) ## if your pieces are capitalized, you're White
        {       #print "In case you didn't know, you're playing white\n";
                @castlechar = ("K","Q"); #white moving  ## these are the characters to look for in $okcastle
                #print "okcastle is $okcastle\n";
                if ($okcastle =~ /$castlechar[0]/)# =~ /$okcastle/)   # castle kingside? ## true if $okcastle contains "K"
                {       #print "Welcome to the world of being white and castling kingside\n";
                        if (&onlist("K51",@sidetomove_cart) and &onlist("R81",@sidetomove_cart)) ## checks if the king is on e1 and rook is on h1
                        {       #print "plus having your king and rook on the right squares\n";
                                ($square1,$dum) = &getsinglemove("K",5,1,1,0,@sidetomove_cart,$separator,@sidenotmoving_cart); ## returns "empty" if f1 is empty
                                ($square2,$dum) = &getsinglemove("K",5,1,2,0,@sidetomove_cart,$separator,@sidenotmoving_cart); ## returns "empty" if g1 is empty
                                #print "and your square1 is $square1 while your square2 is $square2\n";
                                if ($square1 eq "empty" and $square2 eq "empty")
                                {       ## At this point, we've verified that the FEN says kingside castling is OK,
                                        ## that the King and Rook are on the proper squares, and that the squares between them
                                        ## are empty. 
                                        push @moveslist, "o-o"; ## add kingside castling to output @moveslist
                                }
                        }
                }
                if ($okcastle =~ /$castlechar[1]/)# =~ /$okcastle/)   # castle queenside? ## Exact same approach for queenside...
                {       #print "Welcome to the world of being white and castling queenside\n";
                        if (&onlist("K51",@sidetomove_cart) and &onlist("R11",@sidetomove_cart))
                        {       ($square1,$dum) = &getsinglemove("K",5,1,-1,0,@sidetomove_cart,$separator,@sidenotmoving_cart);
                                ($square2,$dum) = &getsinglemove("K",5,1,-2,0,@sidetomove_cart,$separator,@sidenotmoving_cart);
                                ($square3,$dum) = &getsinglemove("K",5,1,-3,0,@sidetomove_cart,$separator,@sidenotmoving_cart);
                                if ($square1 eq "empty" and $square2 eq "empty" and $square3 eq "empty")
                                {       push @moveslist, "o-o-o";
                                }
                        }
                }
        }
        else ## This is if black is moving instead of white.  There's a lot of duplicated code here that we should be able to refactor away
        {       @castlechar = ("k","q");  #black moving
                if ($okcastle =~ /$castlechar[0]/)# =~ /$okcastle/)   # castle kingside?
                {       if (&onlist("k58",@sidetomove_cart) and &onlist("r88",@sidetomove_cart))
                        {       ($square1,$dum) = &getsinglemove("k",5,8,1,0,@sidetomove_cart,$separator,@sidenotmoving_cart);
                                ($square2,$dum) = &getsinglemove("k",5,8,2,0,@sidetomove_cart,$separator,@sidenotmoving_cart);
                                if ($square1 eq "empty" and $square2 eq "empty")
                                {       push @moveslist, "o-o";
                                }
                        }
                }
                if ($okcastle =~ /$castlechar[1]/)# =~ /$okcastle/)   # castle queenside?
                {       if (&onlist("k58",@sidetomove_cart) and &onlist("r18",@sidetomove_cart))
                        {       ($square1,$dum) = &getsinglemove("k",5,8,-1,0,@sidetomove_cart,$separator,@sidenotmoving_cart);
                                ($square2,$dum) = &getsinglemove("k",5,8,-2,0,@sidetomove_cart,$separator,@sidenotmoving_cart);
                                ($square3,$dum) = &getsinglemove("k",5,8,-3,0,@sidetomove_cart,$separator,@sidenotmoving_cart);
                                if ($square1 eq "empty" and $square2 eq "empty" and $square3 eq "empty")
                                {       push @moveslist, "o-o-o";
                                }
                        }
                }
        }
}
# Convert output moves back to algebraic notation
# Maybe we're just going to use the cartesian, so I'll leave that out for now
return @moveslist     # doesn't need to be returned, because it's global, but it doesn't hurt I guess
## Comment on line above is a lie!  @moveslist is not global, and does need to be returned!
} # end of makemoveslist
#===============================================================================
sub getraymoves
{
# strategy is to use getsinglemove repeatedly along a ray until it fails, pushing
# all valid moves onto moveslist
my ($piecetype,$x,$y,$orig_dx,$orig_dy,@restoflist) = @_;   # all the inputs to getsinglemove are going to be the same after $y, so they don't need to be broken up
my ($dx,$dy) = ($orig_dx,$orig_dy);
my $keepgoing = 1; # intialize the looping flag
#print "$piecetype $x $y @restoflist \n";
#die "just before while";
my @moveslist;
while ($keepgoing) {
        my ($squaretype,$move)=&getsinglemove($piecetype,$x,$y,$dx,$dy,@restoflist);
        if ($squaretype eq "enemy" || $squaretype eq "empty")  {
                # add the move to moveslist
                push @moveslist, $move;
                # Originally, I changed $x and $y, but I'm now I'm updating $dx and $dy
                $dx = $dx + $orig_dx;
                $dy = $dy + $orig_dy;
                if ($squaretype eq "enemy") {
                        $keepgoing = undef;
                }
        }
        else {
                # move didn't work, stop looking down this ray
                $keepgoing = undef;
        }
}
return @moveslist
} # end of getraymoves
#===============================================================================
sub getpawnmoves
{
# pawns are hard, I'll deal with them NOW!!
# OK, pawns can always go forward one square if that square is empty. They can go forward
# two squares if on their original square and both squares are empty.  They can move forward
# and diagonally only if those squares are occupied by enemy pieces (or if capturing en passant!)
# inputs are ($piecetype,$curx,$cury,@sidetomove_cart,"side not moving is after this",@sidenotmoving_cart)
my ($enpassant,$ptype,$x,$y,@restoflist) = @_;
my ($color,$promoting,$promotemove,@pawnmoveslist,@dx,@dy,@promote);
if ($ptype eq "P") {
        $color = "white";
        @dx = (-1,1,0,0);
        @dy = (1,1,1,2);
        @promote = ("=Q","=R","=B","=N");
}
elsif ($ptype eq "p") {
        $color = "black";
        @dx = (-1,1,0,0);
        @dy = (-1,-1,-1,-2);
        @promote = ("=q","=r","=b","=n");
}
# Check if moving would lead to promotion
if ($y+$dy[0]==1 || $y+$dy[0]==8) {
        $promoting = 1;
}
else {
        $promoting = 0;
}
# Attack to the left
my ($squaretype,$move) = &getsinglemove($ptype,$x,$y,shift @dx, shift @dy,@restoflist);
if ($squaretype eq "enemy"){
        push @pawnmoveslist, $move;
}
# Attack to the right
($squaretype,$move) = &getsinglemove($ptype,$x,$y,shift @dx, shift @dy,@restoflist);
if ($squaretype eq "enemy"){
        push @pawnmoveslist, $move;
}

# Check for en passant captures
$move = &enpassant($ptype,$x,$y,$dy[0],$enpassant);
push @pawnmoveslist, $move if defined($move);

my @moveslist;
# Move forward one square (and check on two squares)
($squaretype,$move) = &getsinglemove($ptype,$x,$y,shift @dx, shift @dy,@restoflist);
#print "$color $x $y $squaretype $move \n";
if ($squaretype eq "empty"){
        push @pawnmoveslist, $move;

        #Now allow the move to two squares if on 2nd rank (white) or 6th rank (black)
        #But first check if it's empty
        ($squaretype,$move) = &getsinglemove($ptype,$x,$y,shift @dx, shift @dy,@restoflist);
        #print "$squaretype";
        if  ($squaretype eq "empty") {
                #print "$color $y";
                #now check if you're on the correct rank
                if (($y==2 && $color eq "white") || ($y==7 && $color eq "black")) {
                        push @moveslist, $move;
                }
        }
}

if ($promoting){
        # loop over the moves in pawnmoveslist
        foreach my $pmove (@pawnmoveslist) {
                foreach my $pto (@promote) {
                        $promotemove = $pmove . $pto;
                        push @moveslist, $promotemove;
                }
        }
}
else {
        foreach my $move (@pawnmoveslist) {
                push @moveslist, $move;
        }
}
return @moveslist;
} # end of getpawnmoves
#===============================================================================
sub enpassant
{
my ($ptype,$x,$y,$dy,$enpassant) = @_;
if ($enpassant eq "-")
{       return undef;
}
#print "$enpassant\n";
my ($file,$rank) = split(//,$enpassant);
my ($newx,$newy,$epmove);
my %a2c = ("a",1,"b",2,"c",3,"d",4,"e",5,"f",6,"g",7,"h",8);
$file = $a2c{$file}; #convert to cartesian file number
######print "Enpassant is $enpassant\n";
#die "Error: $enpassant / $file / $rank" unless defined $file;
if (($y+$dy) == $rank)
{       if ($x-1 == $file)
        {       $newx = $x-1;
                $newy = $y+$dy;
                $epmove = $ptype.$x.$y."x".$newx.$newy." e.p.";
        }
        elsif ($x+1 == $file)
        {       $newx = $x+1;
                $newy = $y+$dy;
                $epmove = $ptype.$x.$y."x".$newx.$newy." e.p.";
        }
        else
        {       $epmove = undef;
        }
}
else
{       $epmove = undef;
}
return $epmove;
}# end of enpassant
#===============================================================================
sub getsinglemove
{ ## This subroutine has two outputs. The second one is either the move string 
  ## for a single move or "undefined" if the move would be off the board or onto
  ## a friendly piece.  The first output is a string describing the square type 
  ## of the proposed destination square, classifying it as either "empty", "friend"
  ## (if occupied by a friendly piece), "enemy" (if occupied by an enemy piece), or 
  ## "off board" if unoccupied. The inputs are, in order, the piece (e.g. "B"), the 
  ## current x coord of the piece (e.g. 3), the current y coord of the piece (e.g. 1),
  ## the x column change to get to the proposed destination square (e.g. 3 to move 3 
  ## columns to the right), the y row change to get to the proposed destination square 
  ## (e.g. 3 to move 3 rows up), and then all of the friendly pieces, the separator, 
  ## and all of the enemy pieces.
# find the square which is dx dy away, and if it is on the board and unoccupied, then it's a legal move.
# if it is off the board or occupied by a friendly piece, then it's not a legal move.
# if it's an enemy piece, then its a legal capture
# inputs are   $piecetype,$curx,$cury,$dx[$raynum],$dy[$raynum],@sidetomovepos,"side not moving is after this",@sidenotmovingpos
# outputs should be the destination square type (one of empty, off board, friend, or enemy) and the move (e.g. Bh8, or B88 depending on formatting)
#process inputs
my ($ptype,$x,$y,$dx,$dy,@poslist)= @_; ## unpack inputs
my $newx = $x+$dx; ## figure out x coordinate of destination square
my $newy = $y+$dy; ## y coordinate of destination square
my $newpos = $newx . $newy; ## combine the two (this is now a two digit string)
# Short circuit the checking if the new square is off the board
if ($newx > 8 || $newx < 1 || $newy < 1 || $newy > 8) {
        # off the board
        #my @out = ("off board", undef );
        return ("off board", undef );
}
#divide up poslist
my $switchtonotmoving = 0; ## 0 until $separator is hit, 1 afterward
my (@sidetomovexy, @sidenotmovingxy); ## declare new lists to hold just the XY locations of the pieces
#print "Poslist is: @poslist \n";
# loop over positions in list, placing each into the moving or not moving list
my (@splitpos,$posy,$posx,$posxy);
foreach my $pos (@poslist) { ## poslist holds all piece positions, separated by $separator
        if ($pos eq $separator) {
                $switchtonotmoving = 1; ## mark that we've passed the $separator
        }
        else { ## $pos holds a piece position (like "B31" for a white Bishop on c1)
                # just want the board position, not the piece
                @splitpos = split(//,$pos); ## split piece position into individual characters ("B","3","1")
                $posy = pop @splitpos; ## pop takes the last element off the list, which is the y coord
                $posx = pop @splitpos; ## pops the next element off the end of the list, which is now the x coord
                $posxy = $posx . $posy; ## re-assemble into a 2-character string, (like "31")
                if ($switchtonotmoving) { ## if we've hit the separator already...
                        push @sidenotmovingxy, $posxy; ## Add xy location to list of adversary occupied squares
                }
                else { ## if we haven't hit the separator yet...
                        push @sidetomovexy, $posxy; ## Add xy location to list of friend-occupied squares
                }
        }
}
## $newpos holds the proposed destination square xy.  The next conditional
## series checks whether that proposed destination square is on the list of
## occupied friendly squares, on the list of occupied enemy squares, or is
## on neither list (in which case it is empty).  If the square is friend-
## occupied, then you can't move there.  If the square is enemy-occupied,
## you can move there, and the move is a capture (should have an "x" in it).
## If the square is empty, you can move there and the move is not a capture.
## &onlist is a subroutine which returns true if the first input matches any
## of the rest of the inputs. 
# now lists are constructed, next thing is to check whether there newpos one either list
my ($squaretype, $move);
if (&onlist($newpos,@sidetomovexy)) { 
        $squaretype = "friend";
        $move = undef;
}
elsif (&onlist($newpos,@sidenotmovingxy)) {
        $squaretype = "enemy";
        $move = $ptype.$x.$y . "x" . $newpos;
}
else { # empty board location
        $squaretype = "empty";
        $move = $ptype.$x.$y . $newpos;
     }
return ($squaretype,$move)  ## return the square type and move.  
## If the square type is "off board" or "friend", $move will be undefined,
## otherwise, it will hold the string representing the move (e.g. "B31x64" for Bc1xf4)
} # end of getsinglemove
#===============================================================================
sub garglelegalcastle
{
my @legalmoveslist = @_;
my $removekcastle = 0;
my $removeqcastle = 0;
my @trulylegal;
if (&onlist("o-o",@legalmoveslist))
{       #$removekcastle = 1 unless (&onlist("K5161",@legalmoveslist) or &onlist("k5868",@legalmoveslist));
        $removekcastle = 1 unless (&onlist("Ke1f1",@legalmoveslist) or &onlist("ke8f8",@legalmoveslist));
}
if (&onlist("o-o-o",@legalmoveslist))
{       $removeqcastle = 1 unless (&onlist("Ke1d1",@legalmoveslist) or &onlist("ke8d8",@legalmoveslist));
}
foreach (@legalmoveslist)
{       push @trulylegal, $_ unless (($removekcastle and ($_ eq "o-o")) or ($removeqcastle and ($_ eq "o-o-o")))
}
return @trulylegal;
}
#===============================================================================
sub onlist
{
# this subroutine should check whether the first input is repeated anywhere in the rest
# of the inputs; whether it is "on the list".

my ($val,@list) = @_;

foreach my $listval (@list) {
        if ($val eq $listval) {
                return 1;
        }
}
# if you never hit a match, then there's no match!
return undef;
} # end of onlist subroutine
#===============================================================================
sub cart2alg
{
# The purpose of this subroutine is to convert any input positions from cartesian coordinates
# to algebraic notation
# Updated to take moves of the form Bg1f2
# Make a list where the index converts to the letter
my @c2a = (0,"a","b","c","d","e","f","g","h");
my @poslist = @_;
my @out;
foreach my $pos (@poslist){
        # substitute the appropriate letter for the cartesian coord.
        # for example, B14 should become Ba4
        #$pos =~ s/([A-Z|a-z]x?)([1-8])([1-8]=?[A-Z|a-z]?)/$1$c2a[$2]$3/; #old version for moves like Bg1
        $pos =~ s/([PNBRQKpnbrqk])(([1-8])([1-8]))?(x?)([1-8])([1-8])(=?[NBRQnbrq]?)/$1$c2a[$3]$4$5$c2a[$6]$7$8/;  # new version for moves like Bf2g1
        $pos =~ s/0//g; # if the new version is passed an old-style move, a 0 appears in the substitution, this line just removes any zeros
        #$poscopy =~ /([A-Z|a-z])(([1-8])([1-8]))?(x?)([1-8])([1-8])(=?[A-Z|a-z]?)/;
        #print "matches were: \n$1\n$2\n$3\n$4\n$5\n$6\n$7\n$8\n";
        #print "$1$c2a[$3]$4$5$c2a[$6]$7$8\n\n";
        push @out, $pos;
} # end of foreach
return wantarray ? @out : $out[0]; # if a scalar is wanted, it probably means you only passed in one move which you want back out...
} # end of cart2alg
#===============================================================================
sub alg2cart
{
# The purpose of this subroutine is to convert any positions from algebraic notation to cartesian
# coordinates
# Updated to make moves like Bg1f2
my %a2c = ("a",1,"b",2,"c",3,"d",4,"e",5,"f",6,"g",7,"h",8);
my @poslist = @_;
my @out;
foreach my $pos (@poslist) {
        # Substitute the appropriate number for the file lettter
        #$pos =~ s/([A-Z|a-z])([a-h])([1-8].*)/$1$a2c{$2}$3/;
        $pos =~ s/([PNBRQKpnbrqk])([a-h])([1-8])(x?)(([a-h])([1-8]))?(.*)/$1$a2c{$2}$3$4$a2c{$6}$7$8/;
        #$pos =~ /([A-Z|a-z])([a-h])([1-8])([a-h])([1-8])/;
        #$pos =~ /([A-Z|a-z])([a-h])([1-8])(([a-h])([1-8]))/;
        #print "matches were: \n$1\n$2\n$3\n$4\n$5\n$6\n$7\n";
        push @out, $pos;
} # end of foreach
return wantarray ? @out : $out[0]; # if a scalar is wanted, it probably means you only passed in one move which you want back out...
} # end of alg2cart
#===============================================================================
sub cart2ind
{
my ($x,$y) = @_;
my $ind = $x+(8-$y)*8-1;
return $ind;
}
#===============================================================================
sub writeresult
{
my ($result,$tmpfilename) = @_;
my $resultstr;
if ($result eq "draw")
{       $resultstr = "1/2-1/2";
}
elsif ($result eq "white wins")
{       $resultstr = "1-0";
}
elsif ($result eq "black wins")
{       $resultstr = "0-1";
}
else
{       die "Result $result not understood by writeresult subroutine";
}
# resultstr needs to get written at the end of the movelist and in the Result tag
print TMPPGNHANDLE " $resultstr\n";
close TMPPGNHANDLE;
open TMPPGNHANDLE, "<$tmpfilename";  #closes, then reopens the file
my $terminator = $/;   #stores the file record separator
undef $/;   #undefines the file record separator
my $pgn = <TMPPGNHANDLE>;  # gets the whole file
close TMPPGNHANDLE;
$pgn =~ s/(\[Result ")\*/$1$resultstr/;
print REALPGNHANDLE "$pgn";
close REALPGNHANDLE;
unlink ($tmpfilename); #delete temporary file
}#end of writeresult
#===============================================================================
sub sillytalk
{       my @exclam = ('Well!','See here!','I see!','Err...','Oh!','Goodness!','Heavens!','My oh my!','Jiminy!','Gracious me!','Holy snickerdoodles!','Sweet spirit of Elsie the Cow!','Blimey!','Shiver me timbers!','Great balls of felt!');
        my @subject = ('Rats','Crickets','Chimps','Crocodiles','Elephants','Bats', 'Armadillos','Martians','Minions of the underworld','Michael Jackson\'s relatives','Many tiny Englishmen','Midges','A herd of flea-ridden camels','Your sister\'s college roommate\'s third cousin once removed','The ghost of your childhood hamster');
        my @verb = ('slam dunk','mame lame, then blame','lug a plank and spank','chomp-chomp-chomp','smack the heck out of','wreak havoc on','failed to notice','just up and telephoned','body-slammed','tripped','spun around and zoomed','gyrated wildly','spooked','smelled','zoomed');
        my @object = ('me!', 'you!', 'sweet Jesus!', 'my pants!', 'yer\' pants!', 'all of Zimbabwe!','Danny\'s fanny!','Mike\'s tyke!','a bunch of hypocrites!','themselves!','your neighbors','your cousin's pet','that one guy who is always wandering around talking to himself.  You know the one I\'m talking about.');
        my @newline = ("\n");
        my $sentence = &say(\@exclam,\@subject,\@verb,\@object,\@newline);
}
#===============================================================================
sub wisdomtalk
{# when the engine is moving, in place of I in my infinite wisdom
my @put = ("Put","Gently place","Stick","Jam","Put your back into it, and squeeze","Insert","Ram repeatedly","Slide");
my @this = ("this","THIS","as much of this as you can","some of this","a bit of this","anything resembling this","a bunch of this","more than some but less than a lot of this","a skosh of this","all of this and more of this","just a teensy bit of this");
my @prep = ("in","on","underneath","somewhere in the vicinity of","twenty paces due east from","inside","in the depths of","beside","next to", "at the appropriate time, upon", "betwixt Cleveland and","sort of around","in eyesight of","in earshot of","in arm\'s reach of");
my @possess = ("your","your","your","Bob's","your King's","the King's","Ben Franklin's","Bobby Fischer's","Kermit the Frog's","a bearded man's","your mother's","a monkey's uncle's","... You remember that fellow you met yesterday? ... His","any random person's","your cousin\'s","your uncle\'s best friend\'s cat\'s");
my @object = ("pipe","car","mailbox","polka-dotted underwear","toupee","cubicle","hot rod","troubled conscience","toothbrush","pants","left nostril","litter box","mailbox","bomb shelter","attic","shed");
my @and = ("and");
my @verb = ("smoke","eat","consider","become","pursue a vendetta against","make war upon","frighten","be frightened by","moo at","dance a jig around","emblazon your initals on","make a gift of","bequeath","stare at","glare at","hold a mighty grudge against","shake your booty at");
my @it = ("it!\nRLM Move: ");
my $sentence = &say(\@put,\@this,\@prep,\@possess,\@object,\@and,\@verb,\@it);
}
#===============================================================================
sub prompttalk
{
my @goahead = ("Go ahead,","I triple-dog dare you,", "Hurry up and","You've got to","I wonder if I could trouble you to","You know, the game can't go on until you","The Queen of England commands you to","For once in your life, why don't you","It's time to","Come on now,","It would be disappointing if you didn't","All the chess faeries will rejoice if you","Hey,","Its about time for you to","For Pete\'s sake (why is about Pete anyway?  What about for Jim's sake?), c'mon already");
my @adverbs = ("randomly","carefully","provocatively","boldly","timidly","rapidly","profoundly","uncompromisingly","shut up and","resign or","perspicaciously",",in a manner agreeable to you,","less carefully","hurriedly","charmingly","speedily","maliciously");
my @verb = ("make","choose","pick","select","decide on","opt for","commit to");
my @thingy = ("your move!\n");
my $sentence = &say(\@goahead,\@adverbs,\@verb,\@thingy);
}
#===============================================================================
sub say
{#say will receive an array of references to arrays
my @sentence;
foreach (@_)
{       push @sentence, $$_[sprintf("%i",rand($#$_+1))];
}
my $sentence = join(" ",@sentence);
$sentence =~ s/ ,/,/g;
$sentence =~ s/,,/,/g;
print $sentence;
return $sentence;



#Bryan commenting here.  Learning github and terminal.  Cloned from github, opened the file in vim, somehow managed to start typing even though it didn't let me at first, and now I'm going to try and commit this change back to github.

