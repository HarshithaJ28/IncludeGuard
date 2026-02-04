import * as vscode from 'vscode';
import { IncludeGuardAnalyzer } from './analyzer';

let analyzer: IncludeGuardAnalyzer | undefined;

export function activate(context: vscode.ExtensionContext) {
    console.log('IncludeGuard extension activated');

    // Create analyzer
    analyzer = new IncludeGuardAnalyzer(context);

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('includeguard.analyzeFile', async () => {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                await analyzer?.analyzeFile(editor.document);
                vscode.window.showInformationMessage('IncludeGuard: Analysis complete');
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('includeguard.clearDiagnostics', () => {
            analyzer?.clearDiagnostics();
            vscode.window.showInformationMessage('IncludeGuard: Cleared warnings');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('includeguard.analyzeProject', async () => {
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            if (!workspaceFolder) {
                vscode.window.showErrorMessage('No workspace folder open');
                return;
            }

            // Find all C++ files and analyze
            const files = await vscode.workspace.findFiles('**/*.{cpp,cc,cxx,h,hpp}', '**/node_modules/**', 1000);
            
            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'IncludeGuard: Analyzing project',
                cancellable: true
            }, async (progress, token) => {
                for (let i = 0; i < files.length; i++) {
                    if (token.isCancellationRequested) {
                        break;
                    }

                    const document = await vscode.workspace.openTextDocument(files[i]);
                    await analyzer?.analyzeFile(document);
                    
                    progress.report({
                        increment: 100 / files.length,
                        message: `${i + 1}/${files.length} files`
                    });
                }
            });

            vscode.window.showInformationMessage(`IncludeGuard: Analyzed ${files.length} files`);
        })
    );

    // Auto-analyze on file save
    context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument(async (document) => {
            const config = vscode.workspace.getConfiguration('includeguard');
            if (config.get<boolean>('analyzeOnSave', true)) {
                if (document.languageId === 'cpp' || document.languageId === 'c') {
                    await analyzer?.analyzeFile(document);
                }
            }
        })
    );

    // Auto-analyze when opening a file
    context.subscriptions.push(
        vscode.workspace.onDidOpenTextDocument(async (document) => {
            const config = vscode.workspace.getConfiguration('includeguard');
            if (config.get<boolean>('analyzeOnOpen', true)) {
                if (document.languageId === 'cpp' || document.languageId === 'c') {
                    await analyzer?.analyzeFile(document);
                }
            }
        })
    );

    // Analyze currently open document
    const activeEditor = vscode.window.activeTextEditor;
    if (activeEditor && (activeEditor.document.languageId === 'cpp' || activeEditor.document.languageId === 'c')) {
        analyzer.analyzeFile(activeEditor.document);
    }
}

export function deactivate() {
    analyzer?.dispose();
}
