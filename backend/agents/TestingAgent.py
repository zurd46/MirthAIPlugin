import subprocess
from backend.utils import print_panel
import os
import shutil
from datetime import datetime

class TestingAgent:
    def __init__(self):
        self.current_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self.user_login = "zurd46"

    def run_tests(self, plugin_dir: str) -> dict:
        """
        Führt `mvn clean test` im angegebenen Verzeichnis aus.
        """
        # Eingabe-Validierung
        if not plugin_dir or not isinstance(plugin_dir, str):
            error_msg = "Plugin-Verzeichnis ist ungültig oder leer."
            print_panel("[TestingAgent] Eingabefehler", error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timestamp": self.current_date
            }

        # Normalisiere den Pfad für Windows
        plugin_dir = os.path.normpath(plugin_dir)
        
        # Prüfen, ob das Verzeichnis existiert
        if not os.path.exists(plugin_dir):
            error_msg = f"Plugin-Verzeichnis '{plugin_dir}' existiert nicht."
            print_panel("[TestingAgent] Verzeichnis nicht gefunden", error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timestamp": self.current_date
            }

        # Prüfen, ob pom.xml vorhanden ist
        pom_path = os.path.join(plugin_dir, "pom.xml")
        if not os.path.exists(pom_path):
            error_msg = f"Keine pom.xml im Verzeichnis '{plugin_dir}' gefunden."
            print_panel("[TestingAgent] Maven-Projekt ungültig", error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timestamp": self.current_date
            }

        # Maven ist verfügbar (bereits getestet)
        print_panel("[TestingAgent] Maven-Tests starten", f"Verzeichnis: {plugin_dir}")
        
        try:
            # WICHTIG: Für Windows explizit shell=True verwenden
            result = subprocess.run(
                ["mvn", "clean", "test", "-q"],
                cwd=plugin_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300,
                shell=True  # KORREKTUR: Für Windows notwendig
            )
            
            success = result.returncode == 0
            
            # Log-Ausgabe
            if success:
                print_panel("[TestingAgent] Tests erfolgreich", f"Returncode: {result.returncode}")
            else:
                print_panel("[TestingAgent] Tests fehlgeschlagen", f"Returncode: {result.returncode}")
                # Kurze Fehlervorschau
                error_preview = result.stderr[:500] + "..." if len(result.stderr) > 500 else result.stderr
                print_panel("[TestingAgent] Fehlervorschau", error_preview)

            return {
                "success": success,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timestamp": self.current_date,
                "maven_version": "3.9.9",
                "java_version": "23.0.1"
            }

        except subprocess.TimeoutExpired:
            error_msg = "Maven-Tests haben das Timeout von 5 Minuten überschritten."
            print_panel("[TestingAgent] Timeout", error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timeout": True,
                "timestamp": self.current_date
            }
        
        except Exception as e:
            error_msg = f"Unerwarteter Fehler beim Ausführen der Tests: {str(e)}"
            print_panel("[TestingAgent] Unerwarteter Fehler", error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timestamp": self.current_date
            }

    def run_compile_only(self, plugin_dir: str) -> dict:
        """Führt nur mvn clean compile aus"""
        try:
            result = subprocess.run(
                ["mvn", "clean", "compile", "-q"],
                cwd=os.path.normpath(plugin_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120,
                shell=True  # Für Windows
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timestamp": self.current_date,
                "operation": "compile_only"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": self.current_date
            }