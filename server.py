"""CESM Runner MCP — drives any CESM case through setup, build, submit, and monitoring."""

from fastmcp import FastMCP

from tools.inspect import list_cases, get_case_status, check_input_data
from tools.lifecycle import case_setup, case_build, case_submit
from tools.config import xmlquery, xmlchange, preview_run
from tools.logs import tail_log, get_job_status
from tools.discovery import list_compsets
from tools.container import build_sandbox, start_container, container_exec, stop_container, list_containers

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
mcp.add_tool(container_exec)
mcp.add_tool(stop_container)
mcp.add_tool(list_containers)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
