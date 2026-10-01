"""Statically bound template dependencies without rendering or executing code."""

import ast
from dataclasses import dataclass
import re
from typing import Any

from jinja2 import Environment, TemplateSyntaxError, nodes

from homeassistant.core import valid_entity_id

from .const import (
    JINJA_FILTERS,
    JINJA_STATE_FUNCTIONS,
    JINJA_TESTS,
    JS_FUNCTIONS,
    JS_MATH_METHODS,
    JS_RESERVED_NAMES,
    JS_VALUE_METHODS,
    MAX_TEMPLATE_LENGTH,
    MAX_TEMPLATE_NODES,
)

_LITERAL = re.compile(
    r"(?:states|is_state|is_state_attr|state_attr|has_value)\s*\(\s*['\"]([a-z0-9_]+\.[a-z0-9_]+)['\"]"
    r"|(?:hass\.)?states\s*\[\s*['\"]([a-z0-9_]+\.[a-z0-9_]+)['\"]\s*\]"
    r"|states\.([a-z0-9_]+\.[a-z0-9_]+)"
)
_JINJA = Environment()
_JS_TOKEN = re.compile(
    r"\s+|//[^\n]*|/\*[\s\S]*?\*/"
    r"|'(?:\\[^\r\n]|[^'\\\r\n])*'|\"(?:\\[^\r\n]|[^\"\\\r\n])*\""
    r"|(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
    r"|[A-Za-z_$][A-Za-z0-9_$]*"
    r"|===|!==|==|!=|<=|>=|&&|\|\||\+\+|--|[+*/%!?<>=:.,;(){}\[\]-]"
)
_PRECEDENCE = {
    "||": 1,
    "&&": 2,
    "==": 3,
    "!=": 3,
    "===": 3,
    "!==": 3,
    "<": 4,
    ">": 4,
    "<=": 4,
    ">=": 4,
    "+": 5,
    "-": 5,
    "*": 6,
    "/": 6,
    "%": 6,
}


@dataclass(frozen=True)
class TemplateDependencies:
    """A conservative entity set and whether every dependency was bounded."""

    entity_ids: frozenset[str]
    complete: bool


@dataclass(frozen=True)
class _Value:
    kind: str = "data"
    value: Any = None


def _data(value: _Value) -> _Value:
    if value.kind not in {"data", "literal", "record", "date"}:
        raise ValueError("Unbounded template object")
    return value


def _variable(value: _Value) -> _Value:
    """Do not infer a constant lookup key from mutable, branch-local bindings."""
    _data(value)
    return _Value() if value.kind == "literal" else value


def _attribute(name: str) -> None:
    if name.startswith("_") or name in {"constructor", "prototype", "caller", "callee"}:
        raise ValueError("Unsupported template attribute")


def _entity(identifier: Any, found: set[str]) -> _Value:
    if not isinstance(identifier, str) or not valid_entity_id(identifier):
        raise ValueError("Entity reference is not a literal identifier")
    found.add(identifier)
    return _Value("record")


