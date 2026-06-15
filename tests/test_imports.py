import importlib
import io
import contextlib
from unittest.mock import patch
import asyncio
import unittest
from pathlib import Path


class ImportSmokeTests(unittest.TestCase):
    def test_settings_paths_point_inside_solution(self):
        from solution.config import settings

        config = settings()
        solution_root = Path(__file__).resolve().parents[1] / "solution"

        self.assertEqual(solution_root, config.SOLUTION_ROOT)
        self.assertEqual(solution_root / "data", config.DATA_DIR)
        self.assertTrue(config.CULTPASS_DB.exists(), config.CULTPASS_DB)
        self.assertTrue(config.UDAHUB_DB.exists(), config.UDAHUB_DB)

    def test_application_modules_import_from_solution_package_root(self):
        modules = [
            "solution.app",
            "solution.agentic.workflow",
            "solution.agentic.tools.mcp_client",
            "solution.agentic.tools.rag_server",
            "solution.scripts.build_index",
        ]

        for module in modules:
            with self.subTest(module=module):
                importlib.import_module(module)

    def test_mcp_connections_use_project_root_and_explicit_api_env(self):
        from solution.config import settings
        from solution.agentic.tools import mcp_client

        config = settings()
        connections = mcp_client._connections()

        for connection in connections.values():
            self.assertEqual(str(config.PROJECT_ROOT), connection["cwd"])
            self.assertIn("env", connection)
            self.assertTrue(connection["env"].get("OPENAI_API_KEY"))
            self.assertTrue(connection["env"].get("GROQ_API_KEY"))

    def test_reservation_tool_uses_plural_public_name(self):
        from solution.agentic.tools import db_ops
        from solution.agentic.tools.mcp_client import DB_TOOL_NAMES

        self.assertIn("list_reservations", DB_TOOL_NAMES)
        self.assertTrue(hasattr(db_ops, "list_reservations"))
        self.assertIs(db_ops.list_reservations, db_ops.list_reservation)


if __name__ == "__main__":
    unittest.main()
