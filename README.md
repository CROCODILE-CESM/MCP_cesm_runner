# cesm-runner-mcp

MCP server for driving CESM case lifecycle: setup → build → submit → monitor.

Complements the [CrocoDash MCP](https://github.com/CROCODILE-CESM/MCP_CrocoDash), which handles grid creation and forcing. This server picks up where that one leaves off — once a case directory exists, this server drives the CIME build/run pipeline.

## Tools

| Tool | Purpose |
|------|---------|
| `list_cases(search_root)` | Find all CESM cases under a directory |
| `get_case_status(case_dir)` | Read CaseStatus log + key XML config |
| `check_input_data(case_dir)` | Verify all required input files are staged |
| `xmlquery(case_dir, variable)` | Query any CESM XML variable |
| `xmlchange(case_dir, variable, value)` | Set a CESM XML variable |
| `preview_run(case_dir)` | Show PE layout and batch script without submitting |
| `case_setup(case_dir)` | Run `./case.setup` |
| `case_build(case_dir)` | Compile the model (`./case.build`) |
| `case_submit(case_dir)` | Submit to PBS/slurm (`./case.submit`) |
| `tail_log(case_dir, component, lines)` | Read recent run log output |
| `get_job_status(case_dir)` | Check PBS/slurm queue for this case's job |
| `list_compsets(cesmroot, filter)` | List available compsets in a CESM install |

## Resources

| URI | Content |
|-----|---------|
| `cesm://case/{case_dir}/env` | All XML config variables |
| `cesm://case/{case_dir}/status` | CaseStatus log |
| `cesm://case/{case_dir}/logs` | List of run log files |

## Setup

```bash
pip install -e .
# or in the CrocoDash conda env:
conda run -n CrocoDash pip install -e .
```

## Running

```bash
cesm-runner-mcp
# or
python server.py
```

Wire up to Claude Code by adding to `.mcp.json`:

```json
{
  "mcpServers": {
    "cesm-runner": {
      "command": "python",
      "args": ["/path/to/MCP_cesm_runner/server.py"]
    }
  }
}
```

## Design

- **Stateless**: each tool reads from the filesystem; no in-memory state
- **Shells out to CIME scripts**: uses `./xmlquery`, `./case.setup`, etc. directly — version-safe and matches what users run manually
- **Works with any CESM install**: not specific to CrocoDash or MOM6

## CESM install on Derecho

Default reference install: `~/work/installs/cesm3_maddd_new`

Cases live in: `~/croc_cases/`
