import sys
import os
cur_path = os.path.dirname(os.path.abspath(__file__))
rlsolver_path = os.path.join(cur_path, '../../../rlsolver')
sys.path.append(os.path.dirname(rlsolver_path))

import copy
from typing import Dict, List

import networkx as nx

from rlsolver.methods.VRPTW_algs.Label import Label
import numpy as np
from typing import Optional
from rlsolver.methods.VRPTW_algs.config import Config
import sys


class Customer:
    count = 0
    def __init__(self, demand, time_window_start, time_window_end, service_duration):
        # self.id: int = Customer.count
        self.id = Customer.count
        Customer.count += 1
        self.name = str(self.id)
        self.demand: int = demand
        self.time_window = (time_window_start, time_window_end)
        self.service_duration: float = service_duration
        self.is_path_planned: bool = False
        self.labels: List[Label] = []
        self.is_visited = False
        # self.ids_of_successors: List[int] = self.calc_ids_of_successors()
        self.is_depot: bool = False
        self.is_orig: bool = False
        self.is_dest: bool = False

    def __eq__(self, other):
        return self.name == other.name

    @staticmethod
    def obtain_by_name(name_of_cust, customers):
        if name_of_cust.isdigit() and int(name_of_cust) < len(customers):
            cust = customers[int(name_of_cust)]
            if cust.name == name_of_cust:
                return cust
        res = None
        for cust in customers:
            if cust.name == name_of_cust:
                res = cust
                break
        return res

    @staticmethod
    def obtain_index_by_id(id_of_cust, customers):
        res = None
        for i in range(len(customers)):
            cust = customers[i]
            if cust.id == id_of_cust:
                res = i
                break
        return res

    @staticmethod
    def calc_arrival_departure_time(prev_departure, prev, this, graph: nx.DiGraph) -> (bool, float, float):
        if  (prev.name, this.name) not in graph.edges or "duration" not in graph.edges[(prev.name, this.name)]:
            aaa = 1
        arrival = prev_departure + graph.edges[(prev.name, this.name)]["duration"]
        if arrival <= this.time_window[1]:
            feasible = True
            start_service = max(arrival, this.time_window[0])
            departure = start_service + this.service_duration
            return feasible, arrival, departure
        else:
            feasible = False
            return feasible, -1, -1



    # if customer_i can reach customer_j, the return is not None
    @staticmethod
    def extend(this_customer, another_customer, this_label: Label, graph: nx.DiGraph) -> Optional[Label]:
        if this_label.path_denoted_by_names[-1] != this_customer.name or another_customer.name in this_label.path_denoted_by_names:
            return None
        cumulative_demand = this_label.cumulative_demand + another_customer.demand
        arrival_time = this_label.departure_time_list[-1] + graph.edges[(this_customer.name, another_customer.name)]["duration"]
        if arrival_time <= another_customer.time_window[1] and cumulative_demand < Config.VEHICLE_CAPACITY:
            label = copy.deepcopy(this_label)
            label.id = Label.count
            label.name = str(label.id)
            Label.count += 1
            departure_time = max(arrival_time, another_customer.time_window[0]) + another_customer.service_duration
            label.cumulative_travel_cost += graph.edges[(this_customer.name, another_customer.name)]["cost"]
            label.cumulative_duration = departure_time
            label.cumulative_demand = cumulative_demand
            label.visitation_vector[another_customer.id] = True
            label.path_denoted_by_names.append(another_customer.name)
            label.arrival_time_list.append(arrival_time)
            label.departure_time_list.append(departure_time)
            return label
        else:
            return None



    def calc_labels_extend_to_another(self, another_customer) -> List[Label]:
        labels = []
        for label in self.labels:
            if len(label.path_denoted_by_names) >= 2 and label.path_denoted_by_names[-2] == self.id and label.path_denoted_by_names[-1] == another_customer.id:
                labels.append(label)
        return labels



    # # used in impact_heuristic
    # def calc_own_impact_IS(self, vehicle: Vehicle) -> List[float]:
    #     IS = []
    #     for i in range(len(vehicle.paths_if_insert)):
    #         if self.id in vehicle.arrival_time_list_if_insert[i].keys():
    #             Is = vehicle.arrival_time_list_if_insert[i][self.id] - self.time_window[0]
    #             IS.append(Is)
    #     return IS
    #
    # # used in impact_heuristic
    # def calc_external_impact_IU(self, nonrouted_customers: List) -> float:
    #     num_nonrouted_customers = len(nonrouted_customers)
    #     sum_Iu = 0
    #     for customer in nonrouted_customers:
    #         if self.id != customer.id:
    #             Iu = max(customer.time_window[1] - self.time_window[0] - Config.TRAVEL_DURATION_MATRIX[self.id][customer.id], self.time_window[1] - customer.time_window[0] - Config.TRAVEL_DURATION_MATRIX[self.id][customer.id])
    #             sum_Iu += Iu
    #     IU = sum_Iu / (num_nonrouted_customers - 1 + 1e-8)
    #     return IU
    #
    # # used in impact_heuristic
    # def calc_local_disturbance_LD(self, vehicle: Vehicle) -> List[float]:
    #     LD = []
    #     for m in range(len(vehicle.paths_if_insert)):
    #         path = vehicle.paths_if_insert[m]
    #         for k in range(len(path)):
    #             customer = path[k]
    #             if customer.id == self.id:
    #                 i = k - 1
    #                 j = k + 1
    #                 id_i = path[i].id
    #                 id_j = path[j].id
    #                 customer_i = path[i]
    #                 customer_j = path[j]
    #                 c1 = Config.TRAVEL_DIST_MATRIX[id_i][self.id] + Config.TRAVEL_DIST_MATRIX[self.id][id_j] - Config.TRAVEL_DIST_MATRIX[id_i][id_j]
    #                 c2 = (customer_j.time_window[1] - (vehicle.arrival_time_list_if_insert[m][id_i] + customer_i.service_duration + Config.TRAVEL_DURATION_MATRIX[id_i][id_j])) \
    #                      - (customer_j.time_window[1] - (vehicle.arrival_time_list_if_insert[m][self.id] + self.service_duration + Config.TRAVEL_DURATION_MATRIX[self.id][id_j]))
    #                 c3 = self.time_window[1] - (vehicle.arrival_time_list_if_insert[m][id_i] + customer_i.service_duration + Config.TRAVEL_DURATION_MATRIX[id_i][self.id])
    #                 Ld = Config.B1 * c1 + Config.B2 * c2 + Config.B3 * c3
    #                 LD.append(Ld)
    #                 break
    #     return LD
    #
    #
    # # used in impact_heuristic
    # def calc_global_disturbance_IR(self, vehicle: Vehicle) -> float:
    #     LD = self.calc_local_disturbance_LD(vehicle)
    #     IR = np.average(LD)
    #     return IR
    #
    # # used in impact_heuristic
    # def calc_internal_impact_accessibility_ACC(self, vehicle: Vehicle):
    #     IR = self.calc_global_disturbance_IR(vehicle)
    #     ACC = 1 / IR
    #     return ACC
    #
    # # used in impact_heuristic
    # def calc_impact(self, vehicle: Vehicle, nonrouted_customers: List):
    #     success = False
    #     for i in range(1, len(vehicle.path)):
    #         succeed = vehicle.succeed_insert_customer(i, self)
    #         if succeed:
    #             success = True
    #             vehicle.arrival_time_list_if_insert.append(vehicle.arrival_time_dict_if_insert)
    #             vehicle.departure_time_list_if_insert.append(vehicle.departure_time_dict_if_insert)
    #             path_if_insert = copy.deepcopy(vehicle.path_if_insert)
    #             vehicle.paths_if_insert.append(path_if_insert)
    #             vehicle.clear_if_insert3()
    #     if not success:
    #         return Config.INF
    #     Is = self.calc_own_impact_IS(vehicle)
    #     IS = np.average(Is)
    #     IU = self.calc_external_impact_IU(nonrouted_customers)
    #     IR = self.calc_global_disturbance_IR(vehicle)
    #     impact = (float) (Config.Bs * IS + Config.Be * IU + Config.Br * IR)
    #     return impact
    #
    # # used in impact_heuristic
    # def calc_vehicle_with_min_impact(self, vehicles: List[Vehicle], nonrouted_customers: List):
    #     min_impact = Config.INF
    #     selected_vehicle = None
    #     for vehicle in vehicles:
    #         vehicle.clear_if_insert6()
    #         impact = self.calc_impact(vehicle, nonrouted_customers)
    #         if impact < min_impact:
    #             min_impact = impact
    #             selected_vehicle = vehicle
    #     return selected_vehicle, min_impact











