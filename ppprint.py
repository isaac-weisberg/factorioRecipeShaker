import ast
import inspect
from pprint import pformat
from typing import Any


def ppprint(value: Any) -> None:
    frame = inspect.currentframe()
    if frame is None or frame.f_back is None:
        print(pformat(value))
        return

    caller = frame.f_back

    try:
        info = inspect.getframeinfo(caller, context=1)
        if not info.code_context:
            print(pformat(value))
            return

        tree = ast.parse(info.code_context[0].strip())
        if not tree.body or not isinstance(tree.body[0], ast.Expr):
            print(pformat(value))
            return

        expr = tree.body[0].value
        if not isinstance(expr, ast.Call) or not expr.args:
            print(pformat(value))
            return

        name = ast.unparse(expr.args[0])
        print(f"{name} = {pformat(value)}")

    except (SyntaxError, ValueError, OSError):
        print(pformat(value))
    finally:
        del caller
        del frame