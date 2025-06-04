"use strict";
// src/extension.ts
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
function activate(context) {
    context.subscriptions.push(vscode.commands.registerCommand('mirthPluginGen.openChat', () => {
        MirthChatPanel.createOrShow(context.extensionUri);
    }));
}
class MirthChatPanel {
    static currentPanel;
    _panel;
    _extensionUri;
    _disposables = [];
    static createOrShow(extensionUri) {
        const column = vscode.ViewColumn.Beside;
        if (MirthChatPanel.currentPanel) {
            MirthChatPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel('mirthChat', 'Mirth Plugin AI Chat', column, {
            enableScripts: true,
            retainContextWhenHidden: true,
        });
        MirthChatPanel.currentPanel = new MirthChatPanel(panel, extensionUri);
    }
    constructor(panel, extensionUri) {
        this._panel = panel;
        this._extensionUri = extensionUri;
        this._panel.webview.html = this._getHtml();
        this._panel.webview.onDidReceiveMessage(async (message) => {
            if (message.command === 'sendPrompt') {
                const prompt = message.text;
                this._panel.webview.postMessage({
                    command: 'showStatus',
                    text: 'Analysiere Prompt…',
                });
                try {
                    const response = await fetch('http://127.0.0.1:8000/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ prompt }),
                    });
                    if (!response.ok) {
                        this._panel.webview.postMessage({
                            command: 'showError',
                            text: 'Fehler vom Backend: ' + response.statusText,
                        });
                        return;
                    }
                    const data = await response.json();
                    this._panel.webview.postMessage({
                        command: 'showSteps',
                        steps: data.steps,
                        files: data.files,
                        msg: data.msg ?? null,
                        error: data.error ?? null,
                    });
                }
                catch (err) {
                    this._panel.webview.postMessage({
                        command: 'showError',
                        text: 'Verbindungsfehler: ' + (err?.message || err),
                    });
                }
            }
        }, undefined, this._disposables);
        panel.onDidDispose(() => this.dispose(), null, this._disposables);
    }
    dispose() {
        MirthChatPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const d = this._disposables.pop();
            if (d)
                d.dispose();
        }
    }
    _getHtml() {
        return `
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <title>Mirth Plugin AI Chat</title>
  <style>
    html, body {
      margin: 0;
      padding: 0;
      height: 100vh;
      box-sizing: border-box;
      font-family: 'Segoe UI', Arial, sans-serif;
      background: #181c24;
      color: #e8e9ed;
    }
    #mainFlex {
      display: flex;
      flex-direction: column;
      height: 100vh;
      min-height: 100vh;
      width: 100vw;
    }
    #chat {
      display: flex;
      flex-direction: column;
      flex: 9;
      width: 100%;
      background: #232734;
      border: 1px solid #242d3d;
      border-radius: 12px 12px 0 0;
      padding: 18px 16px;
      overflow-y: auto;
      font-size: 1.18em;
      box-shadow: 0 4px 18px #15192030;
      box-sizing: border-box;
    }
    #chatHistory {
      flex: 1;
      overflow-y: auto;
    }
    #statusBar {
      min-height: 30px;
      padding: 5px 0;
    }
    .chatline { margin-bottom: 18px; word-wrap: break-word; }
    .user { color: #6cb3fa; }
    .ai { color: #e9e57e; }
    .ai-status { color: #f5a623; }
    .error { color: #e05353; }
    ul.filelist { margin: 12px 0 0 12px; padding-left: 14px; }
    ul.filelist li { font-size: 1.03em; margin-bottom: 6px; color: #b7dafd; }
    #promptRow {
      flex: 1;
      display: flex;
      gap: 8px;
      padding: 12px;
      background: #181c24;
      box-sizing: border-box;
    }
    #prompt {
      flex: 1;
      background: #1c2030;
      color: #e8e9ed;
      font-size: 1.14em;
      padding: 12px 14px;
      border: 1px solid #232734;
      border-radius: 8px;
      outline: none;
      transition: border 0.15s;
      box-sizing: border-box;
    }
    #prompt:focus { border: 1.5px solid #6cb3fa; }
    #send {
      background: #5ca6ff;
      color: #222;
      font-weight: bold;
      border: none;
      border-radius: 8px;
      font-size: 1.12em;
      padding: 0 26px;
      cursor: pointer;
      transition: background 0.17s, color 0.13s;
      white-space: nowrap;
      box-sizing: border-box;
    }
    #send:hover { background: #75ee96; color: #222; }
  </style>
</head>
<body>
  <div id="mainFlex">
    <div id="chat">
      <div id="chatHistory"></div>
      <div id="statusBar"></div>
    </div>
    <div id="promptRow">
      <input id="prompt" type="text"
             placeholder="Plugin-Beschreibung hier eingeben..."
             autocomplete="off" />
      <button id="send">Senden</button>
    </div>
  </div>
  <script>
    const chatHistory = document.getElementById('chatHistory');
    const statusBar = document.getElementById('statusBar');
    const sendBtn = document.getElementById('send');
    const promptInput = document.getElementById('prompt');

    sendBtn.addEventListener('click', sendPrompt);
    promptInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') sendPrompt();
    });

    // Initiale Systemnachricht
    addLineToHistory('<b class="ai">System:</b> Chat bereit. Beschreiben Sie Ihr Plugin!', 'ai');

    function sendPrompt() {
      const prompt = promptInput.value.trim();
      if (!prompt) return;

      // Benutzereingabe in den Verlauf
      addLineToHistory('<b class="user">Du:</b> ' + escapeHtml(prompt), 'user');
      
      // Status in separatem Bereich anzeigen
      statusBar.innerHTML = '<div class="chatline ai-status">Analysiere Prompt…</div>';
      
      scrollToBottom();

      // Prompt an Extension Host schicken
      window.vscode.postMessage({ command: 'sendPrompt', text: prompt });
      promptInput.value = '';
    }

    window.addEventListener('message', event => {
      const msg = event.data;

      if (msg.command === 'showStatus') {
        statusBar.innerHTML = '<div class="chatline ai-status">' + escapeHtml(msg.text) + '</div>';
        scrollToBottom();
      }
      else if (msg.command === 'showError') {
        statusBar.innerHTML = '';
        addLineToHistory('<b class="error">Fehler:</b> ' + escapeHtml(msg.text), 'error');
      }
      else if (msg.command === 'showSteps') {
        statusBar.innerHTML = '';
        
        // Verarbeitungsschritte anzeigen
        msg.steps.forEach(stepText => {
          addLineToHistory('<b class="ai-status">AI:</b> ' + escapeHtml(stepText), 'ai-status');
        });
        
        if (msg.files && msg.files.length > 0) {
          let fileListHtml = '<ul class="filelist">' +
            msg.files.map(f => {
              return '<li><b>' + escapeHtml(f.path) + '</b> ' +
                     '<span style="color:#e9e9e9;">(' + f.size_bytes + ' Bytes)</span>' +
                     '</li>';
            }).join('') +
            '</ul>';
          addLineToHistory('<b class="ai">AI:</b> Plugin generiert!<br>' + fileListHtml, 'ai');
        } else {
          addLineToHistory('<b class="ai">AI:</b> Plugin generiert!', 'ai');
        }
      }
      if (msg.msg) {
        addLineToHistory('<b class="ai-status">AI:</b> ' + escapeHtml(msg.msg), 'ai-status');
      }
      if (msg.error) {
        addLineToHistory('<b class="error">Fehler:</b> ' + escapeHtml(msg.error), 'error');
      }
      scrollToBottom();
    });

    function addLineToHistory(html, cssClass = '') {
      const line = document.createElement('div');
      line.className = 'chatline' + (cssClass ? ' ' + cssClass : '');
      line.innerHTML = html;
      chatHistory.appendChild(line);
      scrollToBottom();
    }

    function scrollToBottom() {
      chatHistory.scrollTop = chatHistory.scrollHeight;
      if (statusBar) {
        statusBar.scrollIntoView(false);
      }
    }

    function escapeHtml(text) {
      return ('' + text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }

    // VSCode‐API verfügbar machen
    // @ts-ignore
    window.vscode = acquireVsCodeApi();
  </script>
</body>
</html>
    `;
    }
}
function deactivate() { }
