# backend/agents/CodeAgent.py

from langchain_openai import ChatOpenAI
import json
import re
from backend.utils import print_panel, print_tree
import base64
import traceback

class CodeAgent:
    def __init__(self, model_name: str = "gpt-4o", temperature: float = 0.0):
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)

    def generate_files(self, prompt: str, meta: dict) -> list:
        main_class = meta["main_class_name"]
        pkg = meta["package"]
        group_path = pkg.replace(".", "/")
        mirth_ver = meta["mirth_version"]
        plugin_type = meta["plugin_type"]
        deps = meta["provided_dependencies"]
        use_assembly = meta["use_assembly"]
        dicom_flag = meta["dicom_enabled"]

        system_message = (
            "You are a senior Java/Maven developer. Your job is to generate a complete, working Mirth Connect 4.5.2 plugin, "
            "strictly using the official Maven plugin structure:\n"
            "- All files must be under 'GENERATED_PLUGIN/'.\n"
            "- 'pom.xml' with all required dependencies (see prompt/meta),"
            " using <scope>provided</scope> for Mirth JARs from ${env.MIRTH_HOME}/server/lib/.\n"
            "- 'src/main/resources/plugin.xml' with correct metadata.\n"
            "- Main Java class in 'src/main/java/{package}/{MainClass}.java', with all logic, GUIs, and features as described in the prompt.\n"
            "- All additional classes in the correct subfolders, if needed.\n"
            "- (Optional) 'src/main/resources/icons/' for icons if the prompt requires one.\n"
            "- (Optional) 'src/test/java/{package}/' for test classes.\n"
            "- (Optional) 'README.md' with usage notes.\n"
            "DO NOT omit any features described in the user prompt! Implement everything fully."
            "Respond **only** with a JSON array (no markdown, no explanations), e.g. "
            "[{\"path\": \"GENERATED_PLUGIN/...\", \"content\": \"...\"}, ...]."
            f"\n\nUser Prompt:\n{prompt}\n"
        )

        if dicom_flag:
            system_message += (
                "Include dcm4che-core:5.23.0 and dcm4che-net:5.23.0 dependencies and a Java code example for C-FIND.\n"
            )

        # --- LLM Request ---
        print_panel("[CodeAgent] System prompt an LLM:", system_message[:350] + "..." if len(system_message) > 350 else system_message)
        try:
            resp = self.llm.invoke(system_message)
            raw = resp.content
        except Exception as exc:
            print_panel("[CodeAgent] LLM-Request faild", traceback.format_exc())
            raise RuntimeError(f"[CodeAgent] LLM-Request faild: {exc}")

        # --- Strip Markdown (falls nötig) ---
        text = self._strip_code_fences(str(raw))

        # --- Parse JSON (Dateiliste) ---
        try:
            files = json.loads(text)
            if not isinstance(files, list):
                raise ValueError(f"[CodeAgent] Expected a list of file-objects, got {type(files)}")
        except Exception as e:
            print_panel("[CodeAgent] Error parsing LLM response as JSON", str(e))
            print_panel("[CodeAgent] Raw LLM response (unprocessed)", str(raw))
            print_panel("[CodeAgent] (Stripped text)", str(text))
            raise RuntimeError("[CodeAgent] LLM response was not valid JSON with a file list.") from e

        print_panel("[CodeAgent] Number of files received from LLM", str(len(files)))
        print_tree(files)

        # --- Decode Base64 (z.B. PNG oder ZIP) ---
        for file in files:
            p_lower = file["path"].lower()
            if p_lower.endswith(".png") or p_lower.endswith(".zip"):
                try:
                    decoded = base64.b64decode(file["content"])
                    file["content_binary"] = decoded
                    print_panel(f"[CodeAgent] Binary file decoded: {file['path']}", f"{len(decoded)} Bytes")
                except Exception as e:
                    print_panel(f"[CodeAgent] Fehler beim Base64-Decode für {file['path']}", str(e))
                    file["content_binary"] = None
            else:
                file["content_binary"] = None

        return files

    def _strip_code_fences(self, text: str) -> str:
        """
        Entfernt Markdown-Codeblöcke (```json ... ``` oder ``` ... ```)
        """
        pattern = r"^```(?:json)?\s*[\r\n]+(.*?)[\r\n]+```$"
        match = re.search(pattern, text.strip(), flags=re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()