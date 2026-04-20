from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace

from rally.adapters.base import AdapterReadinessFailure
from rally.adapters.mcp_readiness import (
    allowed_mcp_names,
    probe_stdio_startability,
    probe_timeout_sec,
    render_probe_failure,
)


def _completed(
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["probe"], returncode=returncode, stdout=stdout, stderr=stderr)


def _flow_with_agents(agent_mcps: dict[str, tuple[str, ...]]) -> object:
    # allowed_mcp_names only reads flow.agents.values() and each agent's
    # .allowed_mcps tuple, so a SimpleNamespace keeps these tests hermetic
    # and independent of FlowDefinition churn.
    agents = {
        key: SimpleNamespace(allowed_mcps=mcps)
        for key, mcps in agent_mcps.items()
    }
    return SimpleNamespace(agents=agents)


class AllowedMcpNamesTests(unittest.TestCase):
    # Protects the flow-wide MCP aggregation that drives both adapters' MCP
    # config generation and readiness probe selection. Regression here would
    # drop an MCP for some agents or quietly double-probe another, which the
    # operator would only notice as a mid-turn MCP-tool error.

    def test_empty_flow_returns_empty_tuple(self) -> None:
        self.assertEqual(allowed_mcp_names(_flow_with_agents({})), ())

    def test_agents_with_no_mcps_return_empty_tuple(self) -> None:
        self.assertEqual(allowed_mcp_names(_flow_with_agents({"a": (), "b": ()})), ())

    def test_names_are_deduped_across_agents_and_sorted(self) -> None:
        flow = _flow_with_agents(
            {
                "scope_lead": ("z-mcp", "fixture-repo"),
                "change_engineer": ("fixture-repo", "issues-http"),
                "proof_engineer": ("a-mcp",),
            }
        )
        self.assertEqual(
            allowed_mcp_names(flow),
            ("a-mcp", "fixture-repo", "issues-http", "z-mcp"),
        )


class ProbeTimeoutSecTests(unittest.TestCase):
    # Protects the 5-second cap on MCP startup probes. A regression that drops
    # the cap would let a slow MCP freeze `rally run` startup; a regression
    # that ignores a valid short timeout would waste operator wall-clock time.

    def test_none_falls_back_to_five_seconds(self) -> None:
        self.assertEqual(probe_timeout_sec(None), 5.0)

    def test_non_numeric_falls_back_to_five_seconds(self) -> None:
        self.assertEqual(probe_timeout_sec("3"), 5.0)
        self.assertEqual(probe_timeout_sec([3]), 5.0)

    def test_boolean_true_is_rejected_even_though_it_is_int_subclass(self) -> None:
        # `True` is technically an int in Python; guard prevents it from
        # masquerading as a 1-second timeout.
        self.assertEqual(probe_timeout_sec(True), 5.0)

    def test_non_positive_falls_back_to_five_seconds(self) -> None:
        self.assertEqual(probe_timeout_sec(0), 5.0)
        self.assertEqual(probe_timeout_sec(-2.0), 5.0)

    def test_valid_value_below_cap_passes_through(self) -> None:
        self.assertEqual(probe_timeout_sec(2.5), 2.5)

    def test_valid_value_above_cap_is_clamped(self) -> None:
        self.assertEqual(probe_timeout_sec(10), 5.0)
        self.assertEqual(probe_timeout_sec(9999.0), 5.0)


class RenderProbeFailureTests(unittest.TestCase):
    # Protects the operator-facing reason string. The stderr > stdout > generic
    # precedence is what an operator reads first when an MCP probe fails, so
    # drift here makes MCP failures harder to diagnose.

    def test_stderr_is_preferred_when_present(self) -> None:
        self.assertEqual(
            render_probe_failure(
                command=["x"],
                returncode=1,
                stdout="ignored",
                stderr="  boom\n",
            ),
            "boom",
        )

    def test_stdout_last_line_is_used_when_stderr_is_blank(self) -> None:
        self.assertEqual(
            render_probe_failure(
                command=["x"],
                returncode=1,
                stdout="line one\nline two\n",
                stderr="   ",
            ),
            "line two",
        )

    def test_generic_message_when_both_streams_are_blank(self) -> None:
        self.assertEqual(
            render_probe_failure(
                command=["uvx", "fixture-repo-mcp"],
                returncode=2,
                stdout="",
                stderr="",
            ),
            "`uvx fixture-repo-mcp` exited with code 2.",
        )

    def test_none_streams_fall_back_to_generic_message(self) -> None:
        self.assertEqual(
            render_probe_failure(command=["x"], returncode=7, stdout=None, stderr=None),
            "`x` exited with code 7.",
        )


