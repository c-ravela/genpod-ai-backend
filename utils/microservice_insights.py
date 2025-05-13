from typing import Any, Dict, List, Optional, Tuple, Union

from rich import box
from rich.columns import Columns
from rich.console import Console, Group
from rich.table import Table

from utils.logger import logger

PRICING_PER_MODEL = {
    "openai": {
        "chatgpt-4o-latest": {"input_tokens": 5.00,  "output_tokens": 15.00},
        "gpt-4o-2024-08-06": {"input_tokens": 2.50,  "output_tokens": 10.00},
        "gpt-4o-2024-05-13": {"input_tokens": 5.00,  "output_tokens": 15.00},
        "gpt-4o-2024-11-20": {"input_tokens": 2.50,  "cached_input_tokens": 1.25, "output_tokens": 10.00},
        "gpt-3.5-turbo": {"input_tokens": 3.00,  "output_tokens": 6.00},
        "o1-preview-2024-09-12": {"input_tokens": 15.00, "cached_input_tokens": 7.50, "output_tokens": 60.00},
        "o1-mini-2024-09-12": {"input_tokens": 3.00,  "cached_input_tokens": 1.50, "output_tokens": 12.00},
        "o3-mini": {"input_tokens": 1.10,  "cached_input_tokens": 0.55, "output_tokens": 4.40},
    },
    "ollama": {
        "llama3": {}
    },
    "anthropic": {
        "claude-3-5-sonnet-20240620": {"input_tokens": 3.00, "prompt_caching_write": 3.75, "prompt_caching_read": 0.30, "output_tokens": 15.00},
        "claude-instant-1.2": {"input_tokens": 0.80, "output_tokens": 2.40},
    },
    "google": {
        "gemini-2.5-pro-preview-05-06": {"input_tokens": 1.25, "output_tokens": 10.00},
        "gemini-2.5-flash-preview-04-17": {"input_tokens": 0.15, "audio_input_tokens": 1.00, "output_tokens": 3.50},
        "gemini-2.0-flash": {"input_tokens": 0.15, "audio_input_tokens": 1.00, "output_tokens": 0.60},
        "gemini-2.0-flash-lite": {"input_tokens": 0.075, "audio_input_tokens": 0.075, "output_tokens": 0.30},
    },
}

def _get_items_list(data: Dict[str, Any], key: str) -> List[Any]:
    container = data.get(key)
    items = getattr(container, "items", []) if container else []
    return items or []

