{ choose(Less, More) } :-
    less(Less, LessStart, LessDuration),
    more(More, MoreStart, MoreDuration),
    MoreStart <= LessStart,
    MoreStart + MoreDuration >= LessStart + LessDuration.

:- #count { More : choose(Less, More) } != 1, less(Less, _, _).

:- choose(Less1, More), choose(Less2, More), Less1 != Less2,
    less(Less1, LessStart1, LessDuration1),
    less(Less2, LessStart2, _),
    LessStart1 <= LessStart2,
    LessStart1 + LessDuration1 > LessStart2.

#show choose/2.