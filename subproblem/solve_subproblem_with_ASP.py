import os
import sys
import json
import subprocess
from datetime import datetime

os.chdir(os.path.dirname(sys.argv[0]))
os.chdir("..")
if not os.path.isdir("instance"):
    print("Instance folder not found")
    exit(-1)
os.chdir("instance")

with open("operators.json", "r") as file:
    operator_days = json.loads(file.read())
with open("services.json", "r") as file:
    services = json.loads(file.read())
with open("packets.json", "r") as file:
    packets = json.loads(file.read())
with open("priorities.json", "r") as file:
    priorities = json.loads(file.read())
with open("requests.json", "r") as file:
    requests = json.loads(file.read())

os.chdir("..")
os.chdir("subproblem")

start_time = datetime.now()

scheduled_services = dict()
for day_name, day_requests in requests.items():
    day_operators = operator_days[day_name]
    patient_names = set()
    packet_names = set()
    service_names = set()
    care_unit_names = set()
    operator_names = set()
    max_time = 0
    for patient_name, patient in day_requests.items():
        patient_doable = False
        for packet_name in patient["packets"]:
            is_packet_satisfiable = True
            for service_name in packets[packet_name]:
                is_service_satisfiable = False
                care_unit_name = services[service_name]["careUnit"]
                for operator_name, operator in day_operators[care_unit_name].items():
                    if operator["duration"] >= services[service_name]["duration"]:
                        is_service_satisfiable = True
                        operator_names.add(operator_name + "__" + care_unit_name)
                        operator_end_time = operator["start"] + operator["duration"]
                        if max_time < operator_end_time:
                            max_time = operator_end_time
                if is_service_satisfiable:
                    service_names.add(service_name)
                    care_unit_names.add(care_unit_name)
                else:
                    is_packet_satisfiable = False
                    break
            if is_packet_satisfiable:
                packet_names.add(packet_name)
                patient_doable = True
        if patient_doable:
            patient_names.add(patient_name)
    if len(patient_names) == 0:
        scheduled_services[day_name] = {}
        continue
    input_program = ""
    for patient_name in patient_names:
        input_program += "patient_has_priority(" + patient_name + ", " + str(priorities[patient_name]) + ").\n"
    for patient_name in patient_names:
        for packet_name in day_requests[patient_name]["packets"]:
            input_program += "patient_requests(" + patient_name + ", " + packet_name + ").\n"
    for packet_name in packet_names:
        for service_name in packets[packet_name]:
            input_program += "packet_contains(" + packet_name + ", " + service_name + ").\n"
    for service_name in service_names:
        input_program += "service(" + service_name + ", " + services[service_name]["careUnit"] + ", " + str(services[service_name]["duration"]) + ").\n"
    for compound_name in operator_names:
        operator_name, care_unit_name = compound_name.split("__")
        operator = day_operators[care_unit_name][operator_name]
        input_program += "operator(" + operator_name + ", " + care_unit_name + ", " + str(operator["start"]) + ", " + str(operator["duration"]) + ").\n"
    input_program += "time(1.." + str(max_time) + ").\n"
    with open("input_program.lp", "w") as file:
        file.write(input_program)
    with open("results.txt", "w") as file:
        subprocess.run(["clingo", "input_program.lp", "subproblem_program.lp", "--time-limit=2"], stdout=file, stderr=subprocess.DEVNULL)
    day_scheduled_services = []
    with open("results.txt", "r") as file:
        strings = file.read().split("Answer")[-1].split("do(")[1:]
        strings[-1] = strings[-1].split(")")[0] + ") "
        for string in strings:
            tokens = string[:-2].split(",")
            day_scheduled_services.append({
                "patient": tokens[0],
                "service": tokens[1],
                "operator": tokens[2],
                "careUnit": services[tokens[1]]["careUnit"],
                "start": int(tokens[3])
            })
    scheduled_services[day_name] = day_scheduled_services
del day_name, day_requests, day_operators, patient_names, packet_names, service_names, care_unit_names, operator_names, max_time, patient_name, patient, patient_doable, packet_name, is_packet_satisfiable, service_name, is_service_satisfiable, care_unit_name, operator_name, operator, operator_end_time, input_program, compound_name, day_scheduled_services

if os.path.isfile("input_program.lp"):
    os.remove("input_program.lp")
if os.path.isfile("results.txt"):
    os.remove("results.txt")

results = dict()
for day_name, day_scheduled_services in scheduled_services.items():
    not_scheduled_packets = dict()
    for patient_name, patient in requests[day_name].items():
        for packet_name in patient["packets"]:
            is_packet_scheduled = True
            for service_name in packets[packet_name]:
                is_service_scheduled = False
                for scheduled_service in day_scheduled_services:
                    if scheduled_service["patient"] == patient_name and scheduled_service["service"] == service_name:
                        is_service_scheduled = True
                        break
                if not is_service_scheduled:
                    is_packet_scheduled = False
                    break
            if not is_packet_scheduled:
                if patient_name not in not_scheduled_packets:
                    not_scheduled_packets[patient_name] = []
                not_scheduled_packets[patient_name].append(packet_name)
    unused_operators = dict()
    for care_unit_name, care_unit in operator_days[day_name].items():
        for operator_name in care_unit.keys():
            is_operator_used = False
            for scheduled_service in day_scheduled_services:
                if scheduled_service["careUnit"] == care_unit_name and scheduled_service["operator"] == operator_name:
                    is_operator_used = True
                    break
            if not is_operator_used:
                if not care_unit_name in unused_operators:
                    unused_operators[care_unit_name] = []
                unused_operators[care_unit_name].append(operator_name)
    results[day_name] = {
        "scheduledServices": day_scheduled_services,
        "notScheduledPackets": not_scheduled_packets,
        "unusedOperators": unused_operators
    }

end_time = datetime.now()

with open("results.json", "w") as file:
    file.write(json.dumps(results, indent=4, sort_keys=True))

print("Results are in the file 'results.json'")
print("Time taken: " + str(end_time - start_time))