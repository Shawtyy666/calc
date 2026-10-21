"""HTTP API for the calculator."""

import re
from typing import Annotated, Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, field_validator

from app.calculator import CalculationError, calculate, evaluate

Number = Annotated[StrictInt | StrictFloat, Field(allow_inf_nan=False)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Operands(InputModel):
    a: Number
    b: Number


class Operation(Operands):
    op: Literal["+", "-", "*", "/"]


class Expression(InputModel):
    expression: str = Field(min_length=1, max_length=1000)
    variables: dict[str, Number] = Field(default_factory=dict, max_length=100)

    @field_validator("variables")
    @classmethod
    def valid_names(cls, values):
        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", name) for name in values):
            raise ValueError("Имена переменных: латинские буквы, цифры и _, до 64 символов")
        return values


class Result(BaseModel):
    result: float


app = FastAPI(title="FastAPI-калькулятор", version="1.0.0", description="Арифметика и безопасное вычисление выражений с переменными.")


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # Do not echo raw input: NaN/Infinity and error contexts are not JSON-safe.
    details = [
        {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})


@app.exception_handler(CalculationError)
async def calculation_error(request: Request, exc: CalculationError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/", tags=["Сервис"])
def index():
    return {"message": "FastAPI-калькулятор", "docs": "/docs"}


@app.post("/add", response_model=Result, tags=["Арифметика"])
def add(data: Operands):
    return {"result": calculate(data.a, "+", data.b)}


@app.post("/subtract", response_model=Result, tags=["Арифметика"])
def subtract(data: Operands):
    return {"result": calculate(data.a, "-", data.b)}


@app.post("/multiply", response_model=Result, tags=["Арифметика"])
def multiply(data: Operands):
    return {"result": calculate(data.a, "*", data.b)}


@app.post("/divide", response_model=Result, tags=["Арифметика"])
def divide(data: Operands):
    return {"result": calculate(data.a, "/", data.b)}


@app.post("/calculate", response_model=Result, tags=["Арифметика"])
def operation(data: Operation):
    return {"result": calculate(data.a, data.op, data.b)}


@app.post("/evaluate", response_model=Result, tags=["Выражения"])
def expression(data: Expression):
    return {"result": evaluate(data.expression, data.variables)}
