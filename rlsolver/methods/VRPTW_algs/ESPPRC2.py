import sys
import os
cur_path = os.path.dirname(os.path.abspath(__file__))
rlsolver_path = os.path.join(cur_path, '../../../rlsolver')
sys.path.append(os.path.dirname(rlsolver_path))

import copy
import time
import networkx as nx
import operator
from Customer import Customer
from Vehicle import Vehicle
from typing import List, Tuple, Union, Dict
from rlsolver.methods.VRPTW_algs.config import (Config,
                    )
from typing import Dict, List
from rlsolver.methods.VRPTW_algs.Customer import (Customer,
                      )
from rlsolver.methods.VRPTW_algs.Vehicle import Vehicle
from rlsolver.methods.VRPTW_algs.util import (read_data,
                  generate_vehicles,
                  generate_customers_including_orig_dest,
                  generate_vehicles_and_assign_paths,
                  write_result_based_on_vehicles,
                  calc_dist_of_path,
                  obtain_paths_based_on_vehicles,
                  calc_demands_of_paths,
                  calc_durations_of_paths, )
from Label import Label
from util import (read_data_as_nxdigraph,
                  write_result,
                  calc_dists_of_paths)



def check(customers):
    for cust in customers:
        # Label.check(cust.labels)
        for i in range(len(cust.forward_labels)):
            li = cust.forward_labels[i]
            if cust.id not in li.path_denoted_by_names:
                aaa = 1
            for j in range(i + 1, len(cust.forward_labels)):
                lj = cust.forward_labels[j]
                if li == lj:
                    aaa = 1

def forward_loop(forward_customers_will_be_treated: List[Customer], customers: List[Customer], graph: nx.DiGraph):
    while len(forward_customers_will_be_treated) > 0:
        customer_i = forward_customers_will_be_treated.pop()
        for name_j in graph.successors(customer_i.name):
            customer_j = Customer.obtain_by_name(name_j, customers)
            labels_i_to_j = []  # labels extended from i to j
            for i in range(len(customer_i.forward_labels)):
                label = customer_i.forward_labels[i]
                exist = False
                for lj in customer_j.forward_labels:
                    if len(lj.path_denoted_by_names) >= 2 and lj.path_denoted_by_names[-2] == customer_i.id:
                        exist = True
                        break
                if exist:
                    continue
                label_i_to_j = Customer.extend_forward(customer_i, customer_j, label, graph)
                # if customer_i can reach customer_j, label_i_to_j is not None
                if label_i_to_j is not None:
                    labels_i_to_j.append(label_i_to_j)
            labels_j = copy.deepcopy(customer_j.forward_labels)
            labels_j.extend(labels_i_to_j)
            filtered_labels_j = Label.EFF(labels_j, True)
            change = Label.change(filtered_labels_j, customer_j.forward_labels)
            if change:
                customer_j.forward_labels = copy.deepcopy(filtered_labels_j)
                if customer_j not in forward_customers_will_be_treated:
                    forward_customers_will_be_treated.append(customer_j)

def backward_loop(backward_customers_will_be_treated: List[Customer], customers: List[Customer], graph: nx.DiGraph):
    while len(backward_customers_will_be_treated) > 0:
        customer_j2 = backward_customers_will_be_treated.pop()
        for name_i in graph.predecessors(customer_j2.name):
            customer_i: Customer = Customer.obtain_by_name(name_i, customers)
            labels_j_to_i = []  # labels extended from j to i
            for j in range(len(customer_j2.backward_labels)):
                label = customer_j2.backward_labels[j]
                exist = False
                for li in customer_i.backward_labels:
                    if len(li.path_denoted_by_names) >= 2 and li.path_denoted_by_names[1] == customer_j2.name:
                        exist = True
                        break
                if exist:
                    continue
                label_i_to_j = Customer.extend_backward(customer_j2, customer_i, label, customers, graph)
                # if customer_i can reach customer_j, label_i_to_j is not None
                if label_i_to_j is not None:
                    labels_j_to_i.append(label_i_to_j)
            labels_i = copy.deepcopy(customer_i.backward_labels)
            labels_i.extend(labels_j_to_i)
            filtered_labels_i = Label.EFF(labels_i, False)
            change = Label.change(filtered_labels_i, customer_i.forward_labels)
            if change:
                customer_i.backward_labels = copy.deepcopy(filtered_labels_i)
                if customer_i not in backward_customers_will_be_treated:
                    backward_customers_will_be_treated.append(customer_i)

