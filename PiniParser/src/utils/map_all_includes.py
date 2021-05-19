from utils.include_finder import IncludeFinder
import os
from anytree import Node, RenderTree
from anytree.exporter import DotExporter
import networkx as nx
import matplotlib.pyplot as plt
from typing import Dict, List, Set, Callable
import re


PATH_TO_DIR = "/home/darkskylo/Projects/compi/pyParser/ffmpeg-h264-dec"
MAIN_NAME = "/home/darkskylo/Projects/compi/pyParser/ffmpeg-h264-dec/main.c"

FUNCTION_PREFIX = "FUNC@@@/"


class ProjectGraph():
    def __init__(self, main_path=MAIN_NAME, path_to_dir=PATH_TO_DIR):
        self.function_counter = dict()
        self.path_to_main = main_path
        self.path_to_dir = path_to_dir
        self.g, self.gca = self.generate_graph()

    def find_all_c_files(self, c_files_found: List[str]):
        """
        finds all c_files from the given root specified in path_to_dir
        """
        
        for root, _, files in os.walk(self.path_to_dir):
            for filename in files:
                full_path = os.path.join(root, filename)
                if filename.endswith(".c"):
                    c_files_found.append(full_path)

    def _get_all_parents(self, tree: Node, node_name: str, output_parents: List[str]):
        """
        Helper function, appends all parents of a given node into output_parents
        """

        if node_name in [node.name for node in tree.children]:
            output_parents.append(tree.name)

        for child in tree.children:
            self._get_all_parents(child, node_name, output_parents)

    def get_all_parents(self, tree: Node, node_name: str):
        """Returns all parent of a given node


        Args:
            tree (Node): the ast of the file
            node_name (str): the string representing the node name

        Returns:
            [type]: a list of all the parents of the node
        """

        parents = []
        self._get_all_parents(tree, node_name, parents)

        return parents

    def get_function_declaring_parent(self, tree: Node, function_name: str, serial_number: int) -> str:
        """When given a function name, find the parent in which the function is declared.

        Args:
            tree (Node): the ast of the file
            function_name (str): the name of the function
            serial_number (int): the function serial number (if there is more than one function with same name)

        Raises:
            Exception: Function implementation nout found, the function is not implemented
            Exception: Too many implementations were found for function

        Returns:
            [str]: The name of the file in which the function is declared
        """

        declared_parents = [parent for parent in self.get_all_parents(tree, FUNCTION_PREFIX + function_name + "/" + str(
            serial_number)) if ProjectGraph.is_function_declared_in_file(parent, function_name)]
        if len(declared_parents) == 0:
            raise Exception(
                f"Function [{function_name}] implementation not found")
        if len(declared_parents) > 1:
            raise Exception(
                f"Found too many implementations for function {function_name}")

        return declared_parents[0]

    def get_function_node(self, gca: Node, function_name: str, file_name: str) -> Node:
        """get a function node using the name of the function only.
        This is done by finding a node that has the specified name and there is a path from the file node to it.

        Args:
            gca (Node): the tree to search on
            function_name (str): the name of the function to find
            file_name (str): the current file name

        Returns:
            [Node]: the node found
        """
        matching_functions = ProjectGraph.find_all_nodes_with_matching_prefix(
            gca, function_name)
        # this is very slow and can be optimized
        G = nx.DiGraph()
        self.to_nx_graph(gca, G)
        for matching_func in matching_functions:
            if self.is_path_exists(file_name, matching_func, G):
                return matching_func

        if function_name in self.function_counter:
            self.function_counter[function_name] += 1
        else:
            self.function_counter[function_name] = 1

        return ProjectGraph.get_function_as_node_name(function_name, self.function_counter[function_name])

    def find_children_and_add(self, tree: Node, found: List[Node], gca: Node):
        """This function is used to build the graph. find all children from the static includes
        and use them as children in the graph.

        Args:
            tree (Node): the subtree to add to
            found (List[Node]): list of files there were already found by the algorithm (and their order)
            gca (Node): the root of the tree
        """
        found.add(tree.name)
        static = self.find_all_includes(tree.name)

        for child in static:
            Node(self.find_full_path(child), parent=tree)

        for child_node in tree.children:
            if child_node.name not in found and not child_node.name.startswith(FUNCTION_PREFIX):
                self.find_children_and_add(child_node, found, gca)

        if tree.name != "START":
            full_name = self.find_full_path(tree.name)
            with open(full_name, "r") as fd:
                data = fd.read()
                functions = self.get_all_functions(data)
                for function in functions:
                    function_node = self.get_function_node(
                        gca, function, full_name)
                    Node(function_node, parent=tree)

    def to_nx_graph(self, node: Node, G):
        """Covnert the graph to nx graph (to run complex tree algorithms already implemented in nx graph).

        Args:
            node (Node): root to convert from
            G ([type]): output nx graph
        """
        G.add_nodes_from([x.name for x in node.children])
        G.add_edges_from([(node.name, child.name) for child in node.children])

        for child in node.children:
            self.to_nx_graph(child, G)

    def generate_graph(self):
        """generate the graph of includes from a given start file (self.path_to_main).

        Returns:
            [Tuple[Node, nx.DiGraph]]: [a graph representation of the includes, same graph as nx graph]
        """
        gca = Node("START")
        my_node = Node(self.path_to_main, gca)
        found = set()
        self.find_children_and_add(my_node, found, gca)

        c_files = []
        self.find_all_c_files(c_files)
        c_files.remove(self.path_to_main)

        for filename in c_files:
            c_node = Node(filename, gca)
            self.find_children_and_add(c_node, found, gca)

        DotExporter(gca).to_picture("my_includes.png")
        G = nx.DiGraph()
        self.to_nx_graph(gca, G)

        return G, gca

    def find_full_path(self, filename: str):
        """find the full path of a filename.
        This is not a great way to do it since it assumes the file names are uniqe.

        Args:
            filename (str): The name of the file

        Raises:
            Exception: if file can't be found

        Returns:
            [str]: file full path
        """
        filename = filename.split("/")[-1]
        for root, _, files in os.walk(self.path_to_dir):
            for file_n in files:
                if file_n == filename:
                    return os.path.join(root, filename)

        raise Exception(f"{filename} not found")

    def is_path_exists_to_function(self, filename: str, dest_function: str):
        """is there a path from a file node specified to a function node specified.

        Args:
            filename (str): the name of the current file - the dest node.
            dest_function (str): the name of the function we should search

        Returns:
            bool: True if such path exist and False otherwise
        """

        for function_index in range(1, self.function_counter[dest_function] + 1):
            if self.is_path_exists(filename, ProjectGraph.get_function_as_node_name(dest_function, function_index), self.g):
                return True, function_index

        return False, 0

    @staticmethod
    def get_function_as_node_name(function_name: str, serial_number: int) -> str:
        """Given a function. it node name deffers from the function name.
        It is given a function prefix and serial number (Since 2 function can have the same name in the same projects).
        The function_node_name is: FUNCTION_PREFIX + [real name] + "/" + [serial number]

        Args:
            function_name (str): actual name of the function
            serial_number (int): The serial number

        Returns:
            str: the function node name
        """
        return FUNCTION_PREFIX + function_name + "/" + str(serial_number)

    @staticmethod
    def find_all_includes(filename: str) -> List[str]:
        """Find all static includes in a file.
        A static include is an include that is being included with \"\" and not <>.
        This is obviously not mandatory for a project and <> can be also used for static includes
        but that is your problem. Make sure you follow the standart.

        Args:
            filename (str): The name of the file to find it's includes

        Returns:
            List[str] : names of all files that were included
        """

        include_finder = IncludeFinder(filename)
        static, _ = include_finder.find_all()
        return static

    @staticmethod
    def get_all_functions(data: str):
        """Get all functions [definition or declerations] names from a file.

        Args:
            data (str): content of the file to search

        Returns:
            [List[str]]: names of functions found
        """

        regex = r"(\w+\s)+(\w+)\(.*\)"
        new_data = re.findall(regex, data)

        return [tup[1] for tup in new_data]

    @staticmethod
    def is_function_declared_in_file(file_name: str, function_name: str) -> bool:
        """Checks whether a funciton is declared (implemented) in a file.

        Args:
            file_name (str): name of the file to check
            function_name (str): the name of the function

        Returns:
            [bool]: True if declared, False otherwise
        """

        with open(file_name, "r") as fd:
            content = fd.read()

        regex = function_name + "\(.*\)\s*\{"
        matches = re.findall(regex, content)

        return matches != []

    @staticmethod
    def remove_static_includes(data: str) -> str:
        """Remove all static includes from a given file.

        Args:
            data (str): content of the file

        Returns:
            [str]: content with the static includes removed
        """

        regex = r"(?=#include \".*\")(?!.*template\.c\").*"
        exons = re.sub(regex, '', data)

        return exons

    @staticmethod
    def find_conditional_node(tree: Node, name: str, cond_func: Callable[[str, str], bool]):
        if cond_func(name, tree.name):
            return tree

        for child in tree.children:
            node = find_conditional_node(child, name, cond_func)
            if node is not None:
                return node

        return None

    @staticmethod
    def find_node_with_matching_prefix(tree: Node, name: str) -> Node:
        """Find a node with a matching prefix in a given tree.

        Args:
            tree (Node): The tree to search
            name (str): prefix to match in the tree

        Returns:
            [Node]: node found
        """
        return ProjectGraph.find_conditional_node(tree, name, lambda x, y: y.startswith(x))

    @staticmethod
    def _find_all_nodes_with_matching_prefix(tree: Node, name: str, o_found_nodes: List[Node]):
        """Helper method to find all nodes with a matching prefix in a given tree.

        Args:
            tree (Node): The tree to search
            name (str): prefix to match in the tree
            o_found_nodes ([List[Node]]): output nodes that were found
        """

        processed_name = tree.name
        if tree.name.startswith(FUNCTION_PREFIX):
            processed_name = tree.name[len(FUNCTION_PREFIX):]

        if processed_name.startswith(name):
            o_found_nodes.append(tree.name)

        for child in tree.children:
            ProjectGraph._find_all_nodes_with_matching_prefix(
                child, name, o_found_nodes)

    @staticmethod
    def find_all_nodes_with_matching_prefix(tree: Node, name: str):
        """Find all nodes with a matching prefix in a given tree, wrapper to prevoius function.

        Args:
            tree (Node): The tree to search
            name (str): prefix to match in the tree

        Returns:
            [List[Node]]: List of nodes that were found
        """

        found_nodes = []
        ProjectGraph._find_all_nodes_with_matching_prefix(
            tree, name, found_nodes)
        return found_nodes

    @staticmethod
    def find_node(tree: Node, name: str):
        """find a node using it's name.

        Args:
            tree (Node): the tree to search
            name (str): the name to search in the tree

        Returns:
            [Node]: the node found and None if not found
        """

        return ProjectGraph.find_conditional_node(tree, name, lambda x, y: x == y)

    @staticmethod
    def is_path_exists(source: Node, dest: Node, graph: nx.DiGraph) -> bool:
        """Checks whether there exist a path from source to dest in the given graph.

        Args:
            source (nx.Node): source node
            dest (nx.Node): destination node
            graph (nx.Graph): graph

        Returns:
            [bool]: True if such path exists, False otherwise
        """

        return nx.has_path(graph, source, dest)
    

if __name__ == "__main__":
    project_graph = ProjectGraph()
    print("generated graph g")
