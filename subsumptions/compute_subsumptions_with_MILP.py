import os
import sys
import json
from datetime import datetime

from pyomo.environ import ConcreteModel, Binary, maximize, SolverFactory, TerminationCondition
from pyomo.environ import Set, Var, Objective, Constraint

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
        more_total_duration = 0
        for operator_name, operator in more_operators.items():
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
                less_total_duration += operator["duration"]
            if unsatisfiable or more_total_duration < less_total_duration:
                continue
            less_indexes = []
            for less_operator_name in less_operators.keys():
                less_indexes.append(less_operator_name)
            x_indexes = []
            for more_operator_name, more_operator in more_operators.items():
                for less_operator_name, less_operator in less_operators.items():
                    if less_operator["start"] >= more_operator["start"] and less_operator["start"] + less_operator["duration"] <= more_operator["start"] + more_operator["duration"]:
                        x_indexes.append((less_operator_name, more_operator_name))
            if len(x_indexes) == 1:
                lesser_days.append(less_day_name)
                continue
            no_overlap_indexes = []
            for index1 in range(len(x_indexes) - 1):
                for index2 in range(index1 + 1, len(x_indexes)):
                    less_operator_name1, more_operator_name1 = x_indexes[index1]
                    less_operator_name2, more_operator_name2 = x_indexes[index2]
                    if less_operator_name1 != less_operator_name2 and more_operator_name1 == more_operator_name2:
                        if (less_operators[less_operator_name1]["start"] <= less_operators[less_operator_name2]["start"] and less_operators[less_operator_name1]["start"] + less_operators[less_operator_name1]["duration"] > less_operators[less_operator_name2]["start"] or
                            less_operators[less_operator_name2]["start"] <= less_operators[less_operator_name1]["start"] and less_operators[less_operator_name2]["start"] + less_operators[less_operator_name2]["duration"] > less_operators[less_operator_name1]["start"]):
                            no_overlap_indexes.append((less_operator_name1, less_operator_name2, more_operator_name1))
            model = ConcreteModel()
            model.x_indexes = Set(initialize=x_indexes)
            model.no_overlap_indexes = Set(initialize=no_overlap_indexes)
            model.less_indexes = Set(initialize=less_indexes)
            model.x = Var(model.x_indexes, domain=Binary)
            def f(model):
                return sum([model.x[less_index, more_index] for less_index, more_index in model.x_indexes])
            model.objective = Objective(rule=f, sense=maximize)
            def f1(model, less_index1, less_index2, more_index):
                return model.x[less_index1, more_index] + model.x[less_index2, more_index] == 1
            model.no_overlap = Constraint(model.no_overlap_indexes, rule=f1)
            def f2(model, less_index):
                return sum([model.x[less_index, more_index] for (l, more_index) in model.x_indexes if l == less_index]) == 1
            model.only_one = Constraint(model.less_indexes, rule=f2)
            opt = SolverFactory('glpk')
            results = opt.solve(model)
            if results.solver.termination_condition != TerminationCondition.infeasible:
                lesser_days.append(less_day_name)
        if len(lesser_days) > 0:
            subsumption[more_day_name] = lesser_days
    subsumptions[care_unit_name] = subsumption
del care_unit_name, care_unit_names, subsumption, more_day_name, more_operator_day, lesser_days, more_operators, more_total_duration, operator_name, operator, less_day_name, less_operator_day, less_operators, less_total_duration, unsatisfiable, at_least_one, more_operator, x_indexes, no_overlap_indexes, less_indexes, model, opt, results

end_time = datetime.now()

with open("subsumptions.json", "w") as file:
    file.write(json.dumps(subsumptions, indent=4, sort_keys=True))

print("Subsumptions are in the file 'subsumptions.json'")
print("Time taken: " + str(end_time - start_time))