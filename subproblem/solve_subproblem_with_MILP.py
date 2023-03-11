import os
import sys
import json
from datetime import datetime

from pyomo.environ import ConcreteModel, NonNegativeIntegers, Binary, maximize, SolverFactory, value
from pyomo.environ import Set, Var, Objective, Constraint

# initial directory movement
os.chdir(os.path.dirname(sys.argv[0]))
os.chdir("..")
if not os.path.isdir("instance"):
    print("Instance folder not found")
    exit(-1)
os.chdir("instance")

# reads input instance
with open("operators.json", "r") as file:
    operator_days = json.loads(file.read())
with open("services.json", "r") as file:
    services = json.loads(file.read())
with open("packets.json", "r") as file:
    packets = json.loads(file.read())
with open("priorities.json", "r") as file:
    priorities = json.loads(file.read())

os.chdir("..")
os.chdir("master")

with open("requests.json", "r") as file:
    requests = json.loads(file.read())

os.chdir("..")
os.chdir("subproblem")

start_time = datetime.now()

scheduled_services = dict()
for day_name, day_requests in requests.items():
    day_operators = operator_days[day_name]
    request_indexes = set() # fill the indexes with only the minimum information necessary (only required names)
    chi_indexes = set()
    packet_indexes = set()
    packet_service_indexes = set()
    max_time = 0
    something_to_do = False
    for patient_name, patient in day_requests.items():
        for packet_name in patient['packets']:
            is_packet_satisfiable = True
            temp_request_indexes = set()
            temp_packet_service_indexes = set()
            temp_chi_indexes = set()
            for service_name in packets[packet_name]:
                is_service_satisfiable = False
                care_unit_name = services[service_name]['careUnit']
                for operator_name, operator in day_operators[care_unit_name].items():
                    if operator['duration'] >= services[service_name]['duration']:
                        is_service_satisfiable = True
                        temp_chi_indexes.add((patient_name, service_name, operator_name + "__" + care_unit_name)) # combine the operator name with the care_unit in order to avoid ambiguity
                        operator_end_time = operator['start'] + operator['duration']
                        if max_time < operator_end_time:
                            max_time = operator_end_time # max_time is the maximum schedulable day time
                if is_service_satisfiable:  # add names only there is at least one operator that can do the service
                    temp_request_indexes.add((patient_name, service_name))
                    temp_packet_service_indexes.add((patient_name, service_name, packet_name))
                else:
                    is_packet_satisfiable = False
                    break
            if is_packet_satisfiable:  # add names only of packets that are completely satisfiable
                request_indexes.update(temp_request_indexes)
                chi_indexes.update(temp_chi_indexes)
                packet_service_indexes.update(temp_packet_service_indexes)
                packet_indexes.add((patient_name, packet_name))
                something_to_do = True
    if not something_to_do: # short-circuit for empty days
        scheduled_services[day_name] = {}
        continue

    request_indexes = sorted(request_indexes)

    aux1_indexes = [] # indexes for the not-overlapping constraints
    for i in range(len(request_indexes) - 1):
        for j in range(i + 1, len(request_indexes)):
            if request_indexes[i][0] == request_indexes[j][0]:
                aux1_indexes.append((request_indexes[i][0], request_indexes[i][1], request_indexes[j][1]))

    model = ConcreteModel()
    model.request_indexes = Set(initialize=request_indexes)
    model.chi_indexes = Set(initialize=sorted(chi_indexes))
    model.packet_indexes = Set(initialize=sorted(packet_indexes))
    model.packet_service_indexes = Set(initialize=sorted(packet_service_indexes))
    model.aux1_indexes = Set(initialize=aux1_indexes)
    # model.aux2_indexes = Set(initialize=info['aux2_indexes'])

    del request_indexes, chi_indexes, packet_indexes, packet_service_indexes, aux1_indexes, i, j

    model.t = Var(model.request_indexes, domain=NonNegativeIntegers, bounds=(0, max_time))
    model.x = Var(model.request_indexes, domain=Binary)
    model.chi = Var(model.chi_indexes, domain=Binary)
    model.packet = Var(model.packet_indexes, domain=Binary)
    model.aux1 = Var(model.aux1_indexes, domain=Binary)
    # model.aux2 = Var(model.aux2_indexes, domain=Binary)

    def f(model):
        total = len(model.request_indexes) * 100
        return sum(model.packet[pat, pkt] * priorities[pat] for (pat, pkt) in model.packet_indexes) * total - sum(model.x[pat, srv] for (pat, srv) in model.request_indexes)
    model.objective = Objective(rule=f, sense=maximize)

    def f1(model, pat, srv):
        return model.t[pat, srv] - model.x[pat, srv] * max_time <= 0
    model.t_and_x = Constraint(model.request_indexes, rule=f1)
    def f2(model, pat, srv):
        return model.x[pat, srv] - model.t[pat, srv] <= 0
    model.x_and_t = Constraint(model.request_indexes, rule=f2)

    def f3(model, pat, srv):
        return sum(model.chi[pat, srv, op] for (pat2, srv2, op) in model.chi_indexes if pat == pat2 and srv == srv2) - model.x[pat, srv] == 0
    model.x_and_chi = Constraint(model.request_indexes, rule=f3)

    def f4(model, pat, srv, op):
        operator_name, care_unit = op.split("__")
        start_time = day_operators[care_unit][operator_name]['start']
        total = start_time - max_time
        return total + max_time * model.chi[pat, srv, op] - model.t[pat, srv] <= 0
    model.respect_start = Constraint(model.chi_indexes, rule=f4)

    def f5(model, pat, srv, op):
        operator_name, care_unit = op.split("__")
        duration = services[srv]['duration']
        end_time = day_operators[care_unit][operator_name]['start'] + day_operators[care_unit][operator_name]['duration']
        total = duration - end_time - max_time
        return model.t[pat, srv] + total + max_time * model.chi[pat, srv, op] <= 0
    model.respect_end = Constraint(model.chi_indexes, rule=f5)

    def f6(model, pat, srv, pkt):
        return model.packet[pat, pkt] - model.x[pat, srv] <= 0
    model.consistency = Constraint(model.packet_service_indexes, rule=f6)

    # def f7(model, pat, srv1, srv2):
    #     duration = services[srv1]['duration']
    #     total = duration - 2 * max_time
    #     return model.t[pat, srv1] + total - model.t[pat, srv2] + max_time * (- model.aux1[pat, srv1, srv2] + model.x[pat, srv1] + model.x[pat, srv2]) <= 0
    # model.patient_overlap1 = Constraint(model.aux1_indexes, rule=f7)

    # def f8(model, pat, srv1, srv2):
    #     duration = services[srv2]['duration']
    #     total = duration - 3 * max_time
    #     return model.t[pat, srv2] + total - model.t[pat, srv1] + max_time * (model.aux1[pat, srv1, srv2] + model.x[pat, srv1] + model.x[pat, srv2]) <= 0
    # model.patient_overlap2 = Constraint(model.aux1_indexes, rule=f8)

    # def f9(model, op, pat1, srv1, pat2, srv2):
    #     duration = services[srv1]['duration']
    #     total = duration - 2 * max_time
    #     return model.t[pat1, srv1] + total - model.t[pat2, srv2] + max_time * (- model.aux2[op, pat1, srv1, pat2, srv2] + model.chi[pat1, srv1, op] + model.chi[pat2, srv2, op]) <= 0
    # model.operator_overlap1 = Constraint(model.aux2_indexes, rule=f9)

    # def f10(model, op, pat1, srv1, pat2, srv2):
    #     duration = services[srv2]['duration']
    #     total = duration - 3 * max_time
    #     return model.t[pat2, srv2] + total - model.t[pat1, srv1] + max_time * (model.aux2[op, pat1, srv1, pat2, srv2] + model.chi[pat1, srv1, op] + model.chi[pat2, srv2, op]) <= 0
    # model.operator_overlap2 = Constraint(model.aux2_indexes, rule=f10)

    opt = SolverFactory("glpk")
    # model.pprint()
    # exit(0)
    opt.solve(model)

    day_scheduled_services = []
    for x_index in model.chi_indexes:
        if value(model.chi[x_index]) > 0: # decoding the output
            operator_name, care_unit_name = x_index[2].split("__")
            day_scheduled_services.append({
                'patient': x_index[0],
                'service': x_index[1],
                'operator': operator_name,
                'careUnit': care_unit_name,
                'start': int(value(model.t[x_index[0], x_index[1]]))
            })
    day_scheduled_services.sort(key=lambda s: s['patient'] + s['service'])
    scheduled_services[day_name] = day_scheduled_services
