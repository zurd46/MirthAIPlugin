from langchain_openai import ChatOpenAI
import json
import re
import base64
import traceback
import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.traceback import install
install(show_locals=True)
console = Console()

FORBIDDEN_PATTERNS = [
    "import org.dcm4che3.net.service.ServiceClassProvider",
    "import org.dcm4che3.net.service.FindSCU",
    "import org.dcm4che3.net.service.FindSCP",
    "import org.dcm4che3.net.Association",
    "import org.dcm4che3.net.PDVInputStream",
    "import org.dcm4che3.net.Dimse",
    "import org.dcm4che3.net.PresentationContext",
    "ServiceClassProvider",
    "FindSCU",
    "FindSCP",
    "Association",
    "PDVInputStream",
    "Dimse",
    "PresentationContext",
    "Commands"
]

def log_panel(title, content, style="cyan"):
    console.print(Panel(content, title=title, style=style))

def log_tree(files, title="[CodeAgent] File Tree"):
    tree = Tree(title)
    for file in files:
        tree.add(file['path'])
    console.print(tree)

def clean_forbidden_code(content):
    lines = content.splitlines()
    cleaned_lines = []
    for line in lines:
        if not any(pattern in line for pattern in FORBIDDEN_PATTERNS):
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

def valid_java_class(content):
    # Prüft auf echten Klassenkopf, öffnende und schließende Klammern (mind. einmal) und mehr als nur "class X {}"
    m = re.search(r'public\s+class\s+(\w+)', content)
    if not m:
        return False
    class_name = m.group(1)
    if content.count("{") == 0 or content.count("}") == 0:
        return False
    # Nach Entfernen von Kommentaren und Leerzeichen muss mehr als nur "classX{}" übrig sein
    code_only = re.sub(r"//.*|/\*.*?\*/", "", content, flags=re.DOTALL)
    code_only = re.sub(r"\s+", "", code_only)
    minimal = f"publicclass{class_name}{{}}"
    return code_only != minimal and code_only.startswith(f"publicclass{class_name}")

def extract_package_and_class(original):
    pkg_match = re.search(r'package\s+([\w\.]+);', original)
    package_decl = f"package {pkg_match.group(1)};\n\n" if pkg_match else ""
    class_match = re.search(r'public\s+class\s+(\w+)', original)
    class_name = class_match.group(1) if class_match else "Plugin"
    return package_decl, class_name

def validate_and_autocorrect_files(files, is_dicom=False):
    """
    Entfernt nur bei DICOM alle Zeilen mit verbotenen dcm4che-Klassen/Imports aus Java-Dateien.
    Ersetzt kaputte Dateien nur bei DICOM durch eine gültige Stub-Klasse.
    Für Nicht-DICOM-Plugins bleibt alles wie generiert!
    """
    for file in files:
        path = file.get("path", "")
        if path.endswith(".java") and is_dicom:
            original = file.get("content", "")
            cleaned = clean_forbidden_code(original)
            if not valid_java_class(cleaned):
                package_decl, class_name = extract_package_and_class(original)
                cleaned = f"""{package_decl}public class {class_name} {{
    // TODO: Not possible with real dcm4che API
}}"""
            file["content"] = cleaned
    return files

