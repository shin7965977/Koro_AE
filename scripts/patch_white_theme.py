"""Inject clean white theme CSS into Elementary HTML report."""

from pathlib import Path

report_path = Path("docs/elementary_report.html")

custom_css = """
/* ======================================================== */
/* Elementary Clean Light Mode (Pure White Canvas Overrides) */
/* ======================================================== */
body, html, #root {
  background-color: #ffffff !important;
  background: #ffffff !important;
}

.react-flow,
.react-flow__pane,
.react-flow__container,
.react-flow__renderer,
.react-flow__viewport,
div[data-testid="rf__wrapper"],
.react-flow__background,
svg.react-flow__background {
  background-color: #ffffff !important;
  background: #ffffff !important;
}

svg.react-flow__background circle {
  fill: #cbd5e1 !important;
}

.react-flow__edge-path,
.react-flow__connection-path {
  stroke: #64748b !important;
  stroke-width: 1.8px !important;
}

.react-flow__edge:hover .react-flow__edge-path,
.react-flow__edge.selected .react-flow__edge-path {
  stroke: #e11d48 !important;
  stroke-width: 2.5px !important;
}

.react-flow__controls {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
}

.react-flow__controls-button {
  background: #ffffff !important;
  border-bottom: 1px solid #f1f5f9 !important;
}

.react-flow__controls-button:hover {
  background: #f8fafc !important;
}

.react-flow__controls-button svg {
  fill: #334155 !important;
}

[class*="MuiDrawer-paper"],
[class*="MuiTreeView-root"],
div[role="tree"] {
  background-color: #ffffff !important;
}
"""

def patch_white_theme():
    html = report_path.read_text(encoding="utf-8")
    if "/* Elementary Clean Light Mode (Pure White Canvas Overrides) */" in html:
        print("Already patched!")
        return
    idx = html.find("</style>")
    if idx == -1:
        raise ValueError("Could not find </style> in elementary_report.html")
    new_html = html[:idx] + custom_css + html[idx:]
    report_path.write_text(new_html, encoding="utf-8")
    print("✅ Successfully injected pure white theme into docs/elementary_report.html")

if __name__ == "__main__":
    patch_white_theme()
