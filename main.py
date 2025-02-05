from __future__ import annotations
import sys
from dataclasses import dataclass, field
from queue import Queue

IS_DEBUG_MODE = False

@dataclass
class Node:
    id : int
    adjacent_nodes: list[Link] = field(default_factory=list)
    is_gateway : bool = False
    gateway_ponderation : int | None = None
    dist_from_bobnet : int | None = None
    simulated_dist_fom_botnet : int | None = None

    def calculate_dangerous_node(self) -> bool:
        """Check if the current node is dangerous or not"""
        for link in self.adjacent_nodes:
            adjencent_node = link.next_node(self)
            if not link.is_unactivated and adjencent_node.is_gateway:
                return True
        return False

@dataclass
class Link:
    id : int
    nodes : tuple[Node, Node]
    is_unactivated : bool = False

    def next_node(self, previous_node : Node) -> Node:
        return self.nodes[0] if previous_node == self.nodes[1] else self.nodes[1]

class Game:
    def __init__(self, is_debug : bool = False):
        input_tab = [int(i) for i in input().split()]
        self.n :int = input_tab[0]
        self.l :int = input_tab[1]
        self.e :int = input_tab[2]
        self.all_nodes : dict[int, Node] = dict((i, Node(i)) for i in range(0, self.n))
        self.all_links : dict[int, Link] = {}
        self.gateway_nodes : dict[int, Node] = {}
        self.is_debug :bool = is_debug

        self.dangerous_nodes : dict[int, Node]= {}
        self.potential_nodes_to_cut_by_distance : dict[int, list[Node]] = {}

        for i in range(self.l):
            # n1: N1 and N2 defines a link between these nodes
            n1, n2 = [int(j) for j in input().split()]
            link = Link(id = i, nodes = (self.all_nodes[n1], self.all_nodes[n2]))
            self.all_nodes[n1].adjacent_nodes.append(link)
            self.all_nodes[n2].adjacent_nodes.append(link)
            self.all_links[i] = link

        for i in range(self.e):
            ei = int(input())  # the index of a gateway node
            self.all_nodes[ei].is_gateway = True
            self.gateway_nodes[ei] = self.all_nodes[ei]

        self.debug_print()

    def debug_print(self):
        """A debug print for game parameters which are initialized once"""
        if self.is_debug:
            print(f"Node number {self.n}", file=sys.stderr, flush=True)
            print(f"Link number {self.l}", file=sys.stderr, flush=True)
            print(f"Gateway number {self.e}", file=sys.stderr, flush=True)

    def in_loop_debug(self):
        """A debug print for game in loop parameters"""
        if self.is_debug:
            # Print Dangerous Nodes and Distances
            for node in self.dangerous_nodes.values():
                if node.dist_from_bobnet is not None:
                    print(f"Dangerous Node {node.id} at distance {node.dist_from_bobnet} and simulated distance {node.simulated_dist_fom_botnet}", file=sys.stderr, flush=True)

    def game_loop(self):
        """Main loop of the game"""
        # game loop
        while True:
            si = int(input())  # The index of the node on which the Bobnet agent is positioned this turn

            # Get bobnet node
            bobnet_node = self.all_nodes[si]

            # Identify dangerous nodes
            self.find_dangerous_nodes()

            # Check if nearby links (distance = 0)
            link_to_cut = self.immediate_link_to_cut(bobnet_node)

            # If no nearby links - Check distance to all dangerous nodes to prioritize links to cut
            if link_to_cut is None:
                 # Calculate distance to dangerous nodes
                self.caculate_dist_to_gateways(bobnet_node)
                # Order nodes by distance and select links
                self.dangerous_nodes_ordered_by_simulated_distance()
                link_to_cut = self.link_to_cut_from_dangerous_nodes()

            self.in_loop_debug()

            self.cut_link(link_to_cut) if link_to_cut is not None else None

    def caculate_dist_to_gateways(self, bobnet_node : Node) -> None:
        """Caculate distance between bobnet_node and dangerous nodes"""
        # Reset distance from Botnet to Dangerous nodes
        self.reset_dist_to_nodes()
        # Launch the algorithm
        self.caculate_dist_to_gateways_bfs(bobnet_node)

    def reset_dist_to_nodes(self) -> None:
        """Reset distance between bobnet_node and dangerous nodes"""
        for node in self.all_nodes.values():
            node.dist_from_bobnet = None
            node.simulated_dist_fom_botnet = None

    # Algo Queue Breadth-First Search (Parcours en largeur) - TODO Optimize this code to base it on dangerous nodes instead of links
    def caculate_dist_to_gateways_bfs(self, bobnet_node : Node) -> None:
        """Main algorithm for distance calculation based on BFS"""
        queue_bfs : Queue = Queue()
        current_node : Node = bobnet_node
        current_link : Link | None = None
        depth :int = 0
        dangerous_nodes_nb :int = 0

        queue_bfs.put([current_node, current_link, depth, dangerous_nodes_nb])

        processed_nodes : list[Node] = []
        processed_nodes.append(current_node)

        while not queue_bfs.empty():
            current_node, current_link, depth, dangerous_nodes_nb = queue_bfs.get()
            if current_node.is_gateway and current_link is not None:
                previous_node = current_link.next_node(current_node)
                if previous_node.dist_from_bobnet is None or previous_node.dist_from_bobnet > depth:
                    previous_node.dist_from_bobnet = depth - 1
                    previous_node.simulated_dist_fom_botnet = depth - 1 - (dangerous_nodes_nb - 1)
            elif depth == 0 or len(current_node.adjacent_nodes) > 1:
                for link in current_node.adjacent_nodes:
                    if (current_link  is None or link != current_link) and not link.is_unactivated:
                        adjacent_node = link.next_node(current_node)
                        if adjacent_node not in processed_nodes:
                            next_dangerous_nodes_nb = (dangerous_nodes_nb+1) if current_node.id in self.dangerous_nodes else dangerous_nodes_nb
                            queue_bfs.put([adjacent_node, link, depth + 1, next_dangerous_nodes_nb])
                            if not adjacent_node.is_gateway:
                                processed_nodes.append(adjacent_node)

    def cut_link(self, link_to_cut : Link):
        """Print the link to cut and unactivate it"""
        # Send value to print
        print(f"{link_to_cut.nodes[0].id} {link_to_cut.nodes[1].id}")
        # Update the link to ensure it is now considered as cut
        link_to_cut.is_unactivated = True

    def dangerous_nodes_ordered_by_simulated_distance(self):
        """Order nodes by simulated distance to prioritize the dangerous nodes by criticity"""
        potential_nodes_to_cut_by_distance : dict[int, list[Node]] = {}
        for node in self.all_nodes.values():
            if node.simulated_dist_fom_botnet is not None:
                n_gateway = 0
                for link in node.adjacent_nodes:
                    if not link.is_unactivated:
                        adjacent_node = link.next_node(node)
                        if adjacent_node.is_gateway:
                            n_gateway += 1
                distance = node.simulated_dist_fom_botnet - (n_gateway - 1)
                if distance in potential_nodes_to_cut_by_distance:
                    potential_nodes_to_cut_by_distance[distance].append(node)
                else:
                    potential_nodes_to_cut_by_distance[distance] = [node]

        self.potential_nodes_to_cut_by_distance = dict(sorted(potential_nodes_to_cut_by_distance.items()))

    def link_to_cut_from_dangerous_nodes(self) -> Link | None:
        """Extract the first link to cut from the most critical dangerous node"""
        first_node : Node = self.potential_nodes_to_cut_by_distance[next(iter(self.potential_nodes_to_cut_by_distance.keys()))][0]
        for link in first_node.adjacent_nodes:
            if not link.is_unactivated and link.next_node(first_node).is_gateway:
                return link
        return None

    def immediate_link_to_cut(self, bobnet_node : Node) -> Link | None:
        """Check if there is an adjacent link critical to cut this turn, if yes this link is returned"""
        for link in bobnet_node.adjacent_nodes:
            if not link.is_unactivated and link.next_node(bobnet_node).is_gateway:
                return link
        return None

    def find_dangerous_nodes(self):
        """Find and save all dangerous nodes"""
        if len(self.dangerous_nodes) == 0:
            for node in self.all_nodes.values():
                is_dangerous_node = node.calculate_dangerous_node()
                if is_dangerous_node:
                    self.dangerous_nodes[node.id] = node
        else:
            dangerous_nodes_copy = dict(self.dangerous_nodes)
            self.dangerous_nodes = {}
            for node in dangerous_nodes_copy.values():
                is_dangerous_node = node.calculate_dangerous_node()
                if is_dangerous_node:
                    self.dangerous_nodes[node.id] = node


game = Game(IS_DEBUG_MODE)
game.game_loop()