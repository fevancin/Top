import os
import sys
import json
from datetime import datetime

# initial directory movements
os.chdir(os.path.dirname(sys.argv[0]))
os.chdir("..")
if not os.path.isdir("instance"):
    print("Instance folder not found")
    exit(-1)
os.chdir("instance")

# read input instance
with open("services.json", "r") as file:
    services = json.loads(file.read())
with open("packets.json", "r") as file:
    packets = json.loads(file.read())
with open("requests.json", "r") as file:
    requests = json.loads(file.read())

os.chdir("..")
os.chdir("subproblem")

# read subproblem results
with open("results.json", "r") as file:
    results = json.loads(file.read())

os.chdir("..")
os.chdir("subsumptions")

# read subsumptions
with open("subsumptions.json", "r") as file:
    subsumptions = json.loads(file.read())

os.chdir("..")
os.chdir("cores")

start_time = datetime.now()

# packet -> [care_units affected by it]
packet_to_care_units = dict()
care_unit_names = set()
for packet_name, packet in packets.items():
    care_unit_set = set()
    for service_name in packet:
        care_unit_name = services[service_name]['careUnit']
        care_unit_set.add(care_unit_name)
        care_unit_names.add(care_unit_name)
    packet_to_care_units[packet_name] = care_unit_set
del packet_name, packet, service_name, care_unit_set, care_unit_name

cores = dict()
core_index = 0
for day_name, day_results in results.items():
    for patient_name, packets_not_done in day_results['notScheduledPackets'].items():
        for packet_not_done in packets_not_done: # for each packet not done in the subproblem results
            nodes_to_do = [{ #start the search with it
                'patient': patient_name,
                'packet': packet_not_done
            }]
            nodes_done = []
            care_units_to_do = []
            care_units_done = []
            while len(nodes_to_do) > 0:
                current_node = nodes_to_do.pop()
                nodes_done.append(current_node) # do a node visit
                for care_unit in packet_to_care_units[current_node['packet']]:
                    if care_unit not in care_units_done:
                        care_units_to_do.append(care_unit) # visit all new care units touched by the new packet
                while len(care_units_to_do) > 0:
                    current_care_unit = care_units_to_do.pop()
                    care_units_done.append(current_care_unit) # adds to the already-visited care_units
                    for patient_name_to_add, patient_to_add in requests[day_name].items():
                        for packet_name_to_add in patient_to_add['packets']:
                            if current_care_unit not in packet_to_care_units[packet_name_to_add]:
                                continue
                            if patient_name_to_add in day_results['notScheduledPackets'] and packet_name_to_add in day_results['notScheduledPackets'][patient_name_to_add]:
                                continue
                            already_done = False
                            for node in nodes_done:
                                if node['patient'] == patient_name_to_add and node['packet'] == packet_name_to_add:
                                    already_done = True
                                    break
                            if already_done:
                                continue
                            for node in nodes_to_do:
                                if node['patient'] == patient_name_to_add and node['packet'] == packet_name_to_add:
                                    already_done = True
                                    break
                            if already_done:
                                continue
                            nodes_to_do.append({ # if another done packet affect the care_unit, adds it to the todo list
                                'patient': patient_name_to_add,
                                'packet': packet_name_to_add
                            })
            care_units_done.sort()
            packet_groupings = dict() # group the (patient, packet) list by patient
            while len(nodes_done) > 0:
                node = nodes_done.pop()
                if node['patient'] not in packet_groupings:
                    packet_groupings[node['patient']] = []
                packet_groupings[node['patient']].append(node['packet'])
            multipackets = dict() # explode each grouping revealing the services
            for packet_grouping in packet_groupings.values():
                service_set = set()
                for packet_name in packet_grouping:
                    for service_name in packets[packet_name]:
                        service_set.add(service_name)
                service_list = sorted(service_set)
                multipacket_name = "_".join(service_list) # the multipacket name is the concatenation of its service names
                if multipacket_name in multipackets:
                    multipackets[multipacket_name]['times'] += 1 # not repeating of equal multipackets
                else:
                    multipackets[multipacket_name] = {
                        'times': 1,
                        'services': service_list
                    }
            core_days = [day_name] # look for days that are lesser than the current one in each care_unit
            for lesser_day_name in requests.keys():
                if lesser_day_name == day_name:
                    continue
                is_lesser_day = True
                for care_unit_name in care_units_done:
                    if day_name not in subsumptions[care_unit_name] or lesser_day_name not in subsumptions[care_unit_name][day_name]:
                        is_lesser_day = False
                        break
                if is_lesser_day:
                    core_days.append(lesser_day_name)
            core_days.sort()
            cores[f"core{core_index:02}"] = {
                'days': core_days,
                'multipackets': multipackets,
                'affectedCareUnits': care_units_done
            }
            core_index += 1

end_time = datetime.now()

# output cores into json file
with open("unsatisfiable_cores.json", "w") as file:
    file.write(json.dumps(cores, indent=4, sort_keys=True))

print("Cores are in the file 'unsatisfiable_cores.json'")
print(f"Time taken: {end_time - start_time}")