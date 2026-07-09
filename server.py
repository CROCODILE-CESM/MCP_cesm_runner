"""CESM Runner MCP — drives any CESM case through setup, build, submit, and monitoring.

Deployment paths (pair with CrocoDash MCP for case creation):

  PATH A — HPC batch queue (no container):
    case_setup → case_build → case_submit
    Build takes 10–30 min on a compute node via PBS.

  PATH B — HPC + container, no queue (fast iteration, Derecho):
    build_sandbox  (one-time, ~1hr)
    start_container(scratch_dir=...) → run_case_in_container(container, bundle_dir)
    Full setup+build+run inside Apptainer; no queue wait.

  PATH C — Laptop + container (Podman), no queue:
    start_container(inputdata_dir=...) → run_case_in_container(container, bundle_dir)
    Pulls ghcr.io/crocodile-cesm/crocontainer:latest-amd64 automatically.

run_case_in_container is the single call for PATH B and C:
  it copies the bundle → /workspace/bundle/ and runs run_case.sh end-to-end.
"""

from fastmcp import FastMCP

from tools.inspect import list_cases, get_case_status, check_input_data
from tools.lifecycle import case_setup, case_build, case_submit
from tools.config import xmlquery, xmlchange, preview_run
from tools.logs import tail_log, get_job_status
from tools.discovery import list_compsets
from tools.container import build_sandbox, start_container, container_exec, stop_container, list_containers, run_case_in_container

mcp = FastMCP("cesm-runner")

# Case inspection
mcp.add_tool(list_cases)
mcp.add_tool(get_case_status)
mcp.add_tool(check_input_data)

# Case lifecycle (support optional container= arg for crocontainer sessions)
mcp.add_tool(case_setup)
mcp.add_tool(case_build)
mcp.add_tool(case_submit)

# XML config
mcp.add_tool(xmlquery)
mcp.add_tool(xmlchange)
mcp.add_tool(preview_run)

# Monitoring
mcp.add_tool(tail_log)
mcp.add_tool(get_job_status)

# Discovery
mcp.add_tool(list_compsets)

# Container management (crocontainer fast-iteration path)
mcp.add_tool(build_sandbox)
mcp.add_tool(start_container)
mcp.add_tool(run_case_in_container)
mcp.add_tool(container_exec)
mcp.add_tool(stop_container)
mcp.add_tool(list_containers)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