class MicroserviceInsights:
    """
    Generate and render insights for a microservice project side‑by‑side
    using Rich Tables and Columns.
    """

    def __init__(self,
                 data: Dict[str, Any],
                 token_metrics: Optional[List[Any]] = None,
                 current_agent: Optional[Dict[str, Any]] = None) -> None:
        self.data = data
        self.token_metrics = token_metrics or []
        self.current_agent = current_agent or {}
        self.console = Console()
        logger.info("MicroserviceInsights initialized.")

    def _get_field(self, obj: Union[Dict[str, Any], Any], field: str) -> Any:
        if isinstance(obj, dict):
            return obj.get(field)
        return getattr(obj, field, None)

    def _truncate_text(self, text: str, max_length: int = 100) -> str:
        if len(text) <= max_length:
            return text
        return text[:max_length].rstrip() + "…"

    def _count_done_items(self, items: List[Any]) -> int:
        done = 0
        for item in items:
            status = (
                getattr(item, 'status', None)
                or getattr(item, 'task_status', None)
                or getattr(item, 'issue_status', None)
            )
            if str(status) == 'DONE':
                done += 1
        return done

    def _compute_completion_percentage(self) -> str:
        cats = ['tasks', 'planned_tasks', 'issues', 'planned_issues']
        lists = [_get_items_list(self.data, c) for c in cats]
        done = sum(self._count_done_items(lst) for lst in lists)
        total = sum(len(lst) for lst in lists)
        return "0.00%" if total == 0 else f"{done/total*100:.2f}%"

    def _build_overview_table(self) -> Table:
        t = Table(title="Project Overview", box=box.ROUNDED, expand=True)
        t.add_column("Metric", no_wrap=True)
        t.add_column("Value", overflow="fold")
        t.add_row("Service Name",      self.data.get('microservice_name', 'N/A'))
        t.add_row("Current Status",    str(self.data.get('project_status', 'N/A')))
        t.add_row("Completion (%)",    self._compute_completion_percentage())
        t.add_row("Agents Status",     self.data.get('agents_status', 'N/A'))
        t.add_row("Total Tasks",       str(len(_get_items_list(self.data, 'tasks'))))
        t.add_row("Total Planned Tasks", str(len(_get_items_list(self.data, 'planned_tasks'))))
        t.add_row("Total Issues",      str(len(_get_items_list(self.data, 'issues'))))
        t.add_row("User Prompt",       self._truncate_text(self.data.get('user_prompt', 'N/A'), 100))
        t.add_row("Project Directory", self.data.get('project_directory', 'N/A'))
        return t

    def _build_planned_tasks_table(self) -> Table:
        planned = _get_items_list(self.data, 'planned_tasks')
        current = self.data.get('current_planned_task') or {}
        cur_id = self._get_field(current, 'task_id') or "N/A"
        idx = next((i+1 for i,t in enumerate(planned) if getattr(t, 'task_id', None)==cur_id), 0)
        t = Table(title="Planned Tasks", box=box.ROUNDED, expand=True)
        t.add_column("Attribute", no_wrap=True)
        t.add_column("Value", overflow="fold")
        t.add_row("Current Planned Task ID", cur_id)
        t.add_row("Position in Queue",       str(idx))
        t.add_row("Total Planned Tasks",     str(len(planned)))
        return t

    def _build_issues_table(self) -> Table:
        issues = _get_items_list(self.data, 'issues')
        current = self.data.get('current_issue') or {}
        cur_id = self._get_field(current, 'issue_id') or "N/A"
        idx = next((i+1 for i,iss in enumerate(issues) if getattr(iss, 'issue_id', None)==cur_id), 0)
        t = Table(title="Issues", box=box.ROUNDED, expand=True)
        t.add_column("Attribute", no_wrap=True)
        t.add_column("Value", overflow="fold")
        t.add_row("Current Issue Position", str(idx))
        t.add_row("Total Issues",           str(len(issues)))
        return t

    def _build_token_metrics_tables(self) -> List[Table]:
        if not self.token_metrics:
            empty = Table(title="Token Metrics", box=box.ROUNDED, expand=True)
            empty.add_column("Info")
            empty.add_row("No token metrics available.")
            return [empty]

        # group usage
        groups: Dict[Tuple[str,str],Dict[str,float]] = {}
        missing = []
        for tm in self.token_metrics:
            key = (tm.provider, tm.model)
            grp = groups.setdefault(key, {"in":0.0, "out":0.0, "calls":0})
            grp["in"]   += tm.input_tokens
            grp["out"]  += tm.output_tokens
            grp["calls"]+= 1

        # cost‐by‐model table
        cost_tbl = Table(title="Token Metrics by Model", box=box.ROUNDED, expand=True)
        cost_tbl.add_column("Provider/Model", no_wrap=True)
        cost_tbl.add_column("Calls", justify="right")
        cost_tbl.add_column("Input Tokens (Cost)", justify="right")
        cost_tbl.add_column("Output Tokens (Cost)", justify="right")
        cost_tbl.add_column("Total Cost (USD)", justify="right")

        total_cost = 0.0
        for (prov,model), vals in groups.items():
            in_toks = int(vals["in"])
            out_toks= int(vals["out"])
            calls   = vals["calls"]
            pricing = PRICING_PER_MODEL.get(prov,{}).get(model,{})
            in_rate  = pricing.get("input_tokens",0)/1e6
            out_rate = pricing.get("output_tokens",0)/1e6
            if not pricing:
                missing.append(f"{prov}/{model}")
            cost_in  = in_toks * in_rate
            cost_out = out_toks * out_rate
            mc       = cost_in + cost_out
            total_cost += mc

            cost_tbl.add_row(
                f"{prov}/{model}",
                str(calls),
                f"{in_toks:,d} (${'{:.2f}'.format(cost_in)})",
                f"{out_toks:,d} (${'{:.2f}'.format(cost_out)})",
                f"${mc:.2f}"
            )

        # grand total row
        all_calls = sum(v["calls"] for v in groups.values())
        all_in    = sum(int(v["in"])  for v in groups.values())
        all_out   = sum(int(v["out"]) for v in groups.values())
        cost_tbl.add_row(
            "ALL MODELS",
            str(all_calls),
            f"{all_in:,d}",
            f"{all_out:,d}",
            f"${total_cost:.2f}"
        )

        if missing:
            cost_tbl.add_section()
            cost_tbl.add_row(f"[red]⚠️ Missing pricing for {', '.join(sorted(set(missing)))}[/]")

        # summary table
        sum_tbl = Table(title="Token Metrics Summary", box=box.ROUNDED, expand=True)
        sum_tbl.add_column("Metric", no_wrap=True)
        sum_tbl.add_column("Value", justify="right")
        total_dur = sum(tm.llm_duration for tm in self.token_metrics)
        avg_dur   = total_dur / len(self.token_metrics)
        sum_tbl.add_row("Total Calls",             f"{all_calls:,d}")
        sum_tbl.add_row("Aggregate Input Tokens",  f"{all_in:,d}")
        sum_tbl.add_row("Aggregate Output Tokens", f"{all_out:,d}")
        sum_tbl.add_row("Avg Call Duration (s)",   f"{avg_dur:.2f}")
        sum_tbl.add_row("Total LLM Time (s)",      f"{total_dur:.2f}")

        return [cost_tbl, sum_tbl]

    def _build_active_agent_table(self) -> Table:
        if not self.current_agent:
            return Table()  # empty
        tbl = Table(title="Active Agent State", box=box.ROUNDED, expand=True)
        tbl.add_column("Agent",       no_wrap=True)
        tbl.add_column("Active Node", no_wrap=True)
        tbl.add_column("Stage",       no_wrap=True)
        tbl.add_row(
            self._get_field(self.current_agent, 'agent_name') or "N/A",
            self._get_field(self.current_agent, 'active_node') or "N/A",
            self._get_field(self.current_agent, 'current_mode_stage') or "N/A",
        )
        return tbl

    def build_renderable(self):
        """Return a single Renderable for the Live display."""
        overview = self._build_overview_table()
        planned  = self._build_planned_tasks_table()
        issues   = self._build_issues_table()
        agent    = self._build_active_agent_table()

        token_tables = self._build_token_metrics_tables()
        if len(token_tables) == 1:
            # only a single “no metrics” table, so make a blank summary
            cost_tbl    = token_tables[0]
            summary_tbl = Table(title="Token Metrics Summary", box=box.ROUNDED, expand=True)
            summary_tbl.add_column("Info")
            summary_tbl.add_row("No token metrics available.")
        else:
            cost_tbl, summary_tbl = token_tables

        top    = Columns([overview, Group(planned, issues, agent)], expand=True)
        bottom = Columns([summary_tbl, cost_tbl], expand=True)
        return Group(top, "\n", bottom)
