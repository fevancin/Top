% input is in the form of:

% patient_requests(Patient, Packet)
% packet_contains(Packet, Service)
% service(Service, CareUnit, ServiceDuration)
% operator(Operator, CareUnit, OperatorStart, OperatorDuration)
% time(1..T)
% patient_has_priority(Patient, Priority)


% variables that describe the scheduling of a Service
{ do(Patient, Service, Operator, StartTime) } :-
    patient_requests(Patient, Packet),                              % Patient must be requesting a Packet..
    packet_contains(Packet, Service),                               % ..that contains the Service..
    service(Service, CareUnit, ServiceDuration),                    % ..that must be of a CareUnit..
    operator(Operator, CareUnit, OperatorStart, OperatorDuration),  % that is the same of the one of Operator.
    time(StartTime),                                                % Time is a time..
    StartTime >= OperatorStart,                                     % that lies inside the operator activity interval
    StartTime + ServiceDuration <= OperatorStart + OperatorDuration.

% each Service requested by a Patient can be done max 1 time
:- #count { Operator, StartTime : do(Patient, Service, Operator, StartTime) } > 1,
    patient_requests(Patient, Packet),
    packet_contains(Packet, Service).

% it's impossible that a Patient is in two places at the same time
:- do(Patient, Service1, _, StartTime1), do(Patient, Service2, _, StartTime2),
    Service1 != Service2,
    service(Service1, _, ServiceDuration1),
    StartTime1 <= StartTime2, StartTime1 + ServiceDuration1 > StartTime2.

% it's impossible that the same Operator satisfy more than one (Patient, Service) at a time
:- do(Patient1, Service1, Operator, StartTime1), do(Patient2, Service2, Operator, StartTime2),
    #count { p : Patient1 = Patient2 ; s : Service1 = Service2 } <= 1, % here it's avoided the same (Patient, Service) couple
    service(Service1, _, ServiceDuration1),
    StartTime1 <= StartTime2, StartTime1 + ServiceDuration1 > StartTime2.

% variable true for each fully completed Packet
{ packet_done(Patient, Packet) } :- patient_requests(Patient, Packet).

% if packet_done/2 is true, all do/4 of its Services must be also true
:- packet_done(Patient, Packet), packet_contains(Packet, Service), not do(Patient, Service, _, _).

% try to maximize the Packet completed, weighted by Priority
:~ packet_done(Patient, Packet), patient_has_priority(Patient, Priority). [-1@Priority, Patient, Packet]

#show do/4.