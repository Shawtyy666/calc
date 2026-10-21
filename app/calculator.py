"""Restricted arithmetic interpreter; never executes Python code."""

import ast
import math
import operator


class CalculationError(ValueError):
    pass


OPERATIONS = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv}
AST_OPERATIONS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}


def finite(value: float) -> float:
    try:
        value = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise CalculationError("Число вне допустимого диапазона") from exc
    if not math.isfinite(value):
        raise CalculationError("Результат должен быть конечным числом")
    return value


def calculate(a: float, op: str, b: float) -> float:
    if op not in OPERATIONS:
        raise CalculationError("Допустимые операции: +, -, *, /")
    a, b = finite(a), finite(b)
    if op == "/" and b == 0:
        raise CalculationError("Деление на ноль запрещено")
    return finite(OPERATIONS[op](a, b))


def evaluate(expression: str, variables: dict[str, float] | None = None) -> float:
    expression = expression.strip()
    if not expression or len(expression) > 1000:
        raise CalculationError("Выражение должно содержать от 1 до 1000 символов")
    variables = variables or {}
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise CalculationError("Некорректный синтаксис выражения") from exc
    if sum(1 for _ in ast.walk(tree)) > 256:
        raise CalculationError("Выражение слишком сложное")

    def visit(node: ast.AST, depth: int = 0) -> float:
        if depth > 32:
            raise CalculationError("Превышена глубина выражения (32)")
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return finite(node.value)
        if isinstance(node, ast.Name):
            if node.id not in variables:
                raise CalculationError(f"Не задана переменная: {node.id}")
            return finite(variables[node.id])
        if isinstance(node, ast.BinOp) and type(node.op) in AST_OPERATIONS:
            return calculate(visit(node.left, depth + 1), AST_OPERATIONS[type(node.op)], visit(node.right, depth + 1))
        if isinstance(node, ast.UnaryOp) and type(node.op) in (ast.UAdd, ast.USub):
            value = visit(node.operand, depth + 1)
            return value if isinstance(node.op, ast.UAdd) else -value
        raise CalculationError("Разрешены только числа, переменные, +, -, *, / и скобки")

    return visit(tree.body)