class CodeAgent:
    def __init__(self, model_name: str = "gpt-4o", temperature: float = 0.0):
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)
        self.current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.user_login = "zurd46"

    def generate_files(self, prompt: str, meta: dict) -> list:
        main_class = meta.get("main_class_name", "MyPlugin")
        pkg = meta.get("package", "com.example.plugin")
        mirth_ver = meta.get("mirth_version", "4.5.2")
        dicom_flag = meta.get("dicom_enabled", False)

        system_message = self._create_system_prompt(prompt, meta, dicom_flag)

        log_panel("[CodeAgent] Sending request to LLM", f"Model: {self.llm.model_name}, Temperature: {self.llm.temperature}")
        try:
            resp = self.llm.invoke(system_message)
            raw_response = resp.content

            # Typabsicherung für _process_llm_response
            if isinstance(raw_response, str):
                response_str = raw_response
            elif isinstance(raw_response, list):
                response_str = "\n".join(
                    s if isinstance(s, str) else json.dumps(s)
                    for s in raw_response
                )
            else:
                response_str = str(raw_response)

            log_panel("[CodeAgent] Raw LLM response received", f"Length: {len(response_str)} characters")
        except Exception as exc:
            error_msg = f"[CodeAgent] LLM-Request failed: {exc}"
            log_panel("[CodeAgent] LLM-Request Error", traceback.format_exc(), style="red")
            raise RuntimeError(error_msg)

        try:
            files = self._process_llm_response(response_str)
            files = validate_and_autocorrect_files(files, dicom_flag)
            log_panel("[CodeAgent] Files successfully generated", f"Count: {len(files)}")
            log_tree(files)
            return files
        except Exception as e:
            error_msg = f"[CodeAgent] Failed to process LLM response: {e}"
            log_panel("[CodeAgent] Processing Error", str(e), style="red")
            raise RuntimeError(error_msg)

    def _create_system_prompt(self, prompt: str, meta: dict, dicom_flag: bool) -> str:
        base_prompt = f"""You are a senior Java/Maven developer specializing in Mirth Connect plugins.

CRITICAL INSTRUCTIONS:
1. Use the EXACT project structure, conventions, naming, and best practices found in this public GitHub repository:
   https://github.com/kpalang/mirth-sample-plugin
2. Your generated code and all files MUST be fully compatible with the layout, build setup, pom.xml, plugin.xml, and Java code style from this repository.
3. All generated code must be complete: do not leave out any files or boilerplate required by the standard plugin structure.
4. Respond with ONLY a valid JSON array — NO markdown, NO comments, NO explanations, NO other text.
5. The JSON array must contain file objects with "path" and "content" properties.

PLUGIN STRUCTURE REQUIREMENTS:
- All files must be under the 'GENERATED_PLUGIN/' prefix.
- Use the exact Maven directory structure, file locations, and content as in the reference repository.
- pom.xml and plugin.xml must match the style, fields, and metadata from kpalang/mirth-sample-plugin.
- Main Java class must be in the same package structure and style as in the reference repository.
- Implement ALL features described in the user prompt with meaningful, working code.
- Use proper Java naming conventions and best practices as seen in the reference repository.

METADATA:
- Main Class: {meta.get('main_class_name', 'MyPlugin')}
- Package: {meta.get('package', 'com.example.plugin')}
- Plugin Type: {meta.get('plugin_type', 'SERVER_PLUGIN')}
- Mirth Version: {meta.get('mirth_version', '4.5.2')}
- Author: {self.user_login}
- Generated: {self.current_date}

USER REQUEST:
{prompt}
"""

        if dicom_flag:
            base_prompt += """
DICOM REQUIREMENTS:
- Use dcm4che-core:5.23.0 and dcm4che-net:5.23.0 dependencies in pom.xml.
- The pom.xml MUST contain the following <repositories> section for dcm4che:
<repositories>
  <repository>
    <id>dcm4che</id>
    <url>https://www.dcm4che.org/maven2/</url>
  </repository>
</repositories>
- Implement functional DICOM C-FIND operations only using classes/methods/constants that exist in dcm4che 5.23.0.
- Use UID strings directly if no Java constants exist (e.g. "1.2.840.10008.5.1.4.1.2.2.1" for Study Root FIND).
- For DICOM tags, use Tag.<NAME> from org.dcm4che3.data.Tag where possible.
- For VR, use VR.<NAME> from org.dcm4che3.data.VR (e.g., VR.CS, VR.PN, etc).
- NEVER invent classes, constants, or methods! If unsure, add a TODO comment for the user.
- Add proper DICOM connection handling and error management.
- Include meaningful DICOM query and response processing.
"""

        base_prompt += """

STRICT VALIDITY POLICY:
- The generated code MUST compile and run without errors.
- The pom.xml MUST be valid and contain all necessary dependencies.
- You MUST use ONLY existing classes, methods, constants, and APIs from the official documentation of all referenced libraries.
- For DICOM: ONLY use classes, enums, constants and methods available in dcm4che version 5.23.0 (https://www.dcm4che.org/).
- DO NOT invent, assume or guess classes (e.g. 'ServiceClassProvider', 'FindSCU', 'FindSCP', 'Association', 'PresentationContext', 'Dimse', 'PDVInputStream', etc.), methods or constants.
- For DICOM UIDs, if there is no Java constant in dcm4che, use the UID string directly (e.g. "1.2.840.10008.5.1.4.1.2.2.1").
- For DICOM tags, use org.dcm4che3.data.Tag constants.
- For VRs, use org.dcm4che3.data.VR constants (e.g. VR.CS, VR.PN).
- If you are unsure or if something does NOT exist, DO NOT invent code – instead, place a clear // TODO comment for the user at the relevant location.
- DO NOT reference, import, or use any Mirth Connect dependency or Java class or interface (such as com.mirth.connect.plugins:server-api), unless it is explicitly provided AND available on Maven Central.
- The pom.xml MUST NOT contain dependencies that are not available on Maven Central or the provided repository URLs.
- If the user prompt is technically impossible with public APIs, generate a minimal stub and document the limitation in a clear comment.

RESPONSE FORMAT:
- Respond with ONLY a valid JSON array as described above, and nothing else.
"""
        return base_prompt

    def _process_llm_response(self, raw_response: str) -> list:
        preview = raw_response[:500] + "..." if len(raw_response) > 500 else raw_response
        log_panel("[CodeAgent] LLM Response Preview", preview, style="yellow")
        cleaned_text = self._strip_code_fences(raw_response)
        json_text = self._extract_json_array(cleaned_text)
        try:
            files = json.loads(json_text)
            if not isinstance(files, list):
                raise ValueError(f"Expected list, got {type(files)}")
            for i, file in enumerate(files):
                if not isinstance(file, dict):
                    raise ValueError(f"File {i} is not a dict: {type(file)}")
                if "path" not in file:
                    raise ValueError(f"File {i} missing 'path' field")
                if "content" not in file:
                    raise ValueError(f"File {i} missing 'content' field")
                content = str(file["content"])
                if "FromToFromTo" in content and content.count("FromTo") > 5:
                    raise ValueError(f"File {i} contains repetitive/nonsensical content")
        except json.JSONDecodeError as e:
            log_panel("[CodeAgent] JSON Parse Error", f"Error: {e}", style="red")
            log_panel("[CodeAgent] Problematic JSON Text", json_text[:1000] + "..." if len(json_text) > 1000 else json_text, style="red")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            log_panel("[CodeAgent] File Validation Error", str(e), style="red")
            raise ValueError(f"Invalid file structure: {e}")
        self._process_binary_files(files)
        return files

    def _strip_code_fences(self, text: str) -> str:
        text = text.strip()
        pattern = r"^```(?:json)?\s*\n(.*?)\n```$"
        match = re.search(pattern, text, flags=re.DOTALL)
        if match:
            return match.group(1).strip()
        return text

    def _extract_json_array(self, text: str) -> str:
        text = text.strip()
        start_idx = text.find('[')
        if start_idx == -1:
            return text
        bracket_count = 0
        in_string = False
        escape_next = False
        for i in range(start_idx, len(text)):
            char = text[i]
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if not in_string:
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        return text[start_idx:i+1]
        return text[start_idx:]

    def _process_binary_files(self, files: list) -> None:
        binary_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.zip', '.jar', '.ico']
        for file in files:
            path_lower = file["path"].lower()
            is_binary = any(path_lower.endswith(ext) for ext in binary_extensions)
            if is_binary:
                try:
                    content = file["content"]
                    if isinstance(content, str):
                        content = re.sub(r'\s+', '', content)
                        decoded = base64.b64decode(content)
                        file["content_binary"] = decoded
                        log_panel(f"[CodeAgent] Binary file decoded", f"{file['path']} ({len(decoded)} bytes)", style="green")
                    else:
                        file["content_binary"] = None
                        log_panel(f"[CodeAgent] Binary file error", f"{file['path']} - content is not string", style="red")
                except Exception as e:
                    file["content_binary"] = None
                    log_panel(f"[CodeAgent] Base64 decode error", f"{file['path']}: {e}", style="red")
            else:
                file["content_binary"] = None

    # Die restlichen Methoden wie validate_generated_files, auto_correct_files etc. brauchst du nicht mehr explizit,
    # weil alles mit validate_and_autocorrect_files() in generate_files gelöst ist!