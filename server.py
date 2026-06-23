"""CESM Runner MCP — drives any CESM case through setup, build, submit, and monitoring."""

from fastmcp import FastMCP

from tools.inspect import list_cases, get_case_status, check_input_data
from tools.lifecycle import case_setup, case_build, case_submit
from tools.config import xmlquery, xmlchange, preview_run
from tools.logs import tail_log, get_job_status
from tools.discovery import list_compsets

mcp = FastMCP("cesm-runner")

mcp.add_tool(list_cases)
mcp.add_tool(get_case_status)
mcp.add_tool(check_input_data)
mcp.add_tool(case_setup)
mcp.add_tool(case_build)
mcp.add_tool(case_submit)
mcp.add_tool(xmlquery)
mcp.add_tool(xmlchange)
mcp.add_tool(preview_run)
mcp.add_tool(tail_log)
mcp.add_tool(get_job_status)
mcp.add_tool(list_compsets)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
