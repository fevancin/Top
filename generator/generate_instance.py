import os
import sys
import json
import random
from datetime import datetime

seed = 42

day_number = 20

care_unit_number = 4
care_unit_size = (1, 5)

service_number = 20
service_duration = (1, 10)
service_cost = (1, 4)

operator_start = (1, 50)
operator_duration = (1, 50)

packet_number = 16
packet_size = (1, 4)

patient_number = 15
patient_priority = (1, 4)

requests_per_day = (1, 4)
packet_requested = (1, 3)

interdiction_probability = 0.25
interdiction_duration = (1, 5)

necessity_probability = 0.25
necessity_number = (1, 2)
necessity_start = (0, 1)
necessity_duration = (2, 10)

protocols_per_patient = (1, 3)
iteration_number = (1, 2)
initial_offset = (-20, 20)
packets_per_protocol = (1, 3)
start_date = (1, 10)
frequency = (2, 15)
tolerance = (2, 6)
existence_start = (1, 15)
existence_duration = (5, 20)

# initial folder creation
os.chdir(os.path.dirname(sys.argv[0]))
os.chdir("..")
if not os.path.isdir("instance"):
    os.mkdir("instance")
os.chdir("instance")

random.seed(seed)

start_time = datetime.now()

# creation of the operators for each care_unit and for each day
# an operator is a couple [start, duration] of positive int values
operator_days = {}
for day_index in range(day_number):
    operator_day = {}
    for care_unit_index in range(care_unit_number):
        care_unit = {}
        operator_amount = random.randint(care_unit_size[0], care_unit_size[1])
        for operator_index in range(operator_amount):
            care_unit[f"op{operator_index:02}"] = {
                'start': random.randint(operator_start[0], operator_start[1]),
                'duration': random.randint(operator_duration[0], operator_duration[1])
            }
        operator_day[f"cu{care_unit_index:02}"] = care_unit
    operator_days[str(day_index)] = operator_day
del day_index, operator_day, care_unit_index, care_unit, operator_amount, operator_index

# services creation
# a service is described by the tuple (name, care_unit, duration, cost)
services = {}
for service_index in range(service_number):
    services[f"srv{service_index:02}"] = {
        'careUnit': f"cu{random.randint(0, care_unit_number - 1):02}",
        'duration': random.randint(service_duration[0], service_duration[1]),
        'cost': random.randint(service_cost[0], service_cost[1])
    }
del service_index

# packets generation
# a packet is a subset of all possible services
packets = {}
packet_index = 0
window = packet_number
size = packet_size[0]
max_packet_size = packet_size[1]
while packet_index < packet_number:
    window //= 2 # exponential shrinking of generation windows
    if window == 0: window = 1
    for _ in range(window):
        packet = []
        service_indexes = random.sample(range(service_number), size)
        for service_index in service_indexes:
            packet.append(f"srv{service_index:02}")
        packets[f"pkt{packet_index:02}"] = sorted(packet)
        packet_index += 1
    if size + 1 <= max_packet_size:
        size += 1
del packet_index, window, size, max_packet_size, packet, service_indexes

# assign each patient a priority
priorities = {}
for patient_index in range(patient_number):
    priorities[f"pat{patient_index:02}"] = random.randint(patient_priority[0], patient_priority[1])
del patient_index

# requests are composed by a patient group in which each one requests some packets.
# requests are divided by day
requests = {}
for day_index in range(day_number):
    patient_amount = random.randint(requests_per_day[0], requests_per_day[1])
    day_requests = dict()
    for patient_index in range(patient_amount):
        packet_amount = random.randint(packet_requested[0], packet_requested[1])
        packet_indexes = random.sample(range(packet_number), packet_amount)
        request = []
        for packet_index in packet_indexes:
            request.append(f"pkt{packet_index:02}")
        day_requests[f"pat{patient_index:02}"] = {
            'packets': sorted(request)
        }
    requests[str(day_index)] = day_requests
del day_index, patient_amount, day_requests, patient_index, packet_amount, packet_indexes, packet_index

# list all care_unit that have some operator in it
care_unit_names = set()
for operator_day in operator_days.values():
    for care_unit_name in operator_day.keys():
        care_unit_names.add(care_unit_name)
care_unit_names = sorted(care_unit_names)
del operator_day, care_unit_name

# group, for each care_unit and for each day, the total duration of its operator
total_durations = dict()
for day_name, operator_day in operator_days.items():
    day_duration = dict()
    for care_unit_name, care_unit in operator_day.items():
        total_duration = 0
        for operator in care_unit.values():
            total_duration += operator['duration']
        day_duration[care_unit_name] = total_duration
    total_durations[day_name] = day_duration
