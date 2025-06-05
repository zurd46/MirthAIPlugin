# backend/agents/PromptAnalyzerAgent.py

import json
import re
from langchain_openai import ChatOpenAI

class PromptAnalyzerAgent:
    """
    Analysiert einen Benutzer-Prompt und extrahiert strukturierte Metadaten
    für ein Mirth Connect Plugin. Antwortet robust gegen alle LLM-Formate.
    """

    def __init__(self, model_name: str = "gpt-4o", temperature: float = 0.0):
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)

    def analyze(self, prompt: str) -> dict:
        """
        Analysiere den Prompt, fordere Metadaten als reines JSON an und parse sie.
        Fallback auf Defaults, falls das LLM ungültige Antwort liefert.
        """
        dicom_flag = bool(re.search(r"\b(dicom|c[- ]find)\b", prompt, re.IGNORECASE))
        system_message = (
            "You are an assistant that extracts metadata for a Mirth Connect plugin "
            "from a single user prompt. Respond ONLY with a valid JSON dictionary. "
            "NO markdown, NO comments, NO explanation. Use double quotes for all keys and string values.\n\n"
            "Example output:\n"
            "{\n"
            "  \"plugin_name\": \"DicomAnalyzerPlugin\",\n"
            "  \"plugin_description\": \"erstelle ein dicom plugin\",\n"
            "  \"main_class_name\": \"DicomAnalyzerPlugin\",\n"
            "  \"package\": \"com.example\",\n"
            "  \"plugin_id\": \"dicom-analyzer-plugin\",\n"
            "  \"mirth_version\": \"4.5.2\",\n"
            "  \"plugin_type\": \"server_plugin\",\n"
            "  \"use_assembly\": true,\n"
            "  \"provided_dependencies\": [\"mirth-server-api\", \"mirth-client-core\"],\n"
            "  \"dicom_enabled\": true,\n"
            "  \"dicom_host\": \"localhost:104\",\n"
            "  \"dicom_port\": 104,\n"
            "  \"dicom_server_ae\": \"PACSSERVER\",\n"
            "  \"dicom_client_ae\": \"MIRTHCLIENT\"\n"
            "}\n\n"
            "Prompt:\n"
            f"{prompt}\n"
            "Return ONLY valid JSON as above."
        )

        resp = self.llm.invoke(system_message)
        content = str(resp.content).strip()
        content = self._strip_code_fences(content)
        try:
            meta = json.loads(content)
            if not isinstance(meta, dict):
                raise ValueError("LLM response is not a dict.")
        except Exception as e:
            print(f"[PromptAnalyzerAgent] Failed to parse LLM response: {e}")
            return self._default_metadata(prompt, dicom_flag)
        return self._ensure_all_fields(meta, prompt, dicom_flag)

    def _strip_code_fences(self, text: str) -> str:
        """
        Entfernt Markdown-Codeblöcke (```json ... ```) am Anfang/Ende.
        """
        pattern = r"^```(?:json)?\s*[\r\n]+(.*?)[\r\n]+```$"
        match = re.search(pattern, text.strip(), flags=re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()

    def _default_metadata(self, prompt: str, dicom_flag: bool) -> dict:
        """
        Fallback: Standard-Metadaten erzeugen, wenn das LLM Mist liefert.
        """
        # Intelligente Namensableitung aus Prompt
        base_name = "MyMirthPlugin"
        m = re.search(r"plugin\s+([A-Za-z0-9]+)", prompt, re.IGNORECASE)
        if m:
            base_name = m.group(1).strip().capitalize()

        # DICOM-Spezialfall
        if dicom_flag:
            plugin_name = "DicomAnalyzerPlugin"
            main_class = "DicomAnalyzerPlugin"
            plugin_id = "dicom-analyzer-plugin"
        else:
            plugin_name = base_name
            main_class = base_name
            plugin_id = base_name.lower().replace(" ", "-")

        # Defaults zusammenbauen
        result = {
            "plugin_name": plugin_name,
            "plugin_description": prompt[:50] + ("..." if len(prompt) > 50 else ""),
            "main_class_name": main_class,
            "package": "com.example",
            "plugin_id": plugin_id,
            "mirth_version": "4.5.2",
            "plugin_type": "server_plugin",
            "use_assembly": True,
            "provided_dependencies": ["mirth-server-api", "mirth-client-core"],
            "dicom_enabled": dicom_flag,
            "dicom_host": None,
            "dicom_port": None,
            "dicom_server_ae": None,
            "dicom_client_ae": None
        }

        if dicom_flag:
            # Versuche Host:Port, AE-Titles zu extrahieren
            result["dicom_host"] = self._extract_host_port(prompt) or "localhost:104"
            port_match = re.search(r":([0-9]{2,5})", result["dicom_host"])
            result["dicom_port"] = int(port_match.group(1)) if port_match else 104
            result["dicom_server_ae"] = self._extract_server_ae(prompt) or "PACSSERVER"
            result["dicom_client_ae"] = self._extract_client_ae(prompt) or "MIRTHCLIENT"

        return result

    def _ensure_all_fields(self, meta: dict, prompt: str, dicom_flag: bool) -> dict:
        """
        Sicherstellen, dass alle Felder vorhanden sind, ggf. mit Fallbacks.
        """
        defaults = self._default_metadata(prompt, dicom_flag)
        result = {}

        # Standardfelder übernehmen/ersetzen
        for key in [
            "plugin_name", "plugin_description",
            "main_class_name", "package", "plugin_id",
            "mirth_version", "plugin_type", "use_assembly", "provided_dependencies"
        ]:
            result[key] = meta.get(key) if meta.get(key) is not None else defaults[key]

        # DICOM-Felder auffüllen
        if dicom_flag or meta.get("dicom_enabled") is True:
            result["dicom_enabled"] = True
            if meta.get("dicom_host"):
                result["dicom_host"] = meta["dicom_host"]
            else:
                result["dicom_host"] = self._extract_host_port(prompt) or "localhost:104"

            if isinstance(meta.get("dicom_port"), int):
                result["dicom_port"] = meta["dicom_port"]
            else:
                pm = re.search(r":([0-9]{2,5})", result["dicom_host"])
                result["dicom_port"] = int(pm.group(1)) if pm else 104

            result["dicom_server_ae"] = (
                meta.get("dicom_server_ae") or self._extract_server_ae(prompt) or "PACSSERVER"
            )
            result["dicom_client_ae"] = (
                meta.get("dicom_client_ae") or self._extract_client_ae(prompt) or "MIRTHCLIENT"
            )
        else:
            result["dicom_enabled"] = False
            result["dicom_host"] = None
            result["dicom_port"] = None
            result["dicom_server_ae"] = None
            result["dicom_client_ae"] = None

        return result

    def _extract_host_port(self, prompt: str) -> str | None:
        m = re.search(r"([A-Za-z0-9\.-]+:[0-9]{2,5})", prompt)
        return m.group(1) if m else None

    def _extract_server_ae(self, prompt: str) -> str | None:
        m = re.search(r"(?:AE[- ]Title(?: of the server)?\s*[:=]?\s*)([A-Za-z0-9_-]+)",
                      prompt, re.IGNORECASE)
        return m.group(1) if m else None

    def _extract_client_ae(self, prompt: str) -> str | None:
        m = re.search(r"(?:AE[- ]Title(?: of the plugin)?\s*[:=]?\s*)([A-Za-z0-9_-]+)",
                      prompt, re.IGNORECASE)
        return m.group(1) if m else None