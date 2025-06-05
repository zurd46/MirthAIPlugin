// src/extension.ts

import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
  context.subscriptions.push(
    vscode.commands.registerCommand('mirthPluginGen.openChat', () => {
      MirthChatPanel.createOrShow(context.extensionUri);
    })
  );
}

class MirthChatPanel {
  public static currentPanel: MirthChatPanel | undefined;
  private readonly _panel: vscode.WebviewPanel;
  private readonly _extensionUri: vscode.Uri;
  private _disposables: vscode.Disposable[] = [];

  public static createOrShow(extensionUri: vscode.Uri) {
    const column = vscode.ViewColumn.Beside;
    if (MirthChatPanel.currentPanel) {
      MirthChatPanel.currentPanel._panel.reveal(column);
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      'mirthChat',
      'Mirth Plugin AI Chat',
      column,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
      }
    );

    MirthChatPanel.currentPanel = new MirthChatPanel(panel, extensionUri);
  }

  private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
    this._panel = panel;
    this._extensionUri = extensionUri;
    this._panel.webview.html = this._getHtml();

    this._panel.webview.onDidReceiveMessage(
      async (message: any) => {
        if (message.command === 'sendPrompt') {
          const prompt = message.text as string;
          this._panel.webview.postMessage({
            command: 'showStatus',
            text: 'Analyzing prompt…',
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
                text: 'Backend error: ' + response.statusText,
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
          } catch (err) {
            this._panel.webview.postMessage({
              command: 'showError',
              text: 'Connection error: ' + ((err as any)?.message || err),
            });
          }
        }
      },
      undefined,
      this._disposables
    );

    panel.onDidDispose(() => this.dispose(), null, this._disposables);
  }

  public dispose() {
    MirthChatPanel.currentPanel = undefined;
    this._panel.dispose();
    while (this._disposables.length) {
      const d = this._disposables.pop();
      if (d) d.dispose();
    }
  }

  private _getHtml(): string {
    const iconUri = this._panel.webview.asWebviewUri(
      vscode.Uri.joinPath(this._extensionUri, 'images', 'icon.png')
    );

    return `
<!DOCTYPE html>
<html lang="en">
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
      color: #e3e6eb;
    }
    #mainFlex {
      display: flex;
      flex-direction: column;
      height: 100vh;
      min-height: 100vh;
      width: 100vw;
    }
    #headerBar {
      display: flex;
      align-items: center;
      background: #232734;
      border-radius: 12px 12px 0 0;
      padding: 12px 16px 8px 16px;
      font-size: 1.18em;
      font-weight: 600;
      margin-bottom: 2px;
      gap: 12px;
      border-bottom: 1px solid #242d3d;
      min-height: 36px;
    }
    #headerBar img {
      width: 30px;
      height: 30px;
      object-fit: contain;
      margin-right: 8px;
      background: transparent;
      display: inline-block;
      vertical-align: middle;
    }
    #headerTitle {
      color: #e3e6eb;
      font-size: 1.12em;
      letter-spacing: 0.3px;
    }
    #chat {
      display: flex;
      flex-direction: column;
      flex: 9;
      width: 100%;
      background: #232734;
      border: 1px solid #242d3d;
      border-radius: 0 0 0 0;
      padding: 18px 16px 0 16px;
      overflow-y: auto;
      font-size: 12px;
      box-shadow: 0 4px 18px #15192030;
      box-sizing: border-box;
    }
    #chatHistory {
      flex: 1;
      overflow-y: auto;
    }
    #statusBar {
      min-height: 28px;
      padding: 4px 0;
    }
    .chatline {
      margin-bottom: 16px;
      word-break: break-word;
    }
    .user {
      color:rgb(196, 218, 240);
      background: transparent;
    }
    .ai {
      color:rgb(71, 231, 143);
      font-size: 10px;
      font-style: normal;
      background: transparent;
    }
    .ai-status {
      color:rgb(71, 231, 143);
      font-style: normal;
      font-size: 10px;
      background: transparent;
    }
    .error {
      color: #df4444;
      font-weight: 500;
      font-size: 10px;
      background: transparent;
    }
    ul.filelist { margin: 10px 0 0 14px; padding-left: 14px; }
    ul.filelist li { font-size: 10px; margin-bottom: 4px; color: rgb(71, 231, 143); }
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
      background: #212431;
      color: #e3e6eb;
      font-size: 1.09em;
      padding: 12px 14px;
      border: 1px solid #242d3d;
      border-radius: 8px;
      outline: none;
      transition: border 0.15s;
      box-sizing: border-box;
    }
    #prompt:focus { border: 1.5px solid #a7c7e7; }
    #send {
      background: #c4d3ee;
      color: #212431;
      font-weight: 600;
      border: none;
      border-radius: 8px;
      font-size: 1.10em;
      padding: 0 24px;
      cursor: pointer;
      transition: background 0.17s, color 0.13s;
      white-space: nowrap;
      box-sizing: border-box;
    }
    #send:hover { background: #9cc6e9; color: #1d263a; }
  </style>
</head>
<body>
  <div id="mainFlex">
    <div id="headerBar">
      <img src="${iconUri}" alt="Mirth Plugin AI" width="30" height="30"/>
      <span id="headerTitle">Mirth Plugin AI Chat</span>
    </div>
    <div id="chat">
      <div id="chatHistory"></div>
      <div id="statusBar"></div>
    </div>
    <div id="promptRow">
      <input id="prompt" type="text"
             placeholder="Describe your plugin idea here…"
             autocomplete="off" />
      <button id="send">Send</button>
    </div>
  </div>
  <script>
    const chatHistory = document.getElementById('chatHistory');
    const statusBar = document.getElementById('statusBar');
    const sendBtn = document.getElementById('send');
    const promptInput = document.getElementById('prompt');

    // Initial AI message
    addLineToHistory('<b class="ai">AI:</b> Please describe your Mirth Connect plugin as precisely as possible.', 'ai');

    sendBtn.addEventListener('click', sendPrompt);
    promptInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') sendPrompt();
    });

    function sendPrompt() {
      const prompt = promptInput.value.trim();
      if (!prompt) return;

      addLineToHistory('<b class="user">You:</b> ' + escapeHtml(prompt), 'user');
      statusBar.innerHTML = '<div class="chatline ai-status">Analyzing prompt…</div>';
      scrollToBottom();

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
        addLineToHistory('<b class="error">Error:</b> ' + escapeHtml(msg.text), 'error');
      }
      else if (msg.command === 'showSteps') {
        statusBar.innerHTML = '';
        msg.steps.forEach(stepText => {
          addLineToHistory('<b class="ai-status">AI:</b> ' + escapeHtml(stepText), 'ai-status');
        });
        if (msg.files && msg.files.length > 0) {
          let fileListHtml = '<ul class="filelist">' +
            msg.files.map(f => {
              return '<li><b>' + escapeHtml(f.path) + '</b> ' +
                     '<span style="color:#e3e6eb;">(' + f.size_bytes + ' Bytes)</span>' +
                     '</li>';
            }).join('') +
            '</ul>';
          addLineToHistory('<b class="ai">AI:</b> Plugin generated!<br>' + fileListHtml, 'ai');
        } else {
          addLineToHistory('<b class="ai">AI:</b> Plugin generated!', 'ai');
        }
      }
      if (msg.msg) {
        addLineToHistory('<b class="ai-status">AI:</b> ' + escapeHtml(msg.msg), 'ai-status');
      }
      if (msg.error) {
        addLineToHistory('<b class="error">Error:</b> ' + escapeHtml(msg.error), 'error');
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

    // Make VSCode API available
    // @ts-ignore
    window.vscode = acquireVsCodeApi();
  </script>
</body>
</html>
    `;
  }
}

export function deactivate() {}