del day_name, operator_day, day_duration, care_unit_name, care_unit, total_duration, operator

# creation of service incompatibility windows
interdictions = dict()
for service_index in range(service_number):
    interdiction = dict()
    for other_service_index in range(service_number):
        if random.random() < interdiction_probability:
            interdiction[f"srv{other_service_index:02}"] = random.randint(interdiction_duration[0], interdiction_duration[1])
        else:
            interdiction[f"srv{other_service_index:02}"] = 0
    interdictions[f"srv{service_index:02}"] = interdiction
del service_index, interdiction, other_service_index

# generation of service requirements
necessities = dict()
for service_index in range(service_number):
    if random.random() < necessity_probability:
        necessity_amount = random.randint(necessity_number[0], necessity_number[1])
        necessity_indexes = random.sample(range(service_number), necessity_amount)
        necessity = dict()
        for necessity_index in necessity_indexes:
            start = random.randint(necessity_start[0], necessity_start[1])
            necessity[f"srv{necessity_index:02}"] = [
                start,
                start + random.randint(necessity_duration[0], necessity_duration[1])
            ]
        necessities[f"srv{service_index:02}"] = necessity
    else:
        necessities[f"srv{service_index:02}"] = {}
del service_index, necessity_amount, necessity_indexes, necessity, necessity_index, start

# protocol creation
# a protocol has 1+ iterations and each one has 1+ packets repeated at various regular intervals
protocols = dict()
protocol_index = 0
for patient_index in range(patient_number):
    protocol_amount = random.randint(protocols_per_patient[0], protocols_per_patient[1])
    patient_protocols = dict()
    for _ in range(protocol_amount):
        packet_amount = random.randint(packets_per_protocol[0], packets_per_protocol[1])
        packet_indexes = random.sample(range(packet_number), packet_amount)
        packet_list = []
        for packet_index in packet_indexes:
            start = random.randint(existence_start[0], existence_start[1])
            packet_list.append({
                'packet_id': f"pkt{packet_index:02}",
                'start_date': random.randint(start_date[0], start_date[1]),
                'freq': random.randint(frequency[0], frequency[1]),
                'since': "start_date",
                'tolerance': random.randint(tolerance[0], tolerance[1]),
                'existence': [
                    start,
                    start + random.randint(existence_duration[0], existence_duration[1])
                ]
            })
        iteration_amount = random.randint(iteration_number[0], iteration_number[1])
        iterations = {}
        for iteration_index in range(iteration_amount):
            iterations[f"iter{iteration_index:02}"] = [
                packet_list,
                random.randint(initial_offset[0], initial_offset[1])
            ]
        patient_protocols[f"prot{protocol_index:02}"] = iterations
        protocol_index += 1
    patient_name = f"pat{patient_index:02}"
    patient_protocols['priority_weight'] = priorities[patient_name]
    protocols[patient_name] = patient_protocols
del protocol_index, patient_index, protocol_amount, patient_protocols, packet_list, packet_amount, packet_index, start, iteration_amount, iterations, iteration_index, patient_name

full_input = {
    'datecode': datetime.now().strftime("%a-%d-%b-%Y-%H-%M-%S"),
    'horizon': day_number,
    'resources': care_unit_names,
    'capacity': total_durations,
    'daily_capacity': operator_days,
    'services': services,
    'interdictions': interdictions,
    'necessity': necessities,
    'abstract_packet': packets,
    'pat_request': protocols
}

end_time = datetime.now()

# output the instance to json files
with open("operators.json", "w") as file:
    file.write(json.dumps(operator_days, indent=4, sort_keys=True))
with open("services.json", "w") as file:
    file.write(json.dumps(services, indent=4, sort_keys=True))
with open("packets.json", "w") as file:
    file.write(json.dumps(packets, indent=4, sort_keys=True))
with open("priorities.json", "w") as file:
    file.write(json.dumps(priorities, indent=4, sort_keys=True))
with open("full_input.json", "w") as file:
    file.write(json.dumps(full_input, indent=4, sort_keys=True))

os.chdir("..")
if not os.path.isdir("master"):
    os.mkdir("master")
os.chdir("master")

with open("requests.json", "w") as file:
    file.write(json.dumps(requests, indent=4, sort_keys=True))

print("Creation of instance successfull. Data is in folder 'instance'")
print(f"Time taken: {end_time - start_time}")