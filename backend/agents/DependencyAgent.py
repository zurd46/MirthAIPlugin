import os
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.traceback import install
install(show_locals=True)
console = Console()

def log_panel(title, content, style="cyan"):
    console.print(Panel(content, title=title, style=style))

class DependencyAgent:
    def __init__(self, mirth_home=None):
        self.mirth_home = mirth_home or os.getenv("MIRTH_HOME")

    def check_and_install_mirth_server_api(self, version="4.5.2"):
        """
        Prüft, ob server-api im lokalen Maven-Repo vorhanden ist, oder installiert es aus MIRTH_HOME/server-lib.
        Gibt (success: bool, message: str) zurück. Loggt alle Schritte als Rich-Panel.
        """
        # 1. Suche im lokalen Maven-Repository
        m2_path = os.path.expanduser(
            f"~/.m2/repository/com/mirth/connect/plugins/server-api/{version}/server-api-{version}.jar"
        )
        if os.path.exists(m2_path):
            log_panel("[DependencyAgent] Prüfung", "server-api bereits im lokalen Maven-Repository vorhanden.", style="green")
            return True, "server-api already installed in local Maven repo."

        # 2. Suche in MIRTH_HOME/server-lib
        if self.mirth_home:
            jar_path = os.path.join(self.mirth_home, "server-lib", f"server-api-{version}.jar")
            if os.path.exists(jar_path):
                cmd = [
                    "mvn", "install:install-file",
                    "-DgroupId=com.mirth.connect.plugins",
                    "-DartifactId=server-api",
                    f"-Dversion={version}",
                    "-Dpackaging=jar",
                    f"-Dfile={jar_path}"
                ]
                log_panel("[DependencyAgent] Installation", f"Installiere {jar_path} ins Maven-Repository...", style="magenta")
                try:
                    subprocess.run(cmd, check=True)
                    log_panel("[DependencyAgent] Erfolg", "server-api JAR erfolgreich installiert.", style="green")
                    return True, "server-api JAR installed from MIRTH_HOME."
                except Exception as e:
                    log_panel("[DependencyAgent] Fehler", f"Fehler beim Installieren: {e}", style="red")
                    return False, f"Fehler beim Installieren: {e}"

        # 3. Nicht gefunden – Hinweis zum Download & Installation
        msg = (
            "server-api JAR nicht gefunden.\n"
            "Bitte lade es aus deiner Mirth Connect Installation (z.B. von MIRTH_HOME/server-lib/) "
            f"und installiere es manuell mit:\n\n"
            f"mvn install:install-file -DgroupId=com.mirth.connect.plugins -DartifactId=server-api "
            f"-Dversion={version} -Dpackaging=jar -Dfile=/pfad/zu/server-api-{version}.jar\n"
            "\n"
            "Falls du das JAR nicht findest, prüfe, ob Mirth Connect korrekt installiert ist. "
            "Gegebenenfalls musst du es beim Hersteller/Distributor anfordern."
        )
        log_panel("[DependencyAgent] Nicht gefunden", msg, style="red")
        return False, msg