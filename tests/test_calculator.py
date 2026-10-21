import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.calculator import CalculationError, evaluate

client = TestClient(app)


@pytest.mark.parametrize("path,a,b,expected", [("add", 2, 3, 5), ("subtract", 2, 3, -1), ("multiply", -2, 3, -6), ("divide", 7, 2, 3.5)])
def test_arithmetic(path, a, b, expected):
    response = client.post(f"/{path}", json={"a": a, "b": b})
    assert response.status_code == 200
    assert response.json() == {"result": expected}


@pytest.mark.parametrize("op,expected", [("+", 8), ("-", 4), ("*", 12), ("/", 3)])
def test_operation(op, expected):
    assert client.post("/calculate", json={"a": 6, "op": op, "b": 2}).json() == {"result": expected}


@pytest.mark.parametrize("expression,expected", [("2+3*4", 14), ("(2+3)*4", 20), ("8/4/2", 1), ("10-3-2", 5), ("-2 * +3", -6), (" 1.5 + 2e1 ", 21.5), ("0", 0)])
def test_expressions(expression, expected):
    response = client.post("/evaluate", json={"expression": expression})
    assert response.status_code == 200
    assert response.json()["result"] == pytest.approx(expected)


def test_variables():
    response = client.post("/evaluate", json={"expression": "(a+b)*c + (d-e)/(f-g)", "variables": dict(a=2, b=3, c=4, d=10, e=4, f=5, g=2)})
    assert response.status_code == 200
    assert response.json() == {"result": 22.0}


@pytest.mark.parametrize("expression", ["1/0", "x+1", "1+", " ", "True", "'text'", "2**10", "7//2", "7%2", "abs(-1)", "__import__('os').getcwd()", "a.real", "[1][0]", "[x for x in []]", "lambda: 1", "1e309", "1e308*10", "1+"*140+"1", "-"*40+"1", "("*300+"1"+")"*300])
def test_invalid_expression(expression):
    response = client.post("/evaluate", json={"expression": expression})
    assert response.status_code == 400
    assert isinstance(response.json()["detail"], str)


@pytest.mark.parametrize("path,payload", [("divide", {"a": 1, "b": 0}), ("divide", {"a": 1, "b": -0.0}), ("multiply", {"a": 1e308, "b": 10})])
def test_arithmetic_errors(path, payload):
    assert client.post(f"/{path}", json=payload).status_code == 400


@pytest.mark.parametrize("path,payload", [("add", {"a": True, "b": 2}), ("add", {"a": "2", "b": 2}), ("add", {"a": 2}), ("add", {"a": 1, "b": 2, "extra": 3}), ("calculate", {"a": 1, "b": 2, "op": "**"}), ("evaluate", {"expression": "a", "variables": {"a": False}}), ("evaluate", {"expression": "1"*1001}), ("evaluate", {"expression": "a", "variables": {"a.b": 1}})])
def test_validation(path, payload):
    assert client.post(f"/{path}", json=payload).status_code == 422


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "1e999"])
def test_nonfinite_input(value):
    assert client.post("/add", content='{"a": '+value+', "b": 1}', headers={"Content-Type": "application/json"}).status_code == 422


def test_malformed_json():
    assert client.post("/add", content='{', headers={"Content-Type": "application/json"}).status_code == 422


def test_documentation():
    assert client.get("/").status_code == 200
    assert client.get("/docs").status_code == 200
    assert "/evaluate" in client.get("/openapi.json").json()["paths"]


def test_limits():
    with pytest.raises(CalculationError):
        evaluate("1"*1001)
