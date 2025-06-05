# backend/agents/CodeAgent.py

from langchain_openai import ChatOpenAI
import json
import re
from backend.utils import print_panel, print_tree
import base64
import traceback
import os
from datetime import datetime

class CodeAgent:
    def __init__(self, model_name: str = "gpt-4o", temperature: float = 0.0):
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)
        # Korrigiertes aktuelles Datum
        self.current_date = "2025-01-14 10:35:03"  # Realistisches aktuelles Datum
        self.user_login = "zurd46"

    def generate_files(self, prompt: str, meta: dict) -> list:
        """
        Generiert Dateien für ein Mirth Connect Plugin basierend auf dem Prompt und Metadaten.
        """
        # Metadaten extrahieren mit Fallbacks
        main_class = meta.get("main_class_name", "MyPlugin")
        pkg = meta.get("package", "com.example.plugin")
        group_path = pkg.replace(".", "/")
        mirth_ver = meta.get("mirth_version", "4.5.2")
        plugin_type = meta.get("plugin_type", "SERVER_PLUGIN")
        deps = meta.get("provided_dependencies", [])
        use_assembly = meta.get("use_assembly", False)
        dicom_flag = meta.get("dicom_enabled", False)

        # System-Prompt erstellen
        system_message = self._create_system_prompt(prompt, meta, dicom_flag)

        # LLM-Request durchführen
        print_panel("[CodeAgent] Sending request to LLM", f"Model: {self.llm.model_name}, Temperature: {self.llm.temperature}")
        
        try:
            resp = self.llm.invoke(system_message)
            raw_response = resp.content
            print_panel("[CodeAgent] Raw LLM response received", f"Length: {len(raw_response)} characters")
        except Exception as exc:
            error_msg = f"[CodeAgent] LLM-Request failed: {exc}"
            print_panel("[CodeAgent] LLM-Request Error", traceback.format_exc())
            raise RuntimeError(error_msg)

        # Response verarbeiten
        try:
            files = self._process_llm_response(raw_response)
            print_panel("[CodeAgent] Files successfully generated", f"Count: {len(files)}")
            print_tree(files)
            return files
        except Exception as e:
            error_msg = f"[CodeAgent] Failed to process LLM response: {e}"
            print_panel("[CodeAgent] Processing Error", str(e))
            raise RuntimeError(error_msg)

    def _create_system_prompt(self, prompt: str, meta: dict, dicom_flag: bool) -> str:
        """
        Erstellt den System-Prompt für die LLM-Anfrage.
        """
        base_prompt = f"""You are a senior Java/Maven developer specializing in Mirth Connect 4.5.2 plugins.

CRITICAL INSTRUCTIONS:
1. You MUST respond with ONLY a valid JSON array - NO markdown, NO comments, NO explanations, NO other text
2. If you don't follow this format exactly, your response will be rejected
3. The JSON array must contain file objects with "path" and "content" properties
4. Do NOT generate repetitive or nonsensical method names like "FromToFromTo"
5. Generate meaningful, functional code that implements the requested features

PLUGIN STRUCTURE REQUIREMENTS:
- All files under 'GENERATED_PLUGIN/' prefix
- Standard Maven directory structure
- pom.xml with proper Mirth Connect dependencies using <scope>provided</scope>
- plugin.xml in src/main/resources/ with correct metadata
- Main Java class in correct package structure
- Implement ALL features described in the user prompt with meaningful code
- Use proper Java naming conventions and best practices

RESPONSE FORMAT (EXAMPLE):
[
  {{"path": "GENERATED_PLUGIN/pom.xml", "content": "<?xml version=\\"1.0\\" encoding=\\"UTF-8\\"?>\\n<project xmlns=\\"http://maven.apache.org/POM/4.0.0\\">..."}},
  {{"path": "GENERATED_PLUGIN/src/main/resources/plugin.xml", "content": "<?xml version=\\"1.0\\" encoding=\\"UTF-8\\"?>\\n<pluginMetaData>..."}},
  {{"path": "GENERATED_PLUGIN/src/main/java/{meta.get('package', 'com.example.plugin').replace('.', '/')}/{meta.get('main_class_name', 'MyPlugin')}.java", "content": "package {meta.get('package', 'com.example.plugin')};\\n\\nimport com.mirth.connect.plugins.ServerPlugin;\\n..."}}
]

METADATA:
- Main Class: {meta.get('main_class_name', 'MyPlugin')}
- Package: {meta.get('package', 'com.example.plugin')}
- Plugin Type: {meta.get('plugin_type', 'SERVER_PLUGIN')}
- Mirth Version: {meta.get('mirth_version', '4.5.2')}
- Author: {self.user_login}
- Generated: {self.current_date}

USER REQUEST:
{prompt}"""

        if dicom_flag:
            base_prompt += """

DICOM REQUIREMENTS:
- Include dcm4che-core:5.23.0 and dcm4che-net:5.23.0 dependencies in pom.xml
- Implement functional DICOM C-FIND operations
- Add proper DICOM connection handling and error management
- Include meaningful DICOM query and response processing"""

        base_prompt += """

FINAL REMINDER:
- Generate ONLY functional, meaningful code
- NO repetitive method names or placeholder content
- Each method must have a clear purpose and implementation
- RESPOND WITH ONLY THE JSON ARRAY - NO OTHER TEXT OR FORMATTING!"""

        return base_prompt

    def _process_llm_response(self, raw_response: str) -> list:
        """
        Verarbeitet die LLM-Response und extrahiert die Dateiliste.
        """
        # Debug: Zeige ersten Teil der Antwort
        preview = raw_response[:500] + "..." if len(raw_response) > 500 else raw_response
        print_panel("[CodeAgent] LLM Response Preview", preview)
        
        # 1. Markdown-Codeblöcke entfernen
        cleaned_text = self._strip_code_fences(raw_response)
        
        # 2. JSON-Array extrahieren
        json_text = self._extract_json_array(cleaned_text)
        
        # 3. JSON parsen
        try:
            files = json.loads(json_text)
            if not isinstance(files, list):
                raise ValueError(f"Expected list, got {type(files)}")
            
            # Validierung der Dateistruktur
            for i, file in enumerate(files):
                if not isinstance(file, dict):
                    raise ValueError(f"File {i} is not a dict: {type(file)}")
                if "path" not in file:
                    raise ValueError(f"File {i} missing 'path' field")
                if "content" not in file:
                    raise ValueError(f"File {i} missing 'content' field")
                
                # Prüfe auf sinnlose Inhalte
                content = str(file["content"])
                if "FromToFromTo" in content and content.count("FromTo") > 5:
                    raise ValueError(f"File {i} contains repetitive/nonsensical content")
                    
        except json.JSONDecodeError as e:
            print_panel("[CodeAgent] JSON Parse Error", f"Error: {e}")
            print_panel("[CodeAgent] Problematic JSON Text", json_text[:1000] + "..." if len(json_text) > 1000 else json_text)
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            print_panel("[CodeAgent] File Validation Error", str(e))
            raise ValueError(f"Invalid file structure: {e}")

        # 4. Binärdateien verarbeiten
        self._process_binary_files(files)
        
        return files

    def _strip_code_fences(self, text: str) -> str:
        """
        Entfernt Markdown-Codeblöcke (```json ... ``` oder ``` ... ```)
        """
        text = text.strip()
        
        # Pattern für verschiedene Codeblock-Formate
        patterns = [
            r"^```(?:json)?\s*\n(.*?)\n```$",  # ```json ... ```
            r"^```\s*\n(.*?)\n```$",           # ``` ... ```
            r"^`([^`]*)`$",                    # `...`
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.DOTALL)
            if match:
                return match.group(1).strip()
                
        return text

    def _extract_json_array(self, text: str) -> str:
        """
        Extrahiert das erste JSON-Array aus dem Text.
        """
        # Entferne potentielle Einleitungstexte
        text = text.strip()
        
        # Finde den Start des JSON-Arrays
        start_idx = text.find('[')
        if start_idx == -1:
            return text
            
        # Finde das Ende des JSON-Arrays durch Bracket-Matching
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
        
        # Fallback: vom ersten [ bis zum Ende
        return text[start_idx:]

    def _looks_like_json(self, text: str) -> bool:
        """
        Prüft, ob ein Text wie JSON aussieht (einfache Heuristik).
        """
        text = text.strip()
        return (text.startswith('[') and text.endswith(']') and 
                '"path"' in text and '"content"' in text)

    def _process_binary_files(self, files: list) -> None:
        """
        Verarbeitet Binärdateien (PNG, ZIP, etc.) und decodiert Base64.
        """
        binary_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.zip', '.jar', '.ico']
        
        for file in files:
            path_lower = file["path"].lower()
            
            # Prüfe, ob es eine Binärdatei ist
            is_binary = any(path_lower.endswith(ext) for ext in binary_extensions)
            
            if is_binary:
                try:
                    # Versuche Base64-Dekodierung
                    content = file["content"]
                    if isinstance(content, str):
                        # Entferne mögliche Whitespaces/Newlines
                        content = re.sub(r'\s+', '', content)
                        decoded = base64.b64decode(content)
                        file["content_binary"] = decoded
                        print_panel(f"[CodeAgent] Binary file decoded", f"{file['path']} ({len(decoded)} bytes)")
                    else:
                        file["content_binary"] = None
                        print_panel(f"[CodeAgent] Binary file error", f"{file['path']} - content is not string")
                except Exception as e:
                    file["content_binary"] = None
                    print_panel(f"[CodeAgent] Base64 decode error", f"{file['path']}: {e}")
            else:
                file["content_binary"] = None

    def validate_generated_files(self, files: list) -> dict:
        """
        Validiert die generierten Dateien auf Vollständigkeit und Qualität.
        """
        required_files = [
            "GENERATED_PLUGIN/pom.xml",
            "GENERATED_PLUGIN/src/main/resources/plugin.xml"
        ]
        
        found_files = [f["path"] for f in files]
        missing_files = [req for req in required_files if req not in found_files]
        
        has_java_files = any(f["path"].endswith(".java") for f in files)
        
        # Prüfe auf Qualitätsprobleme
        quality_issues = []
        for file in files:
            content = str(file.get("content", ""))
            if "FromToFromTo" in content and content.count("FromTo") > 5:
                quality_issues.append(f"Repetitive content in {file['path']}")
            if len(content.strip()) < 50 and file["path"].endswith(".java"):
                quality_issues.append(f"Suspiciously short Java file: {file['path']}")
        
        return {
            "valid": len(missing_files) == 0 and has_java_files and len(quality_issues) == 0,
            "missing_files": missing_files,
            "has_java_files": has_java_files,
            "quality_issues": quality_issues,
            "total_files": len(files)
        }

    def regenerate_if_invalid(self, prompt: str, meta: dict, max_attempts: int = 3) -> list:
        """
        Generiert Dateien und wiederholt bei ungültigen Ergebnissen.
        """
        for attempt in range(max_attempts):
            try:
                print_panel(f"[CodeAgent] Generation attempt", f"{attempt + 1}/{max_attempts}")
                files = self.generate_files(prompt, meta)
                
                validation = self.validate_generated_files(files)
                if validation["valid"]:
                    print_panel("[CodeAgent] Generation successful", f"Valid files generated on attempt {attempt + 1}")
                    return files
                else:
                    print_panel(f"[CodeAgent] Attempt {attempt + 1} failed validation", str(validation))
                    
            except Exception as e:
                print_panel(f"[CodeAgent] Attempt {attempt + 1} failed with error", str(e))
                
        raise RuntimeError(f"Failed to generate valid files after {max_attempts} attempts")