def obtain_forward_paths(dest: Customer, graph: nx.DiGraph):
    # calc forward paths from orig to dest
    # dest = Customer.obtain_by_name(Config.DEST_NAME, customers)
    if dest is None:
        return [], []
    forward_paths = []
    if Config.SORT_BY_CUMULATIVE_TRAVEL_COST:
        dest.forward_labels.sort(key=operator.attrgetter('cumulative_travel_cost'))
    for i in range(len(dest.forward_labels)):
        label = dest.forward_labels[i]
        path = []
        for k in range(len(label.path_denoted_by_names)):
            this_name = label.path_denoted_by_names[k]
            path.append(this_name)
        if len(path) >= 2:
            forward_paths.append(path)
    forward_dists = calc_dists_of_paths(forward_paths, graph)
    return forward_paths, forward_dists

def obtain_backward_paths(orig: Customer, graph: nx.DiGraph):
    if orig is None:
        return [], []
    backward_paths = []
    if Config.SORT_BY_CUMULATIVE_TRAVEL_COST:
        orig.backward_labels.sort(key=operator.attrgetter('cumulative_travel_cost'))
    for i in range(len(orig.backward_labels)):
        label = orig.backward_labels[i]
        path = []
        for k in range(len(label.path_denoted_by_names)):
            this_name = label.path_denoted_by_names[k]
            path.append(this_name)
        if len(path) >= 2:
            backward_paths.append(path)
    backward_dists = calc_dists_of_paths(backward_paths, graph)
    return backward_paths, backward_dists

# vehicle_capacity: int, result_filename: str
# An exact algorithm for the elementary shortest path problem with resource constraints: Application to some vehicle routing problems
# return paths, each path is a list of customers' names
# paths are sorted by label's cumulative_travel_cost
def ESPPRC2_bidirectional(orig_name: str, dest_name: str, customers: List[Customer], graph: nx.DiGraph()) -> List[List[str]]:
    orig = Customer.obtain_by_name(orig_name, customers)
    orig_label: Label = Label.create_label_for_orig(True)
    orig.forward_labels = [orig_label]

    dest = Customer.obtain_by_name(dest_name, customers)
    dest_label: Label = Label.create_label_for_dest(False)
    dest.backward_labels = [dest_label]

    for customer in customers:
        if customer != orig:
            customer.forward_labels = []
        if customer != dest:
            customer.backward_labels = []
    forward_customers_will_be_treated = [orig]
    backward_customers_will_be_treated = [dest]

    # forward
    forward_loop(forward_customers_will_be_treated, customers, graph)
    dest = Customer.obtain_by_name(Config.DEST_NAME, customers)
    forward_paths, forward_dists = obtain_forward_paths(dest, graph)

    # backward
    backward_loop(backward_customers_will_be_treated, customers, graph)
    orig = Customer.obtain_by_name(Config.ORIG_NAME, customers)
    backward_paths, backward_dists = obtain_backward_paths(orig, graph)

    # join forward_paths and backward_paths
    paths = []
    dists = []

    return paths, dists


def check_nxgraph():
    g = nx.Graph()  # or MultiDiGraph, etc
    # nx.add_path(G, [0, 1, 2])
    g.add_edge(0, 1, weight=1)
    g.add_edge(1, 2, weight=1)
    g.add_edge(2, 3, weight=5)

    # G.edges.data()  # default data is {} (empty dict)
    # G.edges.data("weight", default=1)
    # G.edges([0, 2])  # only edges originating from these nodes
    edges0 = g.edges(1)  # only edges from node 0
    weights = nx.get_edge_attributes(g, 'weight')
    for i, j in weights.keys():
        weight = weights[(i, j)]
        print(f'weight of ({i},{j}): {weight}')
    print()


