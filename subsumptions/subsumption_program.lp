% input is in the form of:

% less(Less, LessStart, LessDuration) for each Less operator
% more(More, MoreStart, MoreDuration) for each More operator

% variable that can be true if Less is an interval contained in More
{ choose(Less, More) } :-
    less(Less, LessStart, LessDuration),
    more(More, MoreStart, MoreDuration),
    MoreStart <= LessStart,
    MoreStart + MoreDuration >= LessStart + LessDuration.

% each Less must choose exactly one More
:- #count { More : choose(Less, More) } != 1, less(Less, _, _).

% it's impossible that two Lesses choose the same More if they overlap
:- choose(Less1, More), choose(Less2, More), Less1 != Less2,
    less(Less1, LessStart1, LessDuration1),
    less(Less2, LessStart2, _),
    LessStart1 <= LessStart2,
    LessStart1 + LessDuration1 > LessStart2.

#show choose/2.