class ProbeStdioStartabilityTests(unittest.TestCase):
    # Protects the probe that gates every MCP-backed turn: this is Rally's only
    # pre-invoke check that the configured MCP command can be started by the
    # host. The probe runs once in `check_turn_readiness`, never inside
    # `invoke` — so a regression that silently accepts a broken config would
    # surface as an opaque mid-turn MCP-tool error with no clear blocker.
    #
    # Separate staleness risk (documented, not closed in this pass): because
    # the probe only runs at readiness time, an MCP that dies between probe
    # and invoke will not be re-checked. A future behavior-change pass could
    # add a re-probe on invoke or a watchdog; RF7 stayed proof-only because
    # that fix spans two adapters and is larger than one audit pass.

    def _probe(
        self,
        *,
        command_name: object = "fixture-mcp",
        raw_args: object = None,
        raw_env: object = None,
        raw_cwd: object = None,
        run_home: Path = Path("/tmp/run_home"),
        env: dict[str, str] | None = None,
        subprocess_run: object = None,
        config_label: str = "Codex config",
        timeout_sec: float = 5.0,
    ) -> AdapterReadinessFailure | None:
        return probe_stdio_startability(
            mcp_name="fixture-repo",
            command_name=command_name,
            raw_args=raw_args,
            raw_env=raw_env,
            raw_cwd=raw_cwd,
            run_home=run_home,
            env=env or {},
            subprocess_run=subprocess_run or (lambda *a, **kw: _completed()),
            config_label=config_label,
            timeout_sec=timeout_sec,
        )

    def test_missing_command_is_rejected_without_running_subprocess(self) -> None:
        def fail_if_called(*a: object, **kw: object) -> subprocess.CompletedProcess[str]:
            self.fail("subprocess must not run when command is missing")

        for command_name in (None, "", "   ", 42):
            with self.subTest(command_name=command_name):
                failure = self._probe(command_name=command_name, subprocess_run=fail_if_called)
                self.assertIsNotNone(failure)
                assert failure is not None
                self.assertEqual(failure.failed_check, "command_startability")
                self.assertEqual(failure.mcp_name, "fixture-repo")
                self.assertIn("Codex config", failure.reason)
                self.assertIn("stdio command", failure.reason)

    def test_non_list_args_are_rejected_without_running_subprocess(self) -> None:
        def fail_if_called(*a: object, **kw: object) -> subprocess.CompletedProcess[str]:
            self.fail("subprocess must not run when args shape is wrong")

        failure = self._probe(raw_args="--flag", subprocess_run=fail_if_called)
        self.assertIsNotNone(failure)
        assert failure is not None
        self.assertEqual(failure.failed_check, "command_startability")
        self.assertIn("non-string stdio args", failure.reason)

    def test_args_with_non_string_item_are_rejected(self) -> None:
        def fail_if_called(*a: object, **kw: object) -> subprocess.CompletedProcess[str]:
            self.fail("subprocess must not run when any arg is non-string")

        failure = self._probe(raw_args=["--repo", 5], subprocess_run=fail_if_called)
        self.assertIsNotNone(failure)
        assert failure is not None
        self.assertEqual(failure.failed_check, "command_startability")
        self.assertIn("non-string stdio args", failure.reason)

    def test_timeout_expiry_is_treated_as_successful_startup(self) -> None:
        # Design note codified here: a TimeoutExpired from the probe means the
        # launcher survived past the short startup window without crashing.
        # That is the "healthy stdio launcher" signal — probe returns None.
        def raise_timeout(command: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
            raise subprocess.TimeoutExpired(cmd=command, timeout=float(kw["timeout"]))

        result = self._probe(command_name="uvx", subprocess_run=raise_timeout)
        self.assertIsNone(result)

    def test_file_not_found_names_the_missing_command(self) -> None:
        def raise_fnf(command: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
            raise FileNotFoundError(command[0])

        failure = self._probe(command_name="missing-mcp", subprocess_run=raise_fnf)
        self.assertIsNotNone(failure)
        assert failure is not None
        self.assertEqual(failure.failed_check, "command_startability")
        self.assertIn("missing-mcp", failure.reason)
        self.assertIn("was not found", failure.reason)

    def test_generic_os_error_is_translated_to_could_not_start(self) -> None:
        def raise_os_error(command: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
            raise OSError("permission denied")

        failure = self._probe(command_name="locked-mcp", subprocess_run=raise_os_error)
        self.assertIsNotNone(failure)
        assert failure is not None
        self.assertEqual(failure.failed_check, "command_startability")
        self.assertIn("locked-mcp", failure.reason)
        self.assertIn("could not start", failure.reason)
        self.assertIn("permission denied", failure.reason)

    def test_non_zero_exit_returns_failure_with_rendered_reason(self) -> None:
        def exit_nonzero(command: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
            return _completed(returncode=2, stdout="", stderr="startup error\n")

        failure = self._probe(subprocess_run=exit_nonzero)
        self.assertIsNotNone(failure)
        assert failure is not None
        self.assertEqual(failure.failed_check, "command_startability")
        self.assertEqual(failure.reason, "startup error")

    def test_non_zero_exit_without_output_uses_generic_command_message(self) -> None:
        def exit_nonzero_silent(command: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
            return _completed(returncode=3, stdout="", stderr="")

        failure = self._probe(
            command_name="uvx",
            raw_args=["fixture-repo-mcp", "--repo", "/tmp/demo"],
            subprocess_run=exit_nonzero_silent,
        )
        self.assertIsNotNone(failure)
        assert failure is not None
        self.assertEqual(
            failure.reason,
            "`uvx fixture-repo-mcp --repo /tmp/demo` exited with code 3.",
        )

    def test_env_merges_base_with_raw_env_and_drops_non_string_values(self) -> None:
        captured: dict[str, object] = {}

        def capture(command: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
            captured["command"] = command
            captured["env"] = dict(kw["env"])
            captured["cwd"] = kw["cwd"]
            captured["timeout"] = kw["timeout"]
            raise subprocess.TimeoutExpired(cmd=command, timeout=float(kw["timeout"]))

        result = self._probe(
            command_name="uvx",
            raw_args=["fixture-repo-mcp"],
            raw_env={
                "PROJECT_ROOT": "/workspace/fixtures",
                "BASE_KEEPS": "unchanged",
                "BASE_OVERRIDE": "raw-wins",
                123: "non-string-key",
                "BAD_VALUE": 7,
            },
            env={"BASE_KEEPS": "unchanged", "BASE_OVERRIDE": "base-loses"},
            subprocess_run=capture,
            timeout_sec=3.0,
        )

        self.assertIsNone(result)
        self.assertEqual(captured["command"], ["uvx", "fixture-repo-mcp"])
        self.assertEqual(captured["timeout"], 3.0)
        merged_env = captured["env"]
        assert isinstance(merged_env, dict)
        self.assertEqual(merged_env["PROJECT_ROOT"], "/workspace/fixtures")
        self.assertEqual(merged_env["BASE_KEEPS"], "unchanged")
        self.assertEqual(merged_env["BASE_OVERRIDE"], "raw-wins")
        self.assertNotIn(123, merged_env)
        self.assertNotIn("BAD_VALUE", merged_env)

    def test_cwd_defaults_to_run_home_when_raw_cwd_is_absent_or_blank(self) -> None:
        captured: list[object] = []

        def capture(command: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
            captured.append(kw["cwd"])
            raise subprocess.TimeoutExpired(cmd=command, timeout=float(kw["timeout"]))

        run_home = Path("/tmp/rally-run-home")
        for raw_cwd in (None, "", "   "):
            with self.subTest(raw_cwd=raw_cwd):
                self._probe(raw_cwd=raw_cwd, run_home=run_home, subprocess_run=capture)
        self.assertEqual(captured, [run_home, run_home, run_home])

    def test_cwd_override_is_used_when_raw_cwd_is_a_string(self) -> None:
        captured: dict[str, object] = {}

        def capture(command: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
            captured["cwd"] = kw["cwd"]
            raise subprocess.TimeoutExpired(cmd=command, timeout=float(kw["timeout"]))

        self._probe(raw_cwd="/opt/fixture-repo", run_home=Path("/tmp/home"), subprocess_run=capture)
        self.assertEqual(captured["cwd"], Path("/opt/fixture-repo"))


if __name__ == "__main__":
    unittest.main()
