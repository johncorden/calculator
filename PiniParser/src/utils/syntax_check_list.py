import argparse
from pycparser import c_parser, c_ast, parse_file
from typing import List

class PiniParser():
    def __init__(self, filename: str, marked: List[str]):
        self.marked = marked
        self.filename = filename

    def parse(self) -> List[str]:
        pass

class Node(object):    
    pass

class NodeVisitor(object):
    pass

class ArrayDecl(Node):
    continue

class ArrayRef(Node):
    continue

class Assignment(Node):
    continue

class BinaryOp(Node):
    continue

class Break(Node):
    continue

class Case(Node):
    continue

class Cast(Node):
    continue

class Compound(Node):
    continue

class CompoundLiteral(Node):
    pass

class Constant(Node):
    continue

class Continue(Node):
    continue

class Decl(Node):
    continue

class DeclList(Node):
    continue

class Default(Node):
    continue

class DoWhile(Node):
    continue

class EllipsisParam(Node):
    continue

class EmptyStatement(Node):
    continue

class Enum(Node):
    continue

class Enumerator(Node):
    continue

class EnumeratorList(Node):
    continue

class ExprList(Node):
    continue

class FileAST(Node):
    continue

class For(Node):
    continue

class FuncCall(Node):
    continue

class FuncDecl(Node):
    continue

class FuncDef(Node):
    continue

class Goto(Node):
    continue

class ID(Node):
    continue

class IdentifierType(Node):
    pass

class If(Node):
    continue

class InitList(Node):
    pass

class Label(Node):
    continue

class NamedInitializer(Node):
    pass

class ParamList(Node):
    continue

class PtrDecl(Node):
    continue

class Return(Node):
    continue

class Struct(Node):
    continue

class StructRef(Node):
    continue

class Switch(Node):
    continue

class TernaryOp(Node):
    continue

class TypeDecl(Node):
    continue

class Typedef(Node):
    continue

class Typename(Node):
    pass

class UnaryOp(Node):
    continue

class Union(Node):
    continue

class While(Node):
    continue

class Pragma(Node):
    pass

def find_dependencies(ast):
    children = ast.children()

    if len(children) == 0:
        return True
    
    for _,child in children:
        if type(child) is c_ast.Compound:
            print("CompoundLiteral")
        find_dependencies(child)
    
    return False


if __name__ == "__main__":
    argparser = argparse.ArgumentParser('Dump AST')
    argparser.add_argument('filename', help='name of file to parse')
    argparser.add_argument('--coord', help='show coordinates in the dump',
                           action='store_true')
    args = argparser.parse_args()

    ast = parse_file(args.filename, use_cpp=False)

    find_dependencies(ast)
    # print("found", sorted(list(marked)))
