import argparse
import copy
import sys
from typing import Dict, List, Set, Tuple
import os
from pycparser import c_ast, c_parser, parse_file
import utils.map_all_includes as mai
from scope_record import ScopeRecord, ScopesList
from log import Log


sys.path.insert(1, 'C:\\Users\\User\\Documents\\Code\\PiniParser\\pycparser')
DEBUG_FILE = "output/functions_not_found.log"
DELIMITER = "@"


class PiniParser():
    def __init__(self, marked: Set[str], start_func: str = "main", filename: str = "", graph_manager=None, debug_file=DEBUG_FILE):
        self.marked = marked
        self.start_func = start_func
        self.functions = dict()
        self.filename = filename
        self.linked_functions = dict()
        self.graph_manager = graph_manager
        self.logger = Log(debug_file)

    def get_marked(self):
        """Returns all marked variables"""
        return self.marked

    def get_functions(self):
        """Returns a set of all functions found"""
        return self.functions.keys()

    def parse(self, ast: c_ast.Node, context: str, scopes: ScopesList = ScopesList(), decl_history: Set[str] = set()) -> List[str]:
        children = ast.children()

        """ Parses a given syntax tree and marks all pini-variables.
        The marked variables will be appended into self.marked with their full path.

        :type self: PiniParser
        :param self: The object of the class

        :type ast: c_ast.Node 
        :param ast: the syntax tree given for parsing

        :type context: string
        :param context: the current context of the parsing (scopes)

        :type scopes: ScopesList
        :param scopes: a list of counter for [if/for/while/else] so we could know which scope are we in.

        :rtype: bool
        """
        if len(children) == 0:
            return True

        for name, child in children:
            if type(child) is c_ast.Typedef:
                continue

            elif type(child) is c_ast.Decl:
                self.handle_decl(child, context, decl_history)

            elif type(child) is c_ast.FuncDef:
                if child.decl.name == self.start_func:
                    self.parse(child, PiniParser.contextify(PiniParser.contextify_list(
                        [self.filename, self.start_func]), context), copy.deepcopy(scopes))
                else:
                    self.functions[child.decl.name] = child

            elif type(child) is c_ast.Compound:
                new_scopes = copy.deepcopy(scopes)
                new_context = context

                if name == "iftrue":
                    new_scopes["if"].append(1)
                    new_context = context + f"if[{str(scopes['if'])}]@"

                elif name == "iffalse":
                    new_scopes["else"].append(1)
                    new_context = context + f"else[{str(scopes['else'])}]@"

                self.parse(child, new_context, new_scopes)

                if name == "iffalse" or name == "iftrue":
                    scopes["if"] += 1

            elif type(child) is c_ast.FuncCall:
                self.parse_called_function(child, context, dict)

            elif type(child) is c_ast.Assignment:
                self.handle_decl(child, context, decl_history)

            elif type(child) is c_ast.If:
                self.handle_if(child, context, scopes, decl_history)
                scopes["if"] += 1

            elif type(child) is c_ast.BinaryOp:
                self.handle_binary_op(child, context, decl_history)

            elif type(child) is c_ast.For:
                print(scopes["for"])
                self.handle_loop(child, context,  copy.deepcopy(
                    scopes), "for", decl_history)
                scopes["for"] += 1

            elif type(child) is c_ast.While:
                print(scopes["while"])
                self.handle_loop(
                    child, context,  copy.deepcopy(scopes), "while", decl_history)
                scopes["while"] += 1

            elif type(child) is c_ast.DoWhile:
                print(scopes["dowhile"])
                self.handle_loop(
                    child, context,  copy.deepcopy(scopes), "dowhile", decl_history)
                scopes["dowhile"] += 1

            elif type(child) is c_ast.DeclList:
                self.parse(child, context, copy.deepcopy(scopes), decl_history)

            elif type(child) is c_ast.Switch:
                self.parse(child, context, copy.deepcopy(scopes), decl_history)

            elif type(child) is c_ast.Case:
                self.parse(child, context, copy.deepcopy(scopes), decl_history)

            # @===================@
            # |   CONTINUE ZONE   |
            # @===================@

            elif type(child) is c_ast.UnaryOp:
                continue

            elif type(child) is c_ast.Break:
                continue

            elif type(child) is c_ast.Constant:
                continue

            elif type(child) is c_ast.Continue:
                continue

            elif type(child) is c_ast.FuncDecl:
                continue

            # this may cause problems, check if needed
            elif type(child) is c_ast.Goto:
                continue

            elif type(child) is c_ast.EmptyStatement:
                continue

            # I have no idea what a type decl is
            elif type(child) is c_ast.TypeDecl:
                print("Type declare found wtf is that?")
                continue

            elif type(child) is c_ast.Label:
                continue

            elif type(child) is c_ast.Cast:
                continue

            elif type(child) is c_ast.Struct:
                continue

            elif type(child) is c_ast.TernaryOp:
                continue

            elif type(child) is c_ast.Union:
                continue

            elif type(child) is c_ast.ArrayRef:
                continue

            elif type(child) is c_ast.ArrayDecl:
                continue

            elif type(child) is c_ast.Enum:
                continue

            elif type(child) is c_ast.PtrDecl:
                print("ptr declare found")
                continue

            # We handle every variadic param as
            elif type(child) is c_ast.EllipsisParam:
                continue

    def stringify_lvalue(self, ast: c_ast.Node) -> str:
        """given an lvalue, return a string value representing this lvalue.

        Args:
            ast (c_ast.Node): the abstract syntax tree of the given lvalue

        Returns:
            str: a string represents the given lvalue
        """

        if type(ast) is c_ast.StructRef:
            return self.stringify_lvalue(ast.name) + ast.type + self.stringify_lvalue(ast.field)
        if type(ast) is c_ast.ID:
            return ast.name
        if type(ast) is str:
            return ast
        if type(ast) is c_ast.ArrayRef:
            return self.stringify_lvalue(ast.name)

    def handle_decl(self, ast: c_ast.Node, context: str, decl_history: Set[str]) -> None:
        """Handle a declaration of a variable, mark all variables that appreas in line.

        Args:
            ast (c_ast.Node): the abstract syntax tree of the input
            context (str): the current context (scopes) of the parsing 
            decl_history (Set[str]): a set that contains all declarations of variables (so we could know what variable to mark)
        """

        if hasattr(ast, "name"):
            decl_history.add(PiniParser.get_contexted_name(
                self.stringify_lvalue(ast.name), context))

        if self.is_pini_var_exists(ast,  context, decl_history):
            if hasattr(ast, "name"):
                context_name = PiniParser.get_contexted_name(
                    self.stringify_lvalue(ast.name), context)
                if not self.is_variable_marked(context_name):
                    self.marked.add(self.find_definition_scope(
                        context_name, decl_history))
            elif hasattr(ast, "lvalue"):
                context_name = PiniParser.get_contexted_name(
                    self.stringify_lvalue(ast.lvalue), context)
                if not self.is_variable_marked(context_name):
                    self.marked.add(self.find_definition_scope(
                        context_name, decl_history))

            self.mark_subtree(ast, context, decl_history)

    def handle_if(self, ast: c_ast.Node, context: str, scopes: ScopesList, decl_history: Set[str]) -> None:
        """Parse an if statement and mark all variables.

        Args:
            ast (c_ast.Node): ast of the if statement
            context (str): the current context (scopes) of the parsing 
            scopes (ScopesList): a list of counter for [if/for/while/else] so we could know which scope are we in.
            decl_history (Set[str]): a set that contains all declarations of variables (so we could know what variable to mark)
        """

        self.parse(ast, context, copy.deepcopy(scopes), decl_history)

    def handle_binary_op(self, ast: c_ast.Node, context: str, decl_history) -> None:
        """Handle a binary op and mark all variables that should be marked.

        Args:
            ast (c_ast.Node): syntax tree of the binary op
            scopes (ScopesList): a list of counter for [if/for/while/else] so we could know which scope are we in.
            decl_history (Set[str]): a set that contains all declarations of variables (so we could know what variable to mark)
        """

        if type(ast) is not c_ast.BinaryOp:
            return

        if self.is_pini_var_exists(ast, context, decl_history):
            self.mark_subtree(ast, context, decl_history)

    def handle_loop(self, ast: c_ast.Node, context: str, scopes: ScopesList, loop_name: str, decl_history: Set[str]) -> None:
        """Handle any loop (while/for) and mark all variables inside

        Args:
            ast (c_ast.Node): syntax tree of the loop
            context (str): the current context (scopes) of the parsing 
            scopes (ScopesList): a list of counter for [if/for/while/else] so we could know which scope are we in.
            loop_name (str): this is a generic function that can parse either for or while, so we need to specify which one for context purposes.
            decl_history (Set[str]): a set that contains all declarations of variables (so we could know what variable to mark)
        """

        self.loop_parse_wrapper(
            ast, context + f"{loop_name}[{str(scopes[f'{loop_name}'])}]@", copy.deepcopy(scopes), loop_name, decl_history)

    def loop_parse_wrapper(self, ast: c_ast.Node, context: str, scopes: ScopesList, loop_name: str, decl_history: Set[str]) -> List[str]:
        """A wrapper function for parsing loops, this function increases the loop scopes cell (we have a new loop and hence need to increase this loop counter by 1).

        Args:
            ast (c_ast.Node): syntax tree of the loop
            context (str): the current context (scopes) of the parsing 
            scopes (ScopesList): a list of counter for [if/for/while/else] so we could know which scope are we in.
            loop_name (str): this is a generic function that can parse either for or while, so we need to specify which one for context purposes.
            decl_history (Set[str]): a set that contains all declarations of variables (so we could know what variable to mark)
        """

        scopes[f"{loop_name}"].append(1)
        self.parse(ast, context, scopes, decl_history)

    def is_pini_var_exists(self, ast: c_ast.Node, context: str, decl_history: Set[str]) -> bool:
        """Check wheter some pini var exists in the given syntax tree.

        Args:
            ast (c_ast.Node): input syntax tree
            context (str): the current context (scopes) of the parsing 
            decl_history (Set[str]): a set that contains all declarations of variables (so we could know what variable to mark)

        Returns:
            bool: True if pini var exists and False otherwise
        """

        children = ast.children()

        if len(children) == 0:
            if type(ast) is c_ast.ID:
                if self.is_variable_marked(context + ast.name):
                    return True
                return False

        if type(ast) is c_ast.FuncCall:
            if hasattr(ast.name, "name"):
                func_name = ast.name.name
                if func_name == "va_arg":
                    return True

            if not self.parse_called_function(ast, context, decl_history):
                return False

            if ast.name.name in self.linked_functions:
                return self.linked_functions[ast.name.name].is_there_pini_return(self.functions[ast.name.name], PiniParser.contextify(ast.name.name, self.linked_functions[ast.name.name].filename + DELIMITER), decl_history)
            else:
                return self.is_there_pini_return(self.functions[ast.name.name], PiniParser.contextify(self.filename, ast.name.name), decl_history)

        if type(ast) is c_ast.StructRef:
            if self.is_variable_marked(context + self.stringify_lvalue(ast)):
                return True
            return False

        for _, child in children:
            if self.is_pini_var_exists(child, context, decl_history):
                return True

        return False

    def mark_subtree(self, ast: c_ast.Node, context: str, decl_history: Set[str]):
        """Mark all variables in a syntex tree. variables in function calls will not be marked.

        Args:
            ast (c_ast.Node): input syntax tree
            context (str): the current context (scopes) of the parsing 
            decl_history (Set[str]): a set that contains all declarations of variables (so we could know what variable to mark)
        """
        children = ast.children()

        if len(children) == 0:
            if type(ast) is c_ast.ID:
                context_name = PiniParser.get_contexted_name(ast.name, context)
                if not self.is_variable_marked(context_name):
                    self.marked.add(self.find_definition_scope(
                        context_name, decl_history))

        if type(ast) is c_ast.FuncCall:
            return

        if type(ast) is c_ast.StructRef:
            return

        if type(ast) is c_ast.ArrayRef:
            return

        for _, child in children:
            self.mark_subtree(child, context, decl_history)

    def link_non_local_function(self,  ast: c_ast.Node) -> Tuple[str, str, c_ast.Node]:
        """If a function was called, and can't be found locally, we would like to link it from the project.
        In order to do that, we build an include graph for the project and try to find a path from the current file to the called function.

        Args:
            ast (c_ast.Node): input syntax tree

        Returns:
            in case of success:
                Tuple[str, PiniParser, c_ast.Node]: [the name of the file declaring the function found, the parser for the function, the ast of the function]
            in case of failure:
                Tuple[str, PiniParser, c_ast.Node]: "", None, None
        """
        if ast.name.name not in self.graph_manager.function_counter:
            # function was not found in graph and hence can't be linked
            self.logger.log(f"{ast.name.name} || Function can't be found")
            return "", None, None

        is_path_exist, found_index = self.graph_manager.is_path_exists_to_function(self.filename, ast.name.name)

        if not is_path_exist:
            # function exists in graph, but there is no legal include path from current file to function.
            self.logger.log(
                f"{ast.name.name} || Function exists, but was not linked")
            return "", None, None

        # get the name of the file in which the function is declared
        file_declaring_function_name = self.graph_manager.get_function_declaring_parent(
            self.graph_manager.gca, ast.name.name, found_index)
        file_found_ast = parse_file(
            file_declaring_function_name, use_cpp=False)

        # get the funciton definition syntex tree
        definition = self.find_function_def_in_tree(
            file_found_ast, ast.name.name)
        if definition is None:
            self.logger.log(
                f"{ast.name.name} || Function is declared, but definition not found")
            return "", None, None

        # save the definition into a dictionary for future use
        self.functions[ast.name.name] = definition

        linked_function_parser = PiniParser(
            self.marked, ast.name.name, file_declaring_function_name, self.graph_manager)

        self.linked_functions[ast.name.name] = linked_function_parser
        return file_declaring_function_name, linked_function_parser, file_found_ast

    def parse_called_function(self, ast: c_ast.Node, call_context: str, decl_history: Set[str], scopes: ScopesList = ScopesList()) -> bool:
        """Parse and mark a call to function. This requires to identify all pini variables from call so we could parse the function.

        Args:
            ast (c_ast.Node): input syntax tree of called function
            context (str): the current context (scopes) of the parsing 
            decl_history (Set[str]): a set that contains all declarations of variables (so we could know what variable to mark)
            scopes (ScopesList): a list of counter for [if/for/while/else] so we could know which scope are we in.

        Returns:
            bool: True if success, False if failure
        """
        file_context = self.filename
        if ast.name.name not in self.functions:
            name, linked_function_parser, file_found_ast = self.link_non_local_function(ast)
            if not name:
                return False

            file_context = name

        # get the context of the definition
        def_context = PiniParser.contextify(
            ast.name.name, file_context + DELIMITER)

        # find the params that needs to be marked in the called function (derived from call and pre-marked params)
        def_params = [PiniParser.get_contexted_name(param_name, def_context)
                      for param_name in PiniParser.get_func_def_params(self.functions[ast.name.name])]
        boolean_pini_call_params = self.get_pini_param_map(
            ast, call_context, def_params, decl_history)

        params_marked = [param_name for param_name, is_pini in zip(
            def_params, boolean_pini_call_params) if is_pini]
        self.marked.update(params_marked)

        if not ast.name.name in self.linked_functions:
            self.parse(self.functions[ast.name.name].body, def_context, scopes)
        else:
            linked_function_parser.parse(file_found_ast, "")

        return True

    def find_function_def_in_tree(self, ast: c_ast.Node, function_name: str) -> c_ast.Node:
        """Find a function definition in a file.
        Ths is mainly used for finding where a function is defined in order to parse it.

        Args:
            ast (c_ast.Node): input syntax tree
            function_name (str): the name of the function we are trying to find.

        Returns:
            c_ast.Node: the function definition found if found otherwise None
        """

        if type(ast) is c_ast.FuncDef and ast.decl.name == function_name:
            return ast

        for _, child in ast.children():
            found = self.find_function_def_in_tree(child, function_name)
            if found:
                return found

        return None

    def get_pini_param_map(self, ast: c_ast.Node, context: str, def_params: List[str], decl_history: Set[str]) -> List[bool]:
        """This function returns which of the variables used in the function call are pini.

        Args:
            ast (c_ast.Node): input syntax tree
            context (str): the current context (scopes) of the parsing 
            decl_history (Set[str]): a set that contains all declarations of variables (so we could know what variable to mark)
            scopes (ScopesList): a list of counter for [if/for/while/else] so we could know which scope are we in.

        Returns:
            List[bool]: a list of booleans such that cell i is true if argument i is pini.
        """

        params_asts = PiniParser.get_func_call_params(ast)
        result = [False] * len(params_asts)
        trues_count = -1

        while trues_count != sum(result):
            trues_count = sum(result)
            for param_index, param_ast in enumerate(params_asts):
                is_pini_exists = self.is_pini_var_exists(
                    param_ast, context, decl_history) or def_params[param_index] in self.marked
                if is_pini_exists:
                    self.mark_subtree(param_ast, context, decl_history)
                result[param_index] = is_pini_exists

        return result

    def is_there_pini_return(self, ast: c_ast.Node, context: str, decl_history: Set[str]) -> bool:
        """Checks whether there is a return in the function that returns a marked variable (pini-var).

        Args:
            ast (c_ast.Node): input syntax tree
            context (str): the current context (scopes) of the parsing 
            decl_history (Set[str]): a set that contains all declarations of variables (so we could know what variable to mark)

        Returns:
            bool: [description]
        """
        children = ast.children()

        if type(ast) is c_ast.Return:
            if self.is_pini_var_exists(ast, context, decl_history):
                return True

        if len(children) == 0:
            return False

        for _, child in children:
            if self.is_there_pini_return(child, context, decl_history):
                return True

        return False

    def is_variable_marked(self, var_name: str) -> bool:
        """Check if a variable is marked.
        This is not a trivial task since we only know the current context, but it might have been defined in an upper scope.

        Args:
            var_name (str): The name of the variable to check

        Returns:
            bool: True if marked, false otherwise
        """

        return self.is_defined_in_upper_scope(var_name, self.marked)[0]

    def find_definition_scope(self, var_name: str, decl_history: Set[str]) -> str:
        """find the definition scope of a variable, this is used in order to check whether a variable is marked.

        Args:
            var_name (str): the name of the variable to find
            decl_history (Set[str]): a set that contains all declarations of variables (so we could know what variable to mark)

        Returns:
            str: the name of the variable definition
        """
        _, var_names = self.is_defined_in_upper_scope(var_name, decl_history)

        for name in var_names:
            for defined_var in decl_history:
                if name == defined_var:
                    return defined_var

        return var_name

    def is_defined_in_upper_scope(self, var_name: str, set_to_check: Set[str]) -> bool:
        """Check if a variable is declared in an upper scope. 

        Args:
            var_name (str): the name of the variable to find
            set_to_check (Set[str]): a set that contains all declarations of variables (so we could know what variable to mark)

        Returns:
            bool: True if defined, False otherwise.
        """
        scopes = var_name.split(DELIMITER)
        var_name = scopes[-1]
        scopes = scopes[:-1]

        preficies = [DELIMITER.join(scope) for scope in [scopes[:i+1]
                                                         for i, _ in enumerate(scopes)]]
        var_names = [prefix + DELIMITER +
                     var_name for prefix in preficies] + [var_name]

        return any([var_name in self.marked for var_name in var_names]), var_names

    @staticmethod
    def get_func_def_params(ast: c_ast.Node) -> List[str]:
        """Get a list of the parameters specified in the function declaration.

        Args:
            ast (c_ast.Node): input syntax tree

        Returns:
            List[str]: the list of parameters.
        """
        if type(ast) is not c_ast.FuncDef:
            return []

        if ast.decl.type.args is None:
            return []

        return [param.name for param in ast.decl.type.args.params]

    @staticmethod
    def get_func_call_params(ast: c_ast.Node) -> List[str]:
        """Get a list of params of the function call

        Args:
            ast (c_ast.Node): input syntax tree

        Returns:
            List[str]: the list of parameters.
        """
        if type(ast) is not c_ast.FuncCall:
            return []

        if ast.args is None:
            return []

        return [param for param in ast.args.exprs]

    @staticmethod
    def contextify(name: str, context: str, delimiter: str = DELIMITER) -> str:
        """Get a current context and a name found and return the contexted name.

        Args:
            name (str): the name of the variable to contextify
            context (str): current context
            delimiter (str, optional): which delimiter should be used, you should not change this. Defaults to DELIMITER.

        Returns:
            str: The contexted name
        """
        return context + name + delimiter

    @staticmethod
    def contextify_list(str_list_to_contextify: List[str], delimiter: str = DELIMITER) -> str:
        """contexify a list of paramters (join them with delimiter).

        Args:
            str_to_contextify (List[str]): List to join with the delimiter
            delimiter (str, optional): which delimiter should be used, you should not change this. Defaults to DELIMITER.

        Returns:
            str: The contexted name
        """
        return DELIMITER.join(str_list_to_contextify)

    @staticmethod
    def get_contexted_name(name: str, context: str) -> str:
        """a context always contains DELIMITER at the end. so get the contexted name using the context and the name only.
        This deffers from contextify method because contextify returns a new context (add @ at the end) and this function return the contexified name.

        Args:
            name (str): the name to return the contexted name
            context (str): the current context

        Returns:
            str: The contexted name
        """

        return context + name