del day_name, day_requests, day_operators, max_time, patient_name, patient, packet_name, is_packet_satisfiable, service_name, is_service_satisfiable, care_unit_name, operator_name, operator, operator_end_time, day_scheduled_services, model, opt

results = dict()
for day_name, day_scheduled_services in scheduled_services.items():
    not_scheduled_packets = dict() # here there will be inserted the packets not completed, divided by patient_name
    for patient_name, patient in requests[day_name].items():
        for packet_name in patient['packets']:
            is_packet_scheduled = True
            for service_name in packets[packet_name]:
                is_service_scheduled = False
                for scheduled_service in day_scheduled_services:
                    if scheduled_service['patient'] == patient_name and scheduled_service['service'] == service_name:
                        is_service_scheduled = True
                        break
                if not is_service_scheduled:
                    is_packet_scheduled = False
                    break
            if not is_packet_scheduled: # if there is at least one of its service not done
                if patient_name not in not_scheduled_packets:
                    not_scheduled_packets[patient_name] = []
                not_scheduled_packets[patient_name].append(packet_name)
    unused_operators = dict()
    for care_unit_name, care_unit in operator_days[day_name].items():
        for operator_name in care_unit.keys():
            is_operator_used = False
            for scheduled_service in day_scheduled_services:
                if scheduled_service['careUnit'] == care_unit_name and scheduled_service['operator'] == operator_name:
                    is_operator_used = True
                    break
            if not is_operator_used: # if no scheduled service uses this operator, add it to the list
                if not care_unit_name in unused_operators:
                    unused_operators[care_unit_name] = []
                unused_operators[care_unit_name].append(operator_name)
    results[day_name] = {
        'scheduledServices': day_scheduled_services,
        'notScheduledPackets': not_scheduled_packets,
        'unusedOperators': unused_operators
    }
del day_name, day_scheduled_services, not_scheduled_packets, patient_name, patient, packet_name, is_packet_scheduled, service_name, is_service_scheduled, scheduled_service, unused_operators, care_unit_name, care_unit, operator_name, is_operator_used

end_time = datetime.now()

# output the result into a json file
with open("results.json", "w") as file:
    file.write(json.dumps(results, indent=4, sort_keys=True))

print("Results are in the file 'results.json'")
print("Time taken: " + str(end_time - start_time))