class _Jinja:
    """Visit all branches of a small, read-only Jinja AST subset."""

    def __init__(self, found: set[str]) -> None:
        self.found = found
        self.variables: dict[str, _Value] = {}

    def visit(self, node: nodes.Node) -> _Value:
        if isinstance(node, nodes.Const):
            return _Value("literal", node.value)
        if isinstance(node, nodes.Name):
            if node.name in self.variables:
                return self.variables[node.name]
            if node.name == "states":
                return _Value("states")
            if node.name in JINJA_STATE_FUNCTIONS | {"now", "utcnow"}:
                return _Value("function", node.name)
            raise ValueError("Unknown Jinja variable")
        if isinstance(node, (nodes.Getattr, nodes.Getitem)):
            parent = self.visit(node.node)
            if isinstance(node, nodes.Getattr):
                key = _Value("literal", node.attr)
            else:
                key = _data(self.visit(node.arg))
            if parent.kind in {"states", "domain"}:
                if key.kind != "literal" or not isinstance(key.value, str):
                    raise ValueError("Dynamic state lookup")
                _attribute(key.value)
                if parent.kind == "domain":
                    return _entity(f"{parent.value}.{key.value}", self.found)
                if "." in key.value:
                    return _entity(key.value, self.found)
                return _Value("domain", key.value)
            _data(parent)
            if isinstance(key.value, str):
                _attribute(key.value)
            if parent.kind == "date" and key.value == "strftime":
                return _Value("function", "strftime")
            return _Value()
        if isinstance(node, nodes.Call):
            function = self.visit(node.node)
            if node.dyn_args is not None or node.dyn_kwargs is not None:
                raise ValueError("Dynamic call arguments")
            arguments = [_data(self.visit(arg)) for arg in node.args]
            for keyword in node.kwargs:
                _data(self.visit(keyword.value))
            name = "states" if function.kind == "states" else function.value
            if function.kind not in {"function", "states"}:
                raise ValueError("Unknown Jinja call")
            if name in JINJA_STATE_FUNCTIONS:
                if not arguments or arguments[0].kind != "literal":
                    raise ValueError("Dynamic entity argument")
                _entity(arguments[0].value, self.found)
                return _Value()
            if name in {"now", "utcnow"}:
                return _Value("date")
            if name == "strftime":
                return _Value()
            raise ValueError("Unknown Jinja function")
        if isinstance(node, (nodes.Filter, nodes.Test)):
            allowed = JINJA_FILTERS if isinstance(node, nodes.Filter) else JINJA_TESTS
            if node.name not in allowed:
                raise ValueError("Unknown Jinja filter or test")
            if node.dyn_args is not None or node.dyn_kwargs is not None:
                raise ValueError("Dynamic filter arguments")
            for child in node.iter_child_nodes():
                _data(self.visit(child))
            return _Value()
        if isinstance(node, nodes.Assign):
            if not isinstance(node.target, nodes.Name):
                raise ValueError("Unsupported Jinja assignment")
            name = node.target.name
            if name in JINJA_STATE_FUNCTIONS | {"now", "utcnow"}:
                raise ValueError("Shadowed Jinja global")
            self.variables[name] = _variable(self.visit(node.node))
            return _Value()
        if type(node) in {
            nodes.Template,
            nodes.Output,
            nodes.TemplateData,
            nodes.If,
            nodes.CondExpr,
            nodes.Compare,
            nodes.Operand,
            nodes.Keyword,
            nodes.Add,
            nodes.Sub,
            nodes.Mul,
            nodes.Div,
            nodes.FloorDiv,
            nodes.Mod,
            nodes.Pow,
            nodes.Neg,
            nodes.Pos,
            nodes.And,
            nodes.Or,
            nodes.Not,
            nodes.Concat,
        }:
            for child in node.iter_child_nodes():
                _data(self.visit(child))
            return _Value()
        raise ValueError("Unsupported Jinja construct")


