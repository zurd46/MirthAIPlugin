import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from backend.agents.PromptAnalyzerAgent import PromptAnalyzerAgent
from backend.agents.CodeAgent import CodeAgent
from backend.utils import save_file

# --- Rich Logging ---
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.table import Table
from rich.traceback import install
install(show_locals=True)
console = Console()

def log_panel(title, content, style="cyan"):
    console.print(Panel(content, title=title, style=style))

def log_tree(files):
    tree = Tree("📦 [bold]GENERATED_PLUGIN[/bold]")
    for file in files:
        rel = file.get("path", "")
        size = file.get("content_binary")
        if size is not None:
            size_bytes = len(size)
        else:
            size_bytes = len(file.get("content", "").encode("utf-8"))
        tree.add(f"[green]{rel}[/green]  [dim]{size_bytes} bytes[/dim]")
    console.print(tree)

def log_steps(steps):
    table = Table(title="Ablaufschritte", show_header=True, header_style="bold magenta")
    table.add_column("Nr.", style="dim")
    table.add_column("Beschreibung")
    for i, step in enumerate(steps, 1):
        table.add_row(str(i), step)
    console.print(table)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class PluginRequest(BaseModel):
    prompt: str

@app.post("/generate")
async def generate_plugin(req: PluginRequest):
    prompt_text = req.prompt
    steps = []
    steps.append("1) Prompt empfangen")

    # --- Log Prompt ---
    log_panel("Prompt erhalten", prompt_text, style="yellow")

    # 1) Metadaten extrahieren
    try:
        analyzer = PromptAnalyzerAgent()
        meta = analyzer.analyze(prompt_text)
        log_panel("Extrahierte Metadaten", str(meta), style="green")
        steps.append("2) Metadaten extrahiert")
    except Exception as e:
        log_panel("Fehler bei der Metadaten-Extraktion", str(e), style="red")
        return JSONResponse({"error": f"Fehler beim Metadaten-Parsing: {e}"}, status_code=500)

    # 2) Files generieren
    try:
        code_agent = CodeAgent()
        files = code_agent.generate_files(prompt_text, meta)
        steps.append(f"3) {len(files)} Dateien generiert")
        log_panel("Dateien generiert", f"{len(files)} Dateien erstellt.", style="blue")
        log_tree(files)
    except Exception as e:
        log_panel("Fehler bei der Dateigenerierung", str(e), style="red")
        return JSONResponse({"error": f"Fehler bei der Dateigenerierung: {e}"}, status_code=500)

    # 3) Dateien speichern
    for file in files:
        orig_path = file.get("path", "")
        path = os.path.normpath(orig_path)
        directory = os.path.dirname(path)
        try:
            if file.get("content_binary") is not None:
                content_bytes = file["content_binary"]
                if directory and not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                with open(path, "wb") as f:
                    f.write(content_bytes)
            else:
                if directory and not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                save_file(path, file.get("content", ""))
            log_panel("Datei gespeichert", f"{path} ({os.path.getsize(path)} bytes)", style="white")
        except Exception as e:
            log_panel("Fehler beim Schreiben", f"{path}\n{e}", style="bold red")
            return JSONResponse({"error": f"Fehler beim Schreiben von {path}: {e}"}, status_code=500)

    steps.append("4) Dateien auf Festplatte gespeichert")
    log_steps(steps)

    return JSONResponse({
        "msg": "Plugin files generated and saved successfully.",
        "steps": steps,
        "files": [
            {
                "path": f["path"],
                "size_bytes": len(f["content_binary"]) if f.get("content_binary") is not None
                              else len(f.get("content", "").encode("utf-8"))
            }
            for f in files
        ]
    })
