"""AI-powered code generation tools for Vissim.

Two tools that split the generate / execute cycle cleanly:

  1. vissim_generate_code  – NL query → Python function string (no side effects)
  2. vissim_execute_code   – executes a previously generated function against
                            the live Vissim COM root object

Usage flow (from any MCP client / Claude chat):
  1. Call vissim_generate_code(query="increase green time of SG1 by 3s")
     → returns {"code": "def vissim_action(Vissim): ..."}
  2. Review the code if desired (dry-run safety step)
  3. Call vissim_execute_code(code=<code from step 1>)
     → returns {"result": ..., "code": ...}

─────────────────────────────────────────────────────────────────
HOW TO ATTACH YOUR PDF / COM JSON SCHEMA
─────────────────────────────────────────────────────────────────
There are two points where your documentation plugs in:

OPTION A – Inline in the system prompt (simplest, works today)
  Open _build_system_prompt() below and paste your extracted COM JSON
  into the SCHEMA_CONTEXT block.  Keep it under ~60 k tokens.
  The JSON you've been building (hierarchy + traversal paths) is ideal here.

OPTION B – PDF attached per call (richer context, slightly slower)
  In _call_claude() below, uncomment the PDF block and set PDF_PATH to
  your manual file.  The PDF is base64-encoded and sent as a document
  block alongside the query.  This uses more tokens per call but gives
  the model the full manual including examples and edge cases.
  Best when your COM JSON isn't complete yet.

OPTION C – Both (recommended for production)
  System prompt = your structured COM JSON (fast, structured traversal).
  PDF attached = full manual as fallback for obscure attributes.
─────────────────────────────────────────────────────────────────
"""

import base64
import textwrap
from pathlib import Path
from typing import Optional

import anthropic

_client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from env
_MODEL  = "claude-sonnet-4-20250514"

# ── Optional: path to your COM API PDF ────────────────────────────────────────
# Set this to enable OPTION B / C above.
# e.g. PDF_PATH = Path("C:/Vissim/docs/vissim_com_manual.pdf")
PDF_PATH: Optional[Path] = Path(r"C:\Users\C10930\C_dev\mcp\llms\Vissim_COM.pdf")


# ── System prompt builder ─────────────────────────────────────────────────────

def _build_system_prompt() -> str:
    # ── OPTION A: paste your COM JSON schema here ──────────────────────────
    # Replace the empty string with your actual JSON string, e.g.:
    #   import json, pathlib
    #   SCHEMA_CONTEXT = pathlib.Path("vissim_com_schema.json").read_text()
    SCHEMA_CONTEXT = ""   # ← your COM JSON goes here

    schema_block = (
        f"\n\nCOM API Schema (use this as ground truth for object paths):\n"
        f"```json\n{SCHEMA_CONTEXT}\n```"
        if SCHEMA_CONTEXT else ""
    )

    return textwrap.dedent(f"""
        You are a PTV Vissim COM API expert.

        Given a natural language instruction, write ONE Python function called
        `vissim_action` that accepts a single argument `Vissim` — the live COM
        root object already connected via win32com.

        Rules:
        - Self-contained: use only Python stdlib inside the function.
        - `Vissim` is the entry point. Never call Vissim.LoadNet, Vissim.Exit,
          or any destructive top-level method.
        - Use 1-based indexing for all COM collections.
        - Traverse via: Vissim.Net.Nodes, Vissim.Net.SignalControllers, etc.
        - Search by name by iterating and comparing .AttValue("Name").
        - Use .AttValue("Attr") to read, .SetAttValue("Attr", val) to write.
        - Return a meaningful value (dict, list, or scalar). Never return None.
        - Raise ValueError with a clear message when an object is not found.

        Common traversal patterns:
          # Signal green time
          sc  = Vissim.Net.SignalControllers.ItemByKey(sc_id)
          sg  = sc.SGs.ItemByKey(sg_index)       # 1-based
          val = sg.AttValue("GreenTime")
          sg.SetAttValue("GreenTime", val + delta)

          # Find node by name
          for node in Vissim.Net.Nodes:
              if node.AttValue("Name") == target_name:
                  ...
        {schema_block}

        Respond with ONLY the raw Python function — no markdown, no backticks,
        no explanation, no imports outside the def block.
    """).strip()


# ── Claude call (with optional PDF attachment) ────────────────────────────────

def _call_claude(query: str) -> str:
    system = _build_system_prompt()

    # Build user content — plain text, or text + PDF document block
    user_content: list | str

    if PDF_PATH and PDF_PATH.exists():
        # OPTION B / C: attach PDF alongside the query
        pdf_b64 = base64.standard_b64encode(PDF_PATH.read_bytes()).decode()
        user_content = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_b64,
                },
                "title": "Vissim COM API Manual",
                "cache_control": {"type": "ephemeral"},   # prompt caching — saves cost on repeated calls
            },
            {"type": "text", "text": f"Vissim instruction: {query}"},
        ]
    else:
        # OPTION A: system prompt only
        user_content = f"Vissim instruction: {query}"

    response = _client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )

    code = response.content[0].text.strip()

    # Strip accidental markdown fences
    if code.startswith("```"):
        code = code.split("\n", 1)[1]
        code = code.rsplit("```", 1)[0].strip()

    return code


# ── Backend methods (added to COMBackend) ────────────────────────────────────
# These are called by the MCP tools below.
# See: com_backend_patch.py for where to paste these into COMBackend.

def _backend_generate_code(query: str) -> dict:
    """Generate a vissim_action(Vissim) function from a natural language query."""
    code = _call_claude(query)
    return {"code": code, "query": query}


def _backend_execute_code(vissim_root, code: str) -> dict:
    """Execute a previously generated vissim_action function against the live COM root."""
    namespace: dict = {}
    exec(compile(code, "<vissim_ai_generated>", "exec"), namespace)  # noqa: S102

    fn = namespace.get("vissim_action")
    if fn is None:
        raise ValueError("Code does not define a `vissim_action(Vissim)` function.")

    result = fn(vissim_root)
    return {"result": result, "code": code}


# ── MCP tool registration — follows project.py pattern exactly ───────────────

def register_ai_tools(mcp, get_backend):
    """Register AI code-generation MCP tools.

    Call this from server.py alongside the other register_*_tools() calls:

        from vissim_mcp.tools.ai_tools import register_ai_tools
        register_ai_tools(mcp, get_backend)
    """

    @mcp.tool()
    def vissim_generate_code(query: str) -> dict:
        """Generate a Python function for a Vissim COM operation from natural language.

        Uses Claude + the COM API manual to write a ready-to-run
        `vissim_action(Vissim)` function. Does NOT connect to or modify Vissim.
        Review the returned code before executing it.

        Args:
            query: Natural language description of the Vissim operation.
                   Example: "Increase green time of signal group SG_North at
                             node Main_Junction by 3 seconds"

        Returns:
            {
              "code":  "def vissim_action(Vissim): ...",
              "query": <original query>
            }
        """
        return _backend_generate_code(query)

    @mcp.tool()
    def vissim_execute_code(code: str) -> dict:
        """Execute a vissim_action(Vissim) function against the live Vissim instance.

        Pass the `code` string returned by vissim_generate_code (or any
        hand-written function matching the same signature).

        Vissim must already be connected (call vissim_connect first).

        Args:
            code: Python source defining `def vissim_action(Vissim): ...`

        Returns:
            {
              "result": <whatever vissim_action returned>,
              "code":   <the code that was executed>
            }
        """
        backend = get_backend()
        backend._ensure_connected()          # raises clearly if not connected
        return _backend_execute_code(backend._vissim, code)