class _JavaScript:
    """Parse scalar expressions, declarations, returns, and conditional branches."""

    def __init__(self, source: str, entity_id: str | None, found: set[str]) -> None:
        self.tokens: list[str] = []
        position = 0
        while position < len(source):
            match = _JS_TOKEN.match(source, position)
            if match is None:
                raise ValueError("Unsupported JavaScript token")
            position = match.end()
            token = match.group()
            if not token.isspace() and not token.startswith(("//", "/*")):
                self.tokens.append(token)
        if len(self.tokens) > MAX_TEMPLATE_NODES:
            raise ValueError("Template is too complex")
        self.position = 0
        self.entity_id, self.found = entity_id, found
        self.variables: dict[str, _Value] = {}

    def peek(self) -> str:
        return self.tokens[self.position] if self.position < len(self.tokens) else ""

    def take(self, expected: str | None = None) -> str:
        token = self.peek()
        if not token or expected is not None and token != expected:
            raise ValueError("Unsupported JavaScript syntax")
        self.position += 1
        return token

    def parse(self) -> None:
        while self.peek():
            self.statement()

    def statement(self) -> None:
        token = self.take()
        if token == ";":
            return
        if token == "{":
            while self.peek() != "}":
                self.statement()
            self.take("}")
            return
        if token == "if":
            self.take("(")
            _data(self.expression())
            self.take(")")
            self.statement()
            if self.peek() == "else":
                self.take()
                self.statement()
            return
        if token in {"let", "const", "var"}:
            name = self.take()
            if (
                not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", name)
                or name in JS_RESERVED_NAMES
            ):
                raise ValueError("Unsupported JavaScript variable")
            self.take("=")
            self.variables[name] = _variable(self.expression())
        elif token == "return":
            _data(self.expression())
        else:
            raise ValueError("Unsupported JavaScript statement")
        if self.peek() == ";":
            self.take()
        elif self.peek() not in {"", "}", "else"}:
            raise ValueError("Missing JavaScript statement boundary")

    def expression(self, minimum: int = 0) -> _Value:
        token = self.take()
        if token in {"!", "+", "-"}:
            _data(self.expression(7))
            value = _Value()
        elif token == "(":
            value = self.expression()
            self.take(")")
        elif token.startswith(("'", '"')):
            value = _Value("literal", ast.literal_eval(token))
        elif token[0].isdigit() or token.startswith(".") and len(token) > 1:
            value = _Value("literal")
        elif token in {"true", "false", "null", "undefined"}:
            value = _Value("literal")
        elif token in self.variables:
            value = self.variables[token]
        elif token == "entity":
            value = _entity(self.entity_id, self.found)
        elif token in {"states", "hass", "Math"}:
            value = _Value(token)
        elif token in JS_FUNCTIONS:
            value = _Value("function")
        else:
            raise ValueError("Unknown JavaScript variable")
        while self.peek() in {".", "[", "("}:
            operation = self.take()
            if operation == "(":
                if value.kind != "function":
                    raise ValueError("Unknown JavaScript call")
                if self.peek() != ")":
                    while True:
                        _data(self.expression())
                        if self.peek() != ",":
                            break
                        self.take()
                self.take(")")
                value = _Value()
                continue
            if operation == ".":
                key = _Value("literal", self.take())
                if not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", key.value):
                    raise ValueError("Invalid JavaScript property")
            else:
                key = _data(self.expression())
                self.take("]")
            if isinstance(key.value, str):
                _attribute(key.value)
            if value.kind in {"hass", "states", "Math"}:
                if key.kind != "literal":
                    raise ValueError("Dynamic JavaScript state lookup")
                if value.kind == "states":
                    value = _entity(key.value, self.found)
                elif value.kind == "hass" and key.value == "states":
                    value = _Value("states")
                elif value.kind == "Math" and key.value in JS_MATH_METHODS:
                    value = _Value("function")
                else:
                    raise ValueError("Unsupported JavaScript namespace")
            else:
                _data(value)
                value = (
                    _Value("function") if key.value in JS_VALUE_METHODS else _Value()
                )
        while self.peek() in _PRECEDENCE and _PRECEDENCE[self.peek()] >= minimum:
            precedence = _PRECEDENCE[self.take()]
            _data(value)
            _data(self.expression(precedence + 1))
            value = _Value()
        if minimum == 0 and self.peek() == "?":
            _data(value)
            self.take()
            _data(self.expression())
            self.take(":")
            _data(self.expression())
            value = _Value()
        return value


def template_dependencies(
    source: str, *, card_type: str = "", entity_id: str | None = None
) -> TemplateDependencies:
    """Reject unsupported operations while retaining recognizable literal IDs."""
    if len(source) > MAX_TEMPLATE_LENGTH:
        return TemplateDependencies(frozenset(), False)
    found = {
        next(group for group in match.groups() if group)
        for match in _LITERAL.finditer(source)
    }
    try:
        if "[[[" in source:
            code = source.strip()
            if (
                card_type != "custom:button-card"
                or not code.startswith("[[[")
                or not code.endswith("]]]")
            ):
                raise ValueError("Unsupported JavaScript template context")
            _JavaScript(code[3:-3], entity_id, found).parse()
        else:
            tree = _JINJA.parse(source)
            if sum(1 for _ in tree.find_all(nodes.Node)) > MAX_TEMPLATE_NODES:
                raise ValueError("Template is too complex")
            _Jinja(found).visit(tree)
    except (ValueError, SyntaxError, TemplateSyntaxError, RecursionError):
        return TemplateDependencies(frozenset(found), False)
    return TemplateDependencies(frozenset(found), True)