def demo():
    start_time = time.time()
    # 点属性: (demand, time_window_start, time_window_end, service_duration)
    nodes = {'s': (0, 0, 0, 0),
             '1': (1, 6, 14, 2),
             '2': (1, 9, 12, 2),
             '3': (1, 8, 12, 2),
             't': (1, 9, 15, 2)}
    # Nodes = {0: (0, 0, 0, 0)
    #     , 1: (1, 6, 14, 2)
    #     , 2: (1, 9, 12, 2)
    #     , 3: (1, 8, 12, 2)
    #     , 4: (1, 9, 15, 2)
    #          }
    # 弧的属性: (duration, dist)
    arcs = {('s', '1'): (8, 3),
            ('s', '2'): (5, 5),
            ('s', '3'): (8, 1),
            ('1', 't'): (4, 7),
            ('2', 't'): (2, 6),
            ('3', 't'): (4, 8)}

    # create the directed Graph
    graph = nx.DiGraph()
    cnt = 0
    customers = []
    # add nodes into the graph
    for name in nodes.keys():
        graph.add_node(name, time_window=(nodes[name][0], nodes[name][1]))
        node = nodes[name]
        customer: Customer = Customer(node[0], node[1], node[2], node[3])
        customer.id = cnt
        customer.name = name
        customers.append(customer)
        cnt += 1

    # add edges into the graph
    for key in arcs.keys():
        graph.add_edge(key[0], key[1], duration=arcs[key][0], cost=arcs[key][1], dist=arcs[key][1])

    # graph, filtered_labels, opt_labels = labeling_SPPRC(graph, org, des)
    Config.NUM_VEHICLES = len(nodes)
    Config.ORIG_NAME = "s"
    Config.DEST_NAME = "t"
    name_of_orig = Config.ORIG_NAME
    ESPPRC1_unidirectional(name_of_orig, customers, graph)
    vehicles = generate_vehicles_and_assign_paths(len(customers), customers)
    filtered_vehicles = vehicles[:Config.NUM_VEHICLES]
    running_duration = time.time() - start_time
    result_filename = "./result/demo.txt"
    alg_name = "ESPPRC1"
    paths = obtain_paths_based_on_vehicles(vehicles)
    dists = calc_dists_of_paths(paths, graph)
    demands = calc_demands_of_paths(vehicles)
    durations = calc_durations_of_paths(vehicles)
    write_result(result_filename, alg_name, paths, running_duration, dists, demands, durations)
    # write_result_based_on_vehicles(vehicles, alg_name, running_duration, result_filename)
    print("paths: ", paths)
    print("running_duration: ", running_duration)
    print()


def main():
    # assert Config.CONNECT_ORIG_DEST is False
    start_time = time.time()
    graph, customers = read_data_as_nxdigraph(Config.INSTANCE_FILENAME, Config.NUM_PURE_CUSTOMERS)
    orig_name = Config.ORIG_NAME
    dest_name = Config.DEST_NAME
    ESPPRC2_bidirectional(orig_name, dest_name, customers, graph)
    vehicles = generate_vehicles_and_assign_paths(len(customers), customers)
    filtered_vehicles = vehicles[:Config.NUM_VEHICLES]
    running_duration = time.time() - start_time
    result_filename = Config.RESULT_FILENAME
    alg_name = "ESPPRC1"
    paths = obtain_paths_based_on_vehicles(filtered_vehicles)
    dists = calc_dists_of_paths(paths, graph)
    demands = calc_demands_of_paths(filtered_vehicles)
    durations = calc_durations_of_paths(filtered_vehicles)
    write_result(result_filename, alg_name, paths, running_duration, dists, demands, durations)
    print("paths: ", paths)
    print("running_duration: ", running_duration)
    print()


if __name__ == '__main__':
    run_main = True
    if run_main:
        main()

    run_demo = False
    if run_demo:
        demo()