def remove_project_static_includes(root: str):
    """Remove all static include from all files in a dir.
    The pycparser can't parse any preprocess syntax and therefore after we build the include graph we need to remove it.

    Args:
        root (str): the root directory to start from.
    """

    for path, _, files in os.walk(root):
        for file in files:
            full_path = os.path.join(path, file)
            with open(full_path, "r") as fd:
                data = fd.read()
                static_removed = mai.ProjectGraph.remove_static_includes(data)

            with open(full_path, "w") as fd:
                fd.write(static_removed)


def mark_project(start_file_name: str, marked: List[str]) -> Set[str]:
    """Mark all variables in a project.

    Args:
        file_name (str): The name of the file to mark
        marked (List[str]): A list of already marked variables.

    Returns:
        Set[str]: The marked variables found in the project
    """

    project_root = "/".join(start_file_name.split("/")[:-1])
    project_graph_manager = mai.ProjectGraph(start_file_name, project_root)

    remove_project_static_includes(project_root)

    ast = parse_file(start_file_name, use_cpp=False)

    pp = PiniParser(set(marked), filename=start_file_name,
                    graph_manager=project_graph_manager)
    pp.parse(ast, "")
    return sorted(list(pp.get_marked()))


if __name__ == "__main__":
    argparser = argparse.ArgumentParser('pini parser')
    argparser.add_argument('filename', help='name of file to parse')
    args = argparser.parse_args()

    print("@=======================@")
    print("| Marked variables are: |")
    print("@=======================@")

    for marked_var in mark_project(args.filename, [str(args.filename) + "@main@x"]):
        print(marked_var)
