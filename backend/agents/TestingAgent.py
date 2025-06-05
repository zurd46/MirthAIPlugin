import subprocess
import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.traceback import install
install(show_locals=True)
console = Console()

def log_panel(title, content, style="cyan"):
    console.print(Panel(content, title=title, style=style))

def _extract_first_error(logtext):
    """Extrahiere die erste relevante Fehlermeldung aus Maven-Log."""
    for line in logtext.splitlines():
        if "[ERROR]" in line and "COMPILATION ERROR" not in line:
            return line.strip()
    return ""

class TestingAgent:
    def __init__(self):
        self.current_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self.user_login = "zurd46"

    def run_maven(self, plugin_dir, maven_args, timeout=300, operation_name="test"):
        shell_flag = os.name == "nt"
        try:
            result = subprocess.run(
                ["mvn"] + maven_args,
                cwd=plugin_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                shell=shell_flag
            )
            success = result.returncode == 0
            log_panel(f"[TestingAgent] Maven {operation_name} " + ("erfolgreich" if success else "fehlgeschlagen"),
                      f"Returncode: {result.returncode}", style="green" if success else "red")
            preview = (result.stdout + result.stderr)[:1000]  # kombiniere für Übersicht
            if not success:
                log_panel("[TestingAgent] Fehlervorschau", preview, style="yellow")
            return {
                "success": success,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "first_error": _extract_first_error(result.stdout + "\n" + result.stderr),
                "timestamp": self.current_date,
                "operation": operation_name,
                "test_report_dir": os.path.join(plugin_dir, "target", "surefire-reports")
            }
        except subprocess.TimeoutExpired:
            error_msg = f"Maven-{operation_name} hat das Timeout überschritten."
            log_panel("[TestingAgent] Timeout", error_msg, style="red")
            return {
                "success": False,
                "error": error_msg,
                "timeout": True,
                "timestamp": self.current_date,
                "operation": operation_name
            }
        except Exception as e:
            error_msg = f"Unerwarteter Fehler bei Maven-{operation_name}: {str(e)}"
            log_panel("[TestingAgent] Unerwarteter Fehler", error_msg, style="red")
            return {
                "success": False,
                "error": error_msg,
                "timestamp": self.current_date,
                "operation": operation_name
            }

    def run_tests(self, plugin_dir: str) -> dict:
        """
        Führt `mvn clean test` im angegebenen Verzeichnis aus.
        """
        if not plugin_dir or not isinstance(plugin_dir, str):
            error_msg = "Plugin-Verzeichnis ist ungültig oder leer."
            log_panel("[TestingAgent] Eingabefehler", error_msg, style="red")
            return {"success": False, "error": error_msg, "timestamp": self.current_date}
        plugin_dir = os.path.normpath(plugin_dir)
        if not os.path.exists(plugin_dir):
            error_msg = f"Plugin-Verzeichnis '{plugin_dir}' existiert nicht."
            log_panel("[TestingAgent] Verzeichnis nicht gefunden", error_msg, style="red")
            return {"success": False, "error": error_msg, "timestamp": self.current_date}
        pom_path = os.path.join(plugin_dir, "pom.xml")
        if not os.path.exists(pom_path):
            error_msg = f"Keine pom.xml im Verzeichnis '{plugin_dir}' gefunden."
            log_panel("[TestingAgent] Maven-Projekt ungültig", error_msg, style="red")
            return {"success": False, "error": error_msg, "timestamp": self.current_date}

        log_panel("[TestingAgent] Maven-Tests starten", f"Verzeichnis: {plugin_dir}", style="magenta")
        return self.run_maven(plugin_dir, ["clean", "test", "-q"], timeout=300, operation_name="test")

    def run_compile_only(self, plugin_dir: str) -> dict:
        """
        Führt nur 'mvn clean compile' im angegebenen Verzeichnis aus.
        """
        if not plugin_dir or not isinstance(plugin_dir, str):
            log_panel("[TestingAgent] Eingabefehler", "Plugin-Verzeichnis ist ungültig oder leer.", style="red")
            return {"success": False, "error": "Plugin-Verzeichnis ist ungültig oder leer.", "timestamp": self.current_date}
        plugin_dir = os.path.normpath(plugin_dir)
        if not os.path.exists(plugin_dir):
            log_panel("[TestingAgent] Verzeichnis nicht gefunden", f"Plugin-Verzeichnis '{plugin_dir}' existiert nicht.", style="red")
            return {"success": False, "error": f"Plugin-Verzeichnis '{plugin_dir}' existiert nicht.", "timestamp": self.current_date}
        pom_path = os.path.join(plugin_dir, "pom.xml")
        if not os.path.exists(pom_path):
            log_panel("[TestingAgent] Maven-Projekt ungültig", f"Keine pom.xml im Verzeichnis '{plugin_dir}' gefunden.", style="red")
            return {"success": False, "error": f"Keine pom.xml im Verzeichnis '{plugin_dir}' gefunden.", "timestamp": self.current_date}

        log_panel("[TestingAgent] Maven-Compile startet", f"Verzeichnis: {plugin_dir}", style="magenta")
        return self.run_maven(plugin_dir, ["clean", "compile", "-q"], timeout=120, operation_name="compile")