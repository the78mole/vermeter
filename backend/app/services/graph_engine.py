"""Graph-based billing calculation engine.

Nodes:
  - SourceNode   : reads consumption value for a meter + period
  - MathNode     : applies a formula like (inputA + inputB) * factor
  - SplitterNode : splits one input into two outputs by ratio
  - SinkNode     : receives final cost amount, stores line item

Uses NetworkX to perform topological sort and execute the DAG.
"""

from __future__ import annotations

import ast
import logging
import operator
import math
from datetime import date
from decimal import Decimal
from typing import Any

import networkx as nx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import BillLineItem, MeterReading, Meter
from app.models.schemas import BillingGraph, GraphCalculationResult, GraphNode

logger = logging.getLogger(__name__)


class GraphExecutionError(Exception):
    pass


# ---------------------------------------------------------------------------
# Safe math expression evaluator (no eval / exec)
# ---------------------------------------------------------------------------

# Allowed AST node types – only basic arithmetic, no attribute access, no calls
_ALLOWED_AST_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    ast.Name,
    # Operators
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.UAdd, ast.USub,
)

_BINARY_OPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS: dict[type, Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_MAX_POW_EXPONENT = 100  # Guard against expensive pow like 2**1000000


def _safe_eval(node: ast.AST, namespace: dict[str, float]) -> float:
    """Recursively evaluate a pre-parsed AST using only whitelisted node types."""
    if not isinstance(node, _ALLOWED_AST_NODES):
        raise GraphExecutionError(f"Disallowed expression node: {type(node).__name__}")

    if isinstance(node, ast.Expression):
        return _safe_eval(node.body, namespace)

    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise GraphExecutionError("Only numeric literals are allowed in formulas")
        return float(node.value)

    if isinstance(node, ast.Name):
        name = node.id
        if name not in namespace:
            raise GraphExecutionError(f"Unknown variable in formula: '{name}'")
        return float(namespace[name])

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BINARY_OPS:
            raise GraphExecutionError(f"Unsupported operator: {op_type.__name__}")
        left = _safe_eval(node.left, namespace)
        right = _safe_eval(node.right, namespace)
        # Guard: prevent runaway exponentiation
        if op_type is ast.Pow and abs(right) > _MAX_POW_EXPONENT:
            raise GraphExecutionError(f"Exponent {right} exceeds maximum allowed value of {_MAX_POW_EXPONENT}")
        return _BINARY_OPS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARY_OPS:
            raise GraphExecutionError(f"Unsupported unary operator: {op_type.__name__}")
        operand = _safe_eval(node.operand, namespace)
        return _UNARY_OPS[op_type](operand)

    raise GraphExecutionError(f"Unhandled AST node type: {type(node).__name__}")


def safe_math_eval(formula: str, namespace: dict[str, float]) -> float:
    """
    Parse and evaluate a simple arithmetic formula without using eval().

    Supports: +, -, *, /, //, %, ** and named variables from namespace.
    Raises GraphExecutionError on any disallowed construct or parse error.
    """
    try:
        tree = ast.parse(formula.strip(), mode="eval")
    except SyntaxError as exc:
        raise GraphExecutionError(f"Formula syntax error: {exc}") from exc

    return _safe_eval(tree, namespace)


class GraphEngine:
    """Execute a billing calculation graph (DAG) and return calculation trace."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def execute(
        self,
        graph: BillingGraph,
        bill_id: str | None = None,
    ) -> GraphCalculationResult:
        """
        Parse, validate, and execute the billing graph.
        Returns node results and full calculation trace.
        """
        errors: list[str] = []
        node_results: dict[str, Any] = {}
        trace: dict[str, Any] = {"nodes": {}, "edges": []}

        try:
            G = self._build_nx_graph(graph)
            self._validate_dag(G)
            sorted_nodes = list(nx.topological_sort(G))
        except GraphExecutionError as exc:
            return GraphCalculationResult(node_results={}, calculation_trace={}, errors=[str(exc)])

        node_map: dict[str, GraphNode] = {n.id: n for n in graph.nodes}

        for node_id in sorted_nodes:
            node = node_map[node_id]
            predecessors = list(G.predecessors(node_id))
            input_values: dict[str, float] = {}

            for pred_id in predecessors:
                edge_data = G.edges[pred_id, node_id]
                source_handle = edge_data.get("source_handle", "output")
                target_handle = edge_data.get("target_handle", "input")
                pred_result = node_results.get(pred_id, {})
                value = pred_result.get(source_handle, 0.0) if isinstance(pred_result, dict) else float(pred_result)
                input_values[target_handle] = value

            try:
                result = await self._execute_node(node, input_values, graph)
            except Exception as exc:
                error_msg = f"Node {node_id} ({node.type}) failed: {exc}"
                errors.append(error_msg)
                logger.warning(error_msg)
                result = {}

            node_results[node_id] = result
            trace["nodes"][node_id] = {
                "type": node.type,
                "inputs": input_values,
                "outputs": result,
            }

        for edge in graph.edges:
            trace["edges"].append({"source": edge.source, "target": edge.target})

        if bill_id and not graph.preview_mode:
            await self._store_sink_items(graph, node_results, bill_id)

        return GraphCalculationResult(
            node_results=node_results,
            calculation_trace=trace,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Node executors
    # ------------------------------------------------------------------

    async def _execute_node(
        self, node: GraphNode, inputs: dict[str, float], graph: BillingGraph
    ) -> dict[str, float]:
        if node.type == "source":
            return await self._execute_source(node, graph)
        if node.type == "math":
            return self._execute_math(node, inputs)
        if node.type == "splitter":
            return self._execute_splitter(node, inputs)
        if node.type == "sink":
            return self._execute_sink(node, inputs)
        raise GraphExecutionError(f"Unknown node type: {node.type}")

    async def _execute_source(self, node: GraphNode, graph: BillingGraph) -> dict[str, float]:
        data = node.data
        meter_id: str = data.get("meter_id", "")

        # Preview mode: use sample data
        if graph.preview_mode and graph.sample_data:
            value = graph.sample_data.get(meter_id, 0.0)
            return {"output": value}

        period_start = date.fromisoformat(data["period_start"])
        period_end = date.fromisoformat(data["period_end"])

        result_start = await self.db.execute(
            select(MeterReading)
            .where(MeterReading.meter_id == meter_id, MeterReading.reading_date <= period_start)
            .order_by(MeterReading.reading_date.desc())
            .limit(1)
        )
        reading_start = result_start.scalar_one_or_none()

        result_end = await self.db.execute(
            select(MeterReading)
            .where(MeterReading.meter_id == meter_id, MeterReading.reading_date <= period_end)
            .order_by(MeterReading.reading_date.desc())
            .limit(1)
        )
        reading_end = result_end.scalar_one_or_none()

        if not reading_start or not reading_end:
            return {"output": 0.0}

        consumption = max(float(reading_end.value) - float(reading_start.value), 0.0)
        return {"output": consumption}

    def _execute_math(self, node: GraphNode, inputs: dict[str, float]) -> dict[str, float]:
        data = node.data
        formula: str = data.get("formula", "inputA + inputB")
        factor: float = float(data.get("factor", 1.0))

        # Build a safe evaluation namespace from inputs
        safe_ns: dict[str, float] = {k: float(v) for k, v in inputs.items()}
        # Also allow positional inputA, inputB from ordered inputs
        input_list = list(inputs.values())
        safe_ns.setdefault("inputA", input_list[0] if len(input_list) > 0 else 0.0)
        safe_ns.setdefault("inputB", input_list[1] if len(input_list) > 1 else 0.0)

        # Use the safe AST-based evaluator instead of eval()
        try:
            result = safe_math_eval(formula, safe_ns) * factor
        except GraphExecutionError:
            raise
        except Exception as exc:
            raise GraphExecutionError(f"Formula evaluation failed: {exc}") from exc

        return {"output": result}

    def _execute_splitter(self, node: GraphNode, inputs: dict[str, float]) -> dict[str, float]:
        data = node.data
        ratio = float(data.get("ratio", 0.3))
        total = inputs.get("input", list(inputs.values())[0] if inputs else 0.0)
        output_a = total * ratio
        output_b = total * (1.0 - ratio)
        return {"output_a": output_a, "output_b": output_b}

    def _execute_sink(self, node: GraphNode, inputs: dict[str, float]) -> dict[str, float]:
        value = inputs.get("input", list(inputs.values())[0] if inputs else 0.0)
        return {"result": value}

    # ------------------------------------------------------------------
    # Graph construction helpers
    # ------------------------------------------------------------------

    def _build_nx_graph(self, graph: BillingGraph) -> nx.DiGraph:
        G: nx.DiGraph = nx.DiGraph()
        for node in graph.nodes:
            G.add_node(node.id)
        for edge in graph.edges:
            G.add_edge(
                edge.source,
                edge.target,
                source_handle=edge.source_handle or "output",
                target_handle=edge.target_handle or "input",
            )
        return G

    def _validate_dag(self, G: nx.DiGraph) -> None:
        if not nx.is_directed_acyclic_graph(G):
            raise GraphExecutionError("The billing graph contains a cycle – it must be a DAG.")

    # ------------------------------------------------------------------
    # Persist sink results as BillLineItems
    # ------------------------------------------------------------------

    async def _store_sink_items(
        self,
        graph: BillingGraph,
        node_results: dict[str, Any],
        bill_id: str,
    ) -> None:
        for node in graph.nodes:
            if node.type != "sink":
                continue
            result = node_results.get(node.id, {})
            amount = float(result.get("result", 0.0))
            data = node.data
            item = BillLineItem(
                bill_id=bill_id,
                description=data.get("description", "Graph calculated cost"),
                cost_type=data.get("cost_type", "GRAPH"),
                total_amount=Decimal(str(amount)).quantize(Decimal("0.01")),
                unit_share=Decimal(str(amount)).quantize(Decimal("0.01")),
                distribution_key="GRAPH",
            )
            self.db.add(item)
        await self.db.flush()
