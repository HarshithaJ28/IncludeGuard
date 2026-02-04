import * as vscode from 'vscode';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as path from 'path';

const execAsync = promisify(exec);

interface IncludeInfo {
    header: string;
    line: number;
    is_system: boolean;
    cost: number;
    likely_used: boolean;
    confidence: number;
}

interface AnalysisResult {
    file: string;
    includes: IncludeInfo[];
    summary: {
        total_cost: number;
        wasted_cost: number;
        potential_savings_pct: number;
    };
    optimization_opportunities: Array<{
        header: string;
        line: number;
        estimated_cost: number;
    }>;
}

export class IncludeGuardAnalyzer {
    private diagnosticCollection: vscode.DiagnosticCollection;
    private statusBarItem: vscode.StatusBarItem;
    private costDecorationType: vscode.TextEditorDecorationType;
    private outputChannel: vscode.OutputChannel;

    constructor(context: vscode.ExtensionContext) {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('includeguard');
        this.statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
        this.outputChannel = vscode.window.createOutputChannel('IncludeGuard');
        
        // Create decoration type for cost annotations
        this.costDecorationType = vscode.window.createTextEditorDecorationType({
            after: {
                margin: '0 0 0 3em',
                fontStyle: 'italic',
                color: new vscode.ThemeColor('editorCodeLens.foreground')
            }
        });

        context.subscriptions.push(
            this.diagnosticCollection,
            this.statusBarItem,
            this.costDecorationType,
            this.outputChannel
        );
    }

    async analyzeFile(document: vscode.TextDocument): Promise<void> {
        // Only analyze C/C++ files
        if (document.languageId !== 'cpp' && document.languageId !== 'c') {
            return;
        }

        const config = vscode.workspace.getConfiguration('includeguard');
        const pythonPath = config.get<string>('pythonPath', 'python');
        const filePath = document.uri.fsPath;

        this.statusBarItem.text = '$(sync~spin) IncludeGuard: Analyzing...';
        this.statusBarItem.show();

        try {
            // Call Python CLI
            const command = `"${pythonPath}" -m includeguard.cli inspect "${filePath}" --json`;
            this.outputChannel.appendLine(`Running: ${command}`);

            const { stdout, stderr } = await execAsync(command, {
                cwd: path.dirname(filePath),
                timeout: 30000
            });

            if (stderr) {
                this.outputChannel.appendLine(`stderr: ${stderr}`);
            }

            // Parse JSON output
            const result: AnalysisResult = JSON.parse(stdout);
            
            // Update diagnostics
            this.updateDiagnostics(document, result);
            
            // Update decorations
            if (config.get<boolean>('showCostDecorations', true)) {
                this.updateDecorations(document, result);
            }
            
            // Update status bar
            const wasteP ct = result.summary.potential_savings_pct;
            const wastedCost = result.summary.wasted_cost;
            this.statusBarItem.text = `$(shield) IncludeGuard: ${wasteP ct.toFixed(1)}% waste (${wastedCost.toFixed(0)} units)`;
            this.statusBarItem.tooltip = `Total cost: ${result.summary.total_cost.toFixed(0)} units\\nPotential savings: ${wasteP ct.toFixed(1)}%`;
            this.statusBarItem.backgroundColor = wasteP ct > 30 ? new vscode.ThemeColor('statusBarItem.errorBackground') : undefined;

        } catch (error: any) {
            this.outputChannel.appendLine(`Error: ${error.message}`);
            this.statusBarItem.text = '$(alert) IncludeGuard: Error';
            this.statusBarItem.tooltip = error.message;
            
            // Show error notification
            vscode.window.showErrorMessage(`IncludeGuard: ${error.message}`);
        }
    }

    private updateDiagnostics(document: vscode.TextDocument, result: AnalysisResult): void {
        const diagnostics: vscode.Diagnostic[] = [];
        const config = vscode.workspace.getConfiguration('includeguard');
        const costThreshold = config.get<number>('costThreshold', 500);

        for (const opp of result.optimization_opportunities) {
            if (opp.estimated_cost < costThreshold) {
                continue;
            }

            const line = opp.line - 1; // Convert to 0-based
            const range = document.lineAt(line).range;
            
            const severity = opp.estimated_cost > 2000 
                ? vscode.DiagnosticSeverity.Warning 
                : vscode.DiagnosticSeverity.Information;

            const diagnostic = new vscode.Diagnostic(
                range,
                `Unused include '${opp.header}' (costs ${opp.estimated_cost.toFixed(0)} units)`,
                severity
            );
            
            diagnostic.source = 'IncludeGuard';
            diagnostic.code = 'unused-include';
            diagnostics.push(diagnostic);
        }

        this.diagnosticCollection.set(document.uri, diagnostics);
    }

    private updateDecorations(document: vscode.TextDocument, result: AnalysisResult): void {
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.document.uri.toString() !== document.uri.toString()) {
            return;
        }

        const decorations: vscode.DecorationOptions[] = [];

        for (const inc of result.includes) {
            if (inc.cost < 100) continue; // Skip low-cost includes

            const line = inc.line - 1;
            if (line >= 0 && line < document.lineCount) {
                const range = new vscode.Range(line, 0, line, 0);
                
                const costStr = inc.cost >= 1000 
                    ? `${(inc.cost / 1000).toFixed(1)}k`
                    : inc.cost.toFixed(0);
                
                const usageStr = inc.likely_used ? '✓' : '✗';
                const decoration: vscode.DecorationOptions = {
                    range,
                    renderOptions: {
                        after: {
                            contentText: `  💰 ${costStr} units ${usageStr}`,
                            color: inc.likely_used ? '#10b981' : '#ef4444'
                        }
                    }
                };
                
                decorations.push(decoration);
            }
        }

        editor.setDecorations(this.costDecorationType, decorations);
    }

    clearDiagnostics(): void {
        this.diagnosticCollection.clear();
        this.statusBarItem.hide();
    }

    dispose(): void {
        this.diagnosticCollection.dispose();
        this.statusBarItem.dispose();
        this.costDecorationType.dispose();
        this.outputChannel.dispose();
    }
}
