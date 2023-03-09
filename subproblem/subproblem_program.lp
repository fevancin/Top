{ do(Patient, Service, Operator, StartTime) } :-
    patient_requests(Patient, Packet),
    packet_contains(Packet, Service),
    service(Service, CareUnit, ServiceDuration),
    operator(Operator, CareUnit, OperatorStart, OperatorDuration),
    time(StartTime),
    StartTime >= OperatorStart,
    StartTime + ServiceDuration <= OperatorStart + OperatorDuration.

:- #count { Operator, StartTime : do(Patient, Service, Operator, StartTime) } > 1,
    patient_requests(Patient, Packet),
    packet_contains(Packet, Service).

:- do(Patient, Service1, _, StartTime1), do(Patient, Service2, _, StartTime2),
    Service1 != Service2,
    service(Service1, _, ServiceDuration1),
    StartTime1 <= StartTime2, StartTime1 + ServiceDuration1 > StartTime2.

:- do(Patient1, Service1, Operator, StartTime1), do(Patient2, Service2, Operator, StartTime2),
    #count { p : Patient1 = Patient2 ; s : Service1 = Service2 } <= 1,
    service(Service1, _, ServiceDuration1),
    StartTime1 <= StartTime2, StartTime1 + ServiceDuration1 > StartTime2.

{ packet_done(Patient, Packet) } :- patient_requests(Patient, Packet).

:- packet_done(Patient, Packet), packet_contains(Packet, Service), not do(Patient, Service, _, _).

:~ packet_done(Patient, Packet), patient_has_priority(Patient, Priority). [-1@Priority, Patient, Packet]

#show do/4.