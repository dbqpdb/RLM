#!/usr/local/bin/perl
use warnings;
use strict;
use vars '$separator', '$userside','$enginename';
use Benchmark;
$enginename = "RLMv0.96";
$separator = "turkeyblurp"; # I have no idea why this is here :)
print "Welcome to the RLM Engine. Would you like to play a game of chess? (yep/nope): ";
my $input = <>;
my ($fen, $correct);
if($input =~ /y/i)
{       print "\nWould you like to play from the normal starting position? (yep/nope): ";
        $input = <>;
        if($input =~ /y/i)
        {       $fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
        }
        else
        {       print "\nOkay. Please enter the FEN for the position from which you would like to play:\n";
                chomp($fen = <>);
                if(&validfen($fen))
                {       print &showboard($fen)."\nIs this correct? (yep/nope): ";
                        chomp($correct = <>);
                }
                while(($correct =~ /n/i) or (!&validfen($fen)))
                {       if(!&validfen($fen))
                        {       print "That's not a valid FEN. Try again or type \"start\" to begin at the starting position.\n";
                        }
                        else
                        {       print "Okay. Try again with another FEN or type \"start\" to begin at the starting position.\n";
                        }
                        chomp($fen = <>);
                        if($fen =~ /s/i)
                        {       $fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
                        }
                        if(&validfen($fen))
                        {       print &showboard($fen)."\nIs this correct? (yep/nope): ";
                                chomp($correct = <>);
                        }
                }
        }
}
else
{       print "In that case, I suggest twiddling your thumbs until you ARE ready to play chess. Good day to you!";
        exit;
}
print "\nWould you like to play the white side or the black side?\n";
$input = <>;
if($input =~ /w/i)
{       $userside = "w";
        print "\nWonderful, I enjoy playing black!\n"
}
elsif($input =~ /b/i)
{       $userside = "b";
        print "\nWicked cool! I simply adore playing white!\n";
}
else
{       print "Aw, to heck with you, I'll play myself!!\n";
        $userside = "none";
}
print "Should I record the moves of this game in a PGN file? (yep/nope):";
$input = <>;
my $pgnflag = 0;
my ($filename,$username,$site,$white,$black,$date,$tmpfilename);
my $setupflag = 0;
if ($input =~ /y/i)
{       print "What file would you like to record to?\nFilename: ";
        chomp($filename = <>);
        if ($filename !~ /\.\w+/)
        {       $filename = $filename . ".pgn";
        }
        $tmpfilename = "$filename.tmp";
        open TMPPGNHANDLE, ">$tmpfilename";
        open REALPGNHANDLE, ">>$filename";
        unless ($userside eq "none")
        {       print "What do they call you?\nName: ";
                chomp($username = <>);
        }
        print "Where can I find you?\nCurrent Location: ";
        chomp($site = <>);
        print TMPPGNHANDLE "\n\n[Event \"RLM Game\"]\n[Site \"$site\"]\n";
        my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime(time);
        $date = join(".",$year+1900,$mon+1,$mday);
        print TMPPGNHANDLE "[Date \"$date\"]\n[Round \"-\"]\n";
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
        print TMPPGNHANDLE "[White \"$white\"]\n[Black \"$black\"]\n";
        if ($fen ne "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        {       print TMPPGNHANDLE "[SetUp \"1\"]\n[FEN \"$fen\"]\n";
                $setupflag = 1;
        }
        print TMPPGNHANDLE "[Result \"*\"]\n";
        $pgnflag = 1;
}

        

my $gameover = 0;
print "\nWhen entering moves during the game, please indicate the piece to move, its origin square, and destination square. You may indicate a capture (with an \"x\") or check (with a \"+\") if you'd like, for example the following are all valid moves:\nBc1f4, e2e4, pc2c4, qa1xh8+, g7g8=q\n\n";
print &showboard($fen);
my $usermove;
my $move;
my ($okcastle,$enpassant,$movessince,$totalmoves,$side2move,@restofstuff) = &processfen($fen);
if ($pgnflag and $setupflag and $side2move eq "b")
{       print TMPPGNHANDLE "$totalmoves. ... ";
}

while(!$gameover)
{
my $movestarttime = new Benchmark;
#my $board = showboard($fen);
#print "Old Position:\n\n$board\n\n";
#my ($okcastle,$enpassant,$movessince,$totalmoves,$side2move,@restofstuff) = &processfen($fen);
if ($movessince >= 100)
{       print "The game is drawn because both sides have just been running around like idiots and more than 50 moves have elapsed without a pawn move or capture, for crying out loud!\n\n";
        if ($pgnflag)
        {       &writeresult("draw",$tmpfilename,$filename);
        }
        exit;
}
my $checkflag = &incheck($okcastle,$enpassant,@restofstuff);
## Call the subroutine which makes the moves list!!
my @curmoveslist = &makemoveslist($checkflag,$okcastle,$enpassant,@restofstuff);
#print "Current moves list is: @curmoveslist\n\n";
my @cmlalg = &cart2alg(@curmoveslist);
#print "Current moves are: \n@cmlalg\n\n";
my @legalmoveslist;
foreach my $move (@cmlalg){ #(@curmoveslist){
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
sub validfen
{
return 1;
}
#===============================================================================
sub movegrinder
{
my $move = shift;
if ($move =~ /(o-o(?:-o)?)/i)
{        return lc($1);
}
my $editmove;
$move =~ s/^(\w\d)/P$1/;
$move =~ /(\w)?(\w\d)x?(\w\d)(=[bnrqBNRQ])?/;
my $piece = $1;
my $startsquare = $2;
my $endsquare = $3;
my $queen;
if(defined $4)
{       $queen=$4;
}else{
        $queen="";
}
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
sub processfen
{
#use warnings;
# print "Welcome to Mike and Dan's RLM engine. Please enter the complete FEN of the position from which you would like to play. Don't forget to put spaces between the six data sets. Use a dash for an empty castling or en passant entry. If you would like to play from the starting position, just type \"start\". Enjoy!\n\n\n";
# $fen = <>;
# chomp $fen;
# $fen =~ s|\s+| |g;
my ($fen) = @_;#"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
# split up the FEN into the various data sets
my @fenar = (split " ", $fen);
my ($poslist, $side2move, $okcastle, $enpassant, $movessince, $totalmoves) = @fenar;
#print "$poslist\n$side2move\n$okcastle\n$enpassant\n$movessince\n$totalmoves\n";
$poslist =~ s|/||g;
#print "$poslist\n";
$poslist =~ s|(\d)|0 x $1|eg;
#print "$poslist\n";
my @possplit = (split "", $poslist);
#print "@possplit \n\n";
my @cart = ();
my ($row,$col,$pos);
for($row = 8; $row > 0; $row--) {
        for($col = 1; $col < 9; ++$col) {
                $pos = $col.$row;
                push @cart, $pos;
        }
}
my (@whitepos,@blackpos) = ();
my $posnum;
for ($posnum=0; $posnum<64; $posnum++){
        if ($possplit[$posnum] =~ /[A-Z]/){
                push @whitepos, $possplit[$posnum].$cart[$posnum];
        }
        elsif ($possplit[$posnum] =~ /[a-z]/){
                push @blackpos, $possplit[$posnum].$cart[$posnum];
        }
}
#print "@whitepos\n\n@blackpos";
my (@side2move,@adversary);
if ($side2move =~ /w/i) {
        @side2move  = @whitepos;
        @adversary = @blackpos;
}
else {
        @side2move = @blackpos;
        @adversary = @whitepos;
}
return ($okcastle,$enpassant,$movessince,$totalmoves,$side2move,@side2move,$separator,@adversary)
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
{
# The purpose of this function is to build a subroutine which takes in a list of
# piece positions and outputs, for each piece, a list of possible destination squares
# which would be legal moves (disregarding check, e.p. and castling for now), taking
# into account the locations of all other pieces.
my $switch = 0;
my (@sidetomove_cart,@sidenotmoving_cart);
my $checkflag = shift;
my $okcastle = shift;
my $enpassant = shift;
foreach my $pos (@_) {
        if ($pos eq $separator) {
                $switch = 1;
        }
        else {
                if (!$switch) {
                        push @sidetomove_cart, $pos;
                }
                else {
                        push @sidenotmoving_cart, $pos;
                }
        }
}
#$checkflag = &incheck($okcastle,$enpassant,@sidetomove_cart,$separator,@sidenotmoving_cart);
#print "\n\nGot into makemoves list \n\n";
#print "@sidetomove_cart \n\n @sidenotmoving_cart\n\n";
my @moveslist = (); # start it as an empty list
# Convert to cartesian coordinates [PNBRQK][1-8][1-8]
#@sidetomove_cart = &alg2cart(@sidetomove_alg);
#@sidenotmoving_cart = &alg2cart(@nottomove_alg);
#print join(" ",(@sidetomove_cart,@sidenotmoving_cart,"\n"));
# Define move patterns
# Loop over pieces
my (@dx,@dy,$movetype);
foreach my $curpiecepos (@sidetomove_cart) {
        my ($piecetype,$curx,$cury) = split(//,$curpiecepos);
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
                # Very complicated, deal with later
                $movetype = "pawn";
        }
        else {
                print "$curpiecepos \n";
                die "Unknown piece type \"$piecetype\" \n";
        } # end of if structure setting up rays and movement types
        # Now call the appropriate routines for making the lists of moves
        my ($raynum,@addmoves);
        if ($movetype eq "ray") { # Move along a ray
                for ($raynum=0; $raynum<= $#dx; ++$raynum) {
                        @addmoves = &getraymoves($piecetype,$curx,$cury,$dx[$raynum],$dy[$raynum],@sidetomove_cart,"turkeyburp",@sidenotmoving_cart);
                        push @moveslist, @addmoves;
                }
        }
        elsif ($movetype eq "single") { # Take single moves in each direction
                for ($raynum=0; $raynum<= $#dx; ++$raynum) {
                        my ($squaretype,$move) = &getsinglemove($piecetype,$curx,$cury,$dx[$raynum],$dy[$raynum],@sidetomove_cart,"turkeyburp",@sidenotmoving_cart);
                        if ($squaretype eq "enemy" or $squaretype eq "empty") { #add the move
                                push @moveslist, $move;
                        }
                }
        }
        elsif ($movetype eq "pawn") {   # Move like a pawn; forward and diagonal to capture, forward if empty,
                                        #forward two if both empty and on original square, promote if you get to the end
                                        # worry about adding en passant later
                #print "got to pawn moves \n";
                @addmoves = &getpawnmoves($enpassant,$piecetype,$curx,$cury,@sidetomove_cart,"turkeyburp",@sidenotmoving_cart);
                push @moveslist, @addmoves;
        }
} # end of piece loop
# See whether castling should be added to movelist
if (not $checkflag)
{       my ($square1,$square2,$square3,@castlechar,$dum);
        #print "Welcome to the world of not being in check!\n";
        if ($sidetomove_cart[0] eq ucfirst($sidetomove_cart[0]))
        {       #print "In case you didn't know, you're playing white\n";
                @castlechar = ("K","Q"); #white moving
                #print "okcastle is $okcastle\n";
                if ($okcastle =~ /$castlechar[0]/)# =~ /$okcastle/)   # castle kingside?
                {       #print "Welcome to the world of being white and castling kingside\n";
                        if (&onlist("K51",@sidetomove_cart) and &onlist("R81",@sidetomove_cart))
                        {       #print "plus having your king and rook on the right squares\n";
                                ($square1,$dum) = &getsinglemove("K",5,1,1,0,@sidetomove_cart,"turkeyburp",@sidenotmoving_cart);
                                ($square2,$dum) = &getsinglemove("K",5,1,2,0,@sidetomove_cart,"turkeyburp",@sidenotmoving_cart);
                                #print "and your square1 is $square1 while your square2 is $square2\n";
                                if ($square1 eq "empty" and $square2 eq "empty")
                                {       push @moveslist, "o-o";
                                }
                        }
                }
                if ($okcastle =~ /$castlechar[1]/)# =~ /$okcastle/)   # castle queenside?
                {       #print "Welcome to the world of being white and castling queenside\n";
                        if (&onlist("K51",@sidetomove_cart) and &onlist("R11",@sidetomove_cart))
                        {       ($square1,$dum) = &getsinglemove("K",5,1,-1,0,@sidetomove_cart,"turkeyburp",@sidenotmoving_cart);
                                ($square2,$dum) = &getsinglemove("K",5,1,-2,0,@sidetomove_cart,"turkeyburp",@sidenotmoving_cart);
                                ($square3,$dum) = &getsinglemove("K",5,1,-3,0,@sidetomove_cart,"turkeyburp",@sidenotmoving_cart);
                                if ($square1 eq "empty" and $square2 eq "empty" and $square3 eq "empty")
                                {       push @moveslist, "o-o-o";
                                }
                        }
                }
        }
        else
        {       @castlechar = ("k","q");  #black moving
                if ($okcastle =~ /$castlechar[0]/)# =~ /$okcastle/)   # castle kingside?
                {       if (&onlist("k58",@sidetomove_cart) and &onlist("r88",@sidetomove_cart))
                        {       ($square1,$dum) = &getsinglemove("k",5,8,1,0,@sidetomove_cart,"turkeyburp",@sidenotmoving_cart);
                                ($square2,$dum) = &getsinglemove("k",5,8,2,0,@sidetomove_cart,"turkeyburp",@sidenotmoving_cart);
                                if ($square1 eq "empty" and $square2 eq "empty")
                                {       push @moveslist, "o-o";
                                }
                        }
                }
                if ($okcastle =~ /$castlechar[1]/)# =~ /$okcastle/)   # castle queenside?
                {       if (&onlist("k58",@sidetomove_cart) and &onlist("r18",@sidetomove_cart))
                        {       ($square1,$dum) = &getsinglemove("k",5,8,-1,0,@sidetomove_cart,"turkeyburp",@sidenotmoving_cart);
                                ($square2,$dum) = &getsinglemove("k",5,8,-2,0,@sidetomove_cart,"turkeyburp",@sidenotmoving_cart);
                                ($square3,$dum) = &getsinglemove("k",5,8,-3,0,@sidetomove_cart,"turkeyburp",@sidenotmoving_cart);
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
{
# find the square which is dx dy away, and if it is on the board and unoccupied, then it's a legal move.
# if it is off the board or occupied by a friendly piece, then it's not a legal move.
# if it's an enemy piece, then its a legal capture
# inputs are   $piecetype,$curx,$cury,$dx[$raynum],$dy[$raynum],@sidetomovepos,"side not moving is after this",@sidenotmovingpos
# outputs should be the destination square type (one of empty, off board, friend, or enemy) and the move (e.g. Bh8, or B88 depending on formatting)
#process inputs
my ($ptype,$x,$y,$dx,$dy,@poslist)= @_;
my $newx = $x+$dx;
my $newy = $y+$dy;
my $newpos = $newx . $newy;
# Short circuit the checking if the new square is off the board
if ($newx > 8 || $newx < 1 || $newy < 1 || $newy > 8) {
        # off the board
        #my @out = ("off board", undef );
        return ("off board", undef );
}
#divide up poslist
my $switchtonotmoving = 0;
my (@sidetomovexy, @sidenotmovingxy);
#print "Poslist is: @poslist \n";
# loop over positions in list, placing each into the moving or not moving list
my (@splitpos,$posy,$posx,$posxy);
foreach my $pos (@poslist) {
        if ($pos eq $separator) {
                $switchtonotmoving = 1;
        }
        else {
                # just want the board position, not the piece
                @splitpos = split(//,$pos);
                $posy = pop @splitpos;
                $posx = pop @splitpos;
                $posxy = $posx . $posy;
                if ($switchtonotmoving) {
                        push @sidenotmovingxy, $posxy;
                }
                else {
                        push @sidetomovexy, $posxy;
                }
        }
}
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
return ($squaretype,$move)
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
{       my @exclam = ('Well!','See here!','I see!','Err...','Oh!','Goodness!','Heavens!','My oh my!','Jiminy!','Gracious me!');
        my @subject = ('Rats','Crickets','Chimps','Crocodiles','Elephants','Bats', 'Armadillos','Martians','Minions of the underworld','Michael Jackson\'s relatives','Many tiny Englishmen');
        my @verb = ('slam dunk','mame lame, then blame','lug a plank and spank','chomp-chomp-chomp','smack the heck out of','wreak havoc on','failed to notice','just up and telephoned','body-slammed');
        my @object = ('me!', 'you!', 'sweet Jesus!', 'my pants!', 'yer\' pants!', 'all of Zimbabwe!','Danny\'s fanny!','Mike\'s tyke!','a bunch of hypocrites!','themselves!');
        my @newline = ("\n");
        my $sentence = &say(\@exclam,\@subject,\@verb,\@object,\@newline);
}
#===============================================================================
sub wisdomtalk
{# when the engine is moving, in place of I in my infinite wisdom
my @put = ("Put","Gently place","Stick","Jam","Put your back into it, and squeeze");
my @this = ("this","THIS","as much of this as you can","some of this","a bit of this","anything resembling this","a bunch of this");
my @prep = ("in","on","underneath","somewhere in the vicinity of","twenty paces due east from","inside","in the depths of","beside","next to", "at the appropriate time, upon", "betwixt Cleveland and");
my @possess = ("your","your","your","Bob's","your King's","the King's","Ben Franklin's","Bobby Fischer's","Kermit the Frog's","a bearded man's","your mother's","a monkey's uncle's","... You remember that fellow you met yesterday? ... His","any random person's");
my @object = ("pipe","car","mailbox","polka-dotted underwear","toupee","cubicle","hot rod","troubled conscience","toothbrush","pants","left nostril");
my @and = ("and");
my @verb = ("smoke","eat","consider","become","pursue a vendetta against","make war upon","frighten","be frightened by","moo at","dance a jig around","emblazon your initals on","make a gift of");
my @it = ("it!\nRLM Move: ");
my $sentence = &say(\@put,\@this,\@prep,\@possess,\@object,\@and,\@verb,\@it);
}
#===============================================================================
sub prompttalk
{
my @goahead = ("Go ahead,","I triple-dog dare you,", "Hurry up and","You've got to","I wonder if I could trouble you to","You know, the game can't go on until you","The Queen of England commands you to","For once in your life, why don't you","It's time to","Come on now,","It would be disappointing if you didn't","All the chess faeries will rejoice if you","Hey,");
my @adverbs = ("randomly","carefully","provocatively","boldly","timidly","rapidly","profoundly","uncompromisingly","shut up and","resign or","perspicaciously",", in a manner agreeable to you,");
my @verb = ("make","choose","pick","select","decide on");
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
}
