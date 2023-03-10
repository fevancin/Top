import os
import sys
import json
import subprocess
from datetime import datetime

# initial directory movements
os.chdir(os.path.dirname(sys.argv[0]))
os.chdir("..")
if not os.path.isdir("instance"):
    print("Instance folder not found")
    exit(-1)
os.chdir("instance")

# read the operator intervals
with open("operators.json", "r") as file:
    operator_days = json.loads(file.read())

os.chdir("..")
os.chdir("subsumptions")

start_time = datetime.now()

# list all the care_units in the input
care_unit_names = set()
for operator_day in operator_days.values():
    for care_unit_name in operator_day.keys():
        care_unit_names.add(care_unit_name)
del operator_day, care_unit_name

subsumptions = dict()
for care_unit_name in care_unit_names:
    subsumption = dict()
    for more_day_name, more_operator_day in operator_days.items():
        lesser_days = [] # here there will be inserted each day <= more_day_name
        if care_unit_name not in more_operator_day:
            continue # an empty care_unit means no lesser days are possible
        more_operators = more_operator_day[care_unit_name]
        if len(more_operators) == 0:
            continue # if there are no operators no lesser days are possible
        more_program = "" # stringify the operarator data for the ASP solver
        more_total_duration = 0
        for operator_name, operator in more_operators.items():
            more_program += f"more({operator_name}, {operator['start']}, {operator['duration']}).\n"
            more_total_duration += operator['duration']
        for less_day_name, less_operator_day in operator_days.items(): # check each other day for <=
            if less_day_name == more_day_name:
                continue # jump the same day
            if care_unit_name not in less_operator_day:
                lesser_days.append(less_day_name)
                continue # if no operators are available the day is sure less
            less_operators = less_operator_day[care_unit_name]
            if len(less_operators) == 0:
                lesser_days.append(less_day_name)
                continue # same short-circuit as above
            less_program = "" # building of the other part of the ASP input program
            less_total_duration = 0
            unsatisfiable = False
            for operator_name, operator in less_operators.items():
                at_least_one = False
                for more_operator in more_operators.values():
                    if operator['start'] >= more_operator['start'] and operator['start'] + operator['duration'] <= more_operator['start'] + more_operator['duration']:
                        at_least_one = True
                        break
                if not at_least_one:
                    unsatisfiable = True
                    break # there must be at least one more_operator that could contain every less_operator
                less_program += f"less({operator_name}, {operator['start']}, {operator['duration']}).\n"
                less_total_duration += operator['duration']
            if unsatisfiable or more_total_duration < less_total_duration:
                continue # other checks for direct incompatibility
            if len(less_operators) == 1:
                lesser_days.append(less_day_name)
                continue # no need to solve if there is only one less_operator
            with open("input_program.lp", "w") as file:
                file.write(more_program)
                file.write(less_program)
            with open("results.txt", "w") as file:
                subprocess.run(["clingo", "input_program.lp", "subsumption_program.lp"], stdout=file, stderr=subprocess.DEVNULL)
            with open("results.txt", "r") as file:
                if file.read().find("UNSATISFIABLE") < 0: # reads the output result of the ASP solver
                    lesser_days.append(less_day_name)
        if len(lesser_days) > 0: # do not insert empty lists in the dictionary
            subsumption[more_day_name] = lesser_days
    subsumptions[care_unit_name] = subsumption
del care_unit_name, care_unit_names, subsumption, more_day_name, more_operator_day, lesser_days, more_operators, more_program, more_total_duration, operator_name, operator, less_day_name, less_operator_day, less_operators, less_program, less_total_duration, unsatisfiable, at_least_one, more_operator

# remove temporary work files
if os.path.isfile("input_program.lp"):
    os.remove("input_program.lp")
if os.path.isfile("results.txt"):
    os.remove("results.txt")

end_time = datetime.now()

# output subsumptions to a json file
with open("subsumptions.json", "w") as file:
    file.write(json.dumps(subsumptions, indent=4, sort_keys=True))

print("Subsumptions are in the file 'subsumptions.json'")
print(f"Time taken: {end_time - start_time}")