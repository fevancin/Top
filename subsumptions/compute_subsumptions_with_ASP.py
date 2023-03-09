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

os.chdir("..")
os.chdir("subsumptions")

start_time = datetime.now()

care_unit_names = set()
for operator_day in operator_days.values():
    for care_unit_name in operator_day.keys():
        care_unit_names.add(care_unit_name)
del operator_day, care_unit_name

subsumptions = dict()
for care_unit_name in care_unit_names:
    subsumption = dict()
    for more_day_name, more_operator_day in operator_days.items():
        lesser_days = []
        if care_unit_name not in more_operator_day:
            continue
        more_operators = more_operator_day[care_unit_name]
        if len(more_operators) == 0:
            continue
        more_program = ""
        more_total_duration = 0
        for operator_name, operator in more_operators.items():
            more_program += "more(" + operator_name + ", " + str(operator["start"]) + ", " + str(operator["duration"]) + ").\n"
            more_total_duration += operator["duration"]
        for less_day_name, less_operator_day in operator_days.items():
            if less_day_name == more_day_name:
                continue
            if care_unit_name not in less_operator_day:
                lesser_days.append(less_day_name)
                continue
            less_operators = less_operator_day[care_unit_name]
            if len(less_operators) == 0:
                lesser_days.append(less_day_name)
                continue
            less_program = ""
            less_total_duration = 0
            unsatisfiable = False
            for operator_name, operator in less_operators.items():
                at_least_one = False
                for more_operator in more_operators.values():
                    if operator["start"] >= more_operator["start"] and operator["start"] + operator["duration"] <= more_operator["start"] + more_operator["duration"]:
                        at_least_one = True
                        break
                if not at_least_one:
                    unsatisfiable = True
                    break
                less_program += "less(" + operator_name + ", " + str(operator["start"]) + ", " + str(operator["duration"]) + ").\n"
                less_total_duration += operator["duration"]
            if unsatisfiable:
                continue
            if more_total_duration < less_total_duration:
                continue
            with open("input_program.lp", "w") as file:
                file.write(more_program)
                file.write(less_program)
            with open("results.txt", "w") as file:
                subprocess.run(["clingo", "input_program.lp", "subsumption_program.lp"], stdout=file, stderr=subprocess.DEVNULL)
            with open("results.txt") as file:
                if file.read().find("UNSATISFIABLE") < 0:
                    lesser_days.append(less_day_name)
        if len(lesser_days) > 0:
            subsumption[more_day_name] = lesser_days
    subsumptions[care_unit_name] = subsumption

if os.path.isfile("input_program.lp"):
    os.remove("input_program.lp")
if os.path.isfile("results.txt"):
    os.remove("results.txt")

end_time = datetime.now()

with open("subsumptions.json", "w") as file:
    file.write(json.dumps(subsumptions, indent=4, sort_keys=True))

print("Subsumptions are in the file 'subsumptions.json'")
print("Time taken: " + str(end_time - start_time))