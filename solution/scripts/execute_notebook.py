from __future__ import annotations

import asyncio
import contextlib
import io
import json
import sys
import traceback
from pathlib import Path

from IPython.core.interactiveshell import InteractiveShell

CELL_TIMEOUT_SECONDS = 300


def stream_output(name: str, text: str) -> dict:
    return {"output_type": "stream", "name": name, "text": text.splitlines(keepends=True)}


def error_output(exc: BaseException) -> dict:
    return {
        "output_type": "error",
        "ename": exc.__class__.__name__,
        "evalue": str(exc),
        "traceback": traceback.format_exception(exc),
    }


async def execute_notebook(path: Path) -> int:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    shell = InteractiveShell.instance()
    execution_count = 1

    for cell in notebook["cells"]:
        if cell.get("cell_type") != "code":
            continue

        source = "".join(cell.get("source", []))
        stdout = io.StringIO()
        outputs: list[dict] = []

        try:
            with contextlib.redirect_stdout(stdout):
                result = await asyncio.wait_for(
                    shell.run_cell_async(source, store_history=False),
                    timeout=CELL_TIMEOUT_SECONDS,
                )
            if result.error_in_exec:
                outputs.append(error_output(result.error_in_exec))
                cell["outputs"] = outputs
                cell["execution_count"] = execution_count
                path.write_text(json.dumps(notebook, indent=2), encoding="utf-8")
                return 1
            if result.error_before_exec:
                outputs.append(error_output(result.error_before_exec))
                cell["outputs"] = outputs
                cell["execution_count"] = execution_count
                path.write_text(json.dumps(notebook, indent=2), encoding="utf-8")
                return 1
        except BaseException as exc:
            outputs.append(error_output(exc))
            cell["outputs"] = outputs
            cell["execution_count"] = execution_count
            path.write_text(json.dumps(notebook, indent=2), encoding="utf-8")
            return 1

        if stdout.getvalue():
            outputs.append(stream_output("stdout", stdout.getvalue()))
        cell["outputs"] = outputs
        cell["execution_count"] = execution_count
        execution_count += 1
        path.write_text(json.dumps(notebook, indent=2) + "\n", encoding="utf-8")

    path.write_text(json.dumps(notebook, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(execute_notebook(Path(sys.argv[1]))))
