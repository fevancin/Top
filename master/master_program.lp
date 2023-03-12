% day(0..D).
% care_unit_has_capacity(CareUnit, Day, Capacity).
% packet_has_care_unit_of_size(Packet, CareUnit, Size).
% patient_has_priority(Patient, Priority).
% protocol_has_window(Patient, Protocol, Packet, StartWindow, EndWindow).

% { do(Patient, Packet, Day) }. variable for each Packet that can be done in day Day (respecting the care units)

% it's not possible an assignment that require more than a care unit can provide a certain day
:- care_unit_capacity(CareUnit, Day, Capacity),
    #sum { Size, Packet, Patient : do(Patient, Packet, Day), packet_has_care_unit_size(Packet, CareUnit, Size) } > Capacity.

% is_window_done/5 becomes true if there is a *single* do/3 in a Day inside its interval [StartWindow, EndWindow]
{ is_window_done(Patient, Protocol, Packet, StartWindow, EndWindow) } :- protocol_has_window(Patient, Protocol, Packet, StartWindow, EndWindow).

:- is_window_done(Patient, _, Packet, StartWindow, EndWindow),                              % it's impossible that a window is satisfied..
    #count { Day : do(Patient, Packet, Day), Day >= StartWindow, Day <= EndWindow } != 1.   % ..if there is not a single Day in which Packet is done

% variable become true if a Protocol is completed in all of its window components
{ is_protocol_done(Patient, Protocol) } :- protocol_has_window(Patient, Protocol, _, _, _).

:- is_protocol_done(Patient, Protocol),                                     % it's impossible that a Protocol is done if..
    protocol_has_window(Patient, Protocol, Packet, StartWindow, EndWindow), % ..has a window..
    not is_window_done(Patient, Protocol, Packet, StartWindow, EndWindow).  % ..that is not satisfied

% try to maximize the Protocols done, weighted by the Patient Priority..
:~ is_protocol_done(Patient, Protocol), patient_has_priority(Patient, Priority). [-10, Priority, Patient, Protocol]

% ..while not exceeding doing useless Packets
:~ do(Patient, Packet, Day). [1, Patient, Packet, Day]

#show do/3.
% #show is_window_done/5.
#show is_protocol_done/2.