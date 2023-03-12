import os
import sys
import json
import subprocess
from datetime import datetime

# initial directory movement
os.chdir(os.path.dirname(sys.argv[0]))
os.chdir("..")
if not os.path.isdir("instance"):
    print("Instance folder not found")
    exit(-1)
os.chdir("instance")

# reads input instance
with open("full_input.json", "r") as file:
    full_input = json.loads(file.read())

os.chdir("..")
os.chdir("master")

start_time = datetime.now()

days_compatible_with_packet = dict()
for packet_name, packet in full_input["abstract_packet"].items():
    packet_requests = dict()
    for service_name in packet:
        care_unit_name = full_input["services"][service_name]["careUnit"]
        if care_unit_name not in packet_requests:
            packet_requests[care_unit_name] = 0
        packet_requests[care_unit_name] += full_input["services"][service_name]["duration"]
    compatibility_days = []
    for day_name, capacities in full_input["capacity"].items():
        is_packet_compatible = True
        for care_unit_name, care_unit_request in packet_requests.items():
            if care_unit_request >= capacities[care_unit_name]:
                is_packet_compatible = False
                break
        if is_packet_compatible:
            compatibility_days.append(day_name)
    if len(compatibility_days) > 0:
        days_compatible_with_packet[packet_name] = compatibility_days
del packet_name, packet, packet_requests, service_name, care_unit_name, compatibility_days, day_name, capacities, is_packet_compatible, care_unit_request

days_compatible_with_protocol_packet = dict()
windows = dict()
for patient_name, patient in full_input["pat_request"].items():
    for protocol_name, protocol in patient.items():
        if protocol_name == "priority_weight":
            continue
        for iteration in protocol.values():
            protocol_packets = iteration[0]
            initial_shift = iteration[1]
            for protocol_packet in protocol_packets:
                compatibility_day_indexes = set()
                start_window_day = protocol_packet["existence"][0]
                end_window_day = protocol_packet["existence"][1]
                start_day = protocol_packet["start_date"]
                tolerance = protocol_packet["tolerance"]
                packet_name = protocol_packet["packet_id"]
                for exact_day_index in range(start_day, end_window_day, protocol_packet["freq"]):
                    if exact_day_index < start_window_day:
                        continue
                    windows[(patient_name, protocol_name, packet_name)] = (start_window_day, end_window_day)
                    for day_index in range(exact_day_index - tolerance, exact_day_index + tolerance):
                        if day_index < start_window_day or day_index > end_window_day:
                            continue
                        if str(day_index) in days_compatible_with_packet[packet_name]:
                            compatibility_day_indexes.add(day_index)
                if len(compatibility_day_indexes) == 0:
                    continue
                if (patient_name, packet_name) in days_compatible_with_protocol_packet:
                    days_compatible_with_protocol_packet[(patient_name, packet_name)].update(compatibility_day_indexes)
                else:
                    days_compatible_with_protocol_packet[(patient_name, packet_name)] = compatibility_day_indexes
del patient_name, patient, protocol_name, protocol, iteration, protocol_packets, initial_shift, protocol_packet, compatibility_day_indexes, start_window_day, end_window_day, start_day, tolerance, packet_name, exact_day_index, day_index, days_compatible_with_packet

input_program = f"day(0..{full_input['horizon']}).\n" # input program of the ASP solver
patient_names = set()

# TODO add initial shift when build input in python!!!
# TODO add constraint for sum of packet dimensions < capacity of the day

for (patient_name, packet_name), days in days_compatible_with_protocol_packet.items():
    patient_names.add(patient_name)
    for day_index in days:
        input_program += f"{{ do({patient_name}, {packet_name}, {day_index}) }}.\n"
del patient_name, packet_name, days, day_index, days_compatible_with_protocol_packet

for (patient_name, protocol_name, packet_name), (window_start, window_end) in windows.items():
    input_program += f"protocol_has_window({patient_name}, {protocol_name}, {packet_name}, {window_start}, {window_end}).\n"
del patient_name, protocol_name, packet_name, window_start, window_end, windows

for patient_name in patient_names:
    input_program += f"patient_has_priority({patient_name}, {full_input['pat_request'][patient_name]['priority_weight']}).\n"
del patient_name, patient_names

with open("input_program.lp", "w") as file:
    file.write(input_program)
del input_program

with open("results.txt", "w") as file:
    subprocess.run(["clingo", "input_program.lp", "master_program.lp", "--time-limit=2"], stdout=file, stderr=subprocess.DEVNULL)

data = {
    'protocols_done': [],
    'packets_to_schedule': []
}

with open("results.txt", "r") as file: # reads results
    strings = file.read().split("Answer")[-1].split("\n")[1].split(" ") # some decoding string magic..
    for string in strings:
        name, params = string.split("(")
        tokens = params[:-1].split(",")
        if name == "do":
            data['packets_to_schedule'].append({
                'patient': tokens[0],
                'packet': tokens[1],
                'day': tokens[2]
            })
        elif name == "is_protocol_done":
            data['protocols_done'].append({
                'patient': tokens[0],
                'protocol': tokens[1]
            })
del strings, string, name, params, tokens

# removing the temporary files
if os.path.isfile("input_program.lp"):
    os.remove("input_program.lp")
if os.path.isfile("results.txt"):
    os.remove("results.txt")

# build the packet requests, grouping by day and patient name
requests = dict()
for packet_to_schedule in data['packets_to_schedule']:
    patient_name = packet_to_schedule['patient']
    packet_name = packet_to_schedule['packet']
    day = packet_to_schedule['day']
    if day not in requests:
        requests[day] = dict()
    if patient_name not in requests[day]:
        requests[day][patient_name] = {
            'packets': []
        }
    if packet_name not in requests[day][patient_name]['packets']:
        requests[day][patient_name]['packets'].append(packet_name)
del data

end_time = datetime.now()

# output the result into a json file
with open("requests.json", "w") as file:
    file.write(json.dumps(requests, indent=4, sort_keys=True))

print("Requests are in the file 'requests.json'")
print(f"Time taken: {end_time - start_time}")