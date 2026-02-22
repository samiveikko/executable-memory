"""Safe expression evaluator for `when` conditions and `assert check`."""

from __future__ import annotations

import ast
import operator
from types import ModuleType
from typing import Any

# Allowed binary operators
_BINOPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
}

_UNARY_OPS = {
    ast.Not: operator.not_,
    ast.USub: operator.neg,
}


def safe_eval(expr: str, context: dict[str, Any], udf_module: ModuleType | None = None) -> Any:
    """Evaluate a restricted expression.

    Supported: bool, number, string literals, comparisons, bool ops,
    arithmetic, variable access, attribute access, udf.* calls,
    dict/list indexing.
    """
    tree = ast.parse(expr, mode="eval")
    return _eval_node(tree.body, context, udf_module)


def _eval_node(node: ast.AST, ctx: dict[str, Any], udf: ModuleType | None) -> Any:
    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        if node.id == "True":
            return True
        if node.id == "False":
            return False
        if node.id == "None":
            return None
        if node.id not in ctx:
            raise NameError(f"Undefined variable: {node.id}")
        return ctx[node.id]

    if isinstance(node, ast.Attribute):
        obj = _eval_node(node.value, ctx, udf)
        return getattr(obj, node.attr)

    if isinstance(node, ast.Subscript):
        obj = _eval_node(node.value, ctx, udf)
        key = _eval_node(node.slice, ctx, udf)
        return obj[key]

    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, ctx, udf)
        for op_node, comparator in zip(node.ops, node.comparators):
            right = _eval_node(comparator, ctx, udf)
            op_fn = _BINOPS.get(type(op_node))
            if op_fn is None:
                raise ValueError(f"Unsupported comparison: {type(op_node).__name__}")
            if not op_fn(left, right):
                return False
            left = right
        return True

    if isinstance(node, ast.BoolOp):
        op_fn = _BINOPS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported bool op: {type(node.op).__name__}")
        result = _eval_node(node.values[0], ctx, udf)
        for val in node.values[1:]:
            result = op_fn(result, _eval_node(val, ctx, udf))
        return result

    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, ctx, udf)
        right = _eval_node(node.right, ctx, udf)
        op_fn = _BINOPS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported binary op: {type(node.op).__name__}")
        return op_fn(left, right)

    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, ctx, udf)
        op_fn = _UNARY_OPS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported unary op: {type(node.op).__name__}")
        return op_fn(operand)

    if isinstance(node, ast.Call):
        func = _eval_node(node.func, ctx, udf)
        args = [_eval_node(a, ctx, udf) for a in node.args]
        kwargs = {kw.arg: _eval_node(kw.value, ctx, udf) for kw in node.keywords}
        return func(*args, **kwargs)

    if isinstance(node, ast.IfExp):
        test = _eval_node(node.test, ctx, udf)
        return _eval_node(node.body, ctx, udf) if test else _eval_node(node.orelse, ctx, udf)

    raise ValueError(f"Unsupported expression node: {type(node).__name__}")
