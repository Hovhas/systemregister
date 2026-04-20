#!/usr/bin/env node
/**
 * Quality Guardrails Hook
 *
 * Blockerar potentiellt farliga kod-mönster i realtid.
 * Triggas: PreToolUse för Edit/Write
 *
 * Regler:
 * - TypeScript: blockerar `any` typ utan motivering
 * - Python: blockerar `# type: ignore` utan motivering
 * - SQL: blockerar UPDATE/DELETE utan WHERE
 * - Bash/Shell: blockerar exponering av .env filer
 * - Secrets: blockerar hårdkodade API-nycklar/tokens
 * - Iteration-guard: varnar/blockerar vid upprepad redigering av samma fil
 */

const fs = require('fs');
const path = require('path');

const EDIT_STATE_FILE = path.join(__dirname, 'state', 'edit-count.json');
const EDIT_WARN_THRESHOLD = 3;
const EDIT_BLOCK_THRESHOLD = 5;

// Läs tool input från stdin
let inputData = '';
process.stdin.setEncoding('utf8');

process.stdin.on('data', (chunk) => {
  inputData += chunk;
});

process.stdin.on('end', () => {
  try {
    const toolInput = JSON.parse(inputData);

    // Iteration-guard: kontrollera upprepade edits av samma fil
    const iterResult = checkIterationGuard(toolInput);
    if (iterResult.blocked) {
      console.error(`\n[ITERATION-GUARD] ${iterResult.reason}`);
      console.error(`Fil: ${iterResult.file}`);
      console.error(`Förslag: ${iterResult.suggestion}\n`);
      process.exit(1);
    }
    if (iterResult.warning) {
      console.error(`\n[ITERATION-GUARD] Varning: ${iterResult.warning}`);
    }

    const result = validateToolInput(toolInput);

    if (result.blocked) {
      console.error(`\n[QUALITY-GUARD] ${result.reason}`);
      console.error(`Fil: ${result.file || 'okänd'}`);
      console.error(`Regel: ${result.rule}`);
      console.error(`Förslag: ${result.suggestion}\n`);
      process.exit(1);
    }

    process.exit(0);
  } catch (err) {
    // Ogiltigt JSON — kan inte avgöra blockering, låt igenom med varning
    process.stderr.write(`[quality-guard] VARNING: Kunde inte parsa input: ${err.message}\n`);
    process.exit(0);
  }
});

function checkIterationGuard(input) {
  const toolName = input.tool_name || '';
  if (!['Edit', 'Write'].includes(toolName)) return {};

  const filePath = (input.tool_input || {}).file_path || '';
  if (!filePath) return {};

  let state = {};
  try {
    if (fs.existsSync(EDIT_STATE_FILE)) {
      state = JSON.parse(fs.readFileSync(EDIT_STATE_FILE, 'utf8'));
    }
  } catch { state = {}; }

  state[filePath] = (state[filePath] || 0) + 1;
  const count = state[filePath];

  try {
    const dir = path.dirname(EDIT_STATE_FILE);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(EDIT_STATE_FILE, JSON.stringify(state, null, 2));
  } catch { /* ignore */ }

  if (count >= EDIT_BLOCK_THRESHOLD) {
    return {
      blocked: true,
      file: filePath,
      reason: `Fil redigerad ${count} gånger denna session (max ${EDIT_BLOCK_THRESHOLD})`,
      suggestion: 'Stanna upp och tänk om. Looping-beteende detekterat. Prova ett annat angreppssätt.'
    };
  }

  if (count >= EDIT_WARN_THRESHOLD) {
    return {
      warning: `${filePath} redigerad ${count}/${EDIT_BLOCK_THRESHOLD} gånger. Närmar sig gränsen.`
    };
  }

  return {};
}

function validateToolInput(input) {
  const toolName = input.tool_name || '';
  const params = input.tool_input || {};

  if (!['Edit', 'Write'].includes(toolName)) {
    return { blocked: false };
  }

  const filePath = params.file_path || '';
  const content = params.new_string || params.content || '';

  if (!content) {
    return { blocked: false };
  }

  const ext = filePath.split('.').pop()?.toLowerCase() || '';

  // TypeScript/JavaScript: blockera obefogad `any`
  if (['ts', 'tsx', 'js', 'jsx'].includes(ext)) {
    const anyPattern = /:\s*any\s*[;,)=\]]/g;
    const matches = content.match(anyPattern);

    if (matches && matches.length > 0) {
      if (!content.includes('// eslint-disable') &&
          !content.includes('// @ts-ignore') &&
          !content.includes('// any: ')) {
        return {
          blocked: true,
          file: filePath,
          rule: 'no-untyped-any',
          reason: 'Använder `any` typ utan motivering',
          suggestion: 'Använd specifik typ, `unknown`, eller lägg till kommentar: // any: <motivering>'
        };
      }
    }
  }

  // Python: blockera obefogad type: ignore
  if (['py'].includes(ext)) {
    if (content.includes('# type: ignore') && !content.includes('# type: ignore[')) {
      return {
        blocked: true,
        file: filePath,
        rule: 'no-blanket-type-ignore',
        reason: 'Använder blanket `# type: ignore` utan specifik kod',
        suggestion: 'Använd `# type: ignore[specific-error]` med felkod'
      };
    }
  }

  // SQL: blockera UPDATE/DELETE utan WHERE
  if (['sql'].includes(ext) || content.match(/\b(UPDATE|DELETE)\s+/i)) {
    const lines = content.split('\n');
    let inBlockComment = false;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (inBlockComment) {
        if (line.includes('*/')) inBlockComment = false;
        continue;
      }
      if (line.includes('/*')) {
        inBlockComment = true;
        if (line.indexOf('*/') > line.indexOf('/*')) inBlockComment = false;
        continue;
      }

      const trimmed = line.trimStart();
      if (trimmed.startsWith('--') || trimmed.startsWith('//') || trimmed.startsWith('#')) {
        continue;
      }

      const lineUpper = line.toUpperCase();
      if ((lineUpper.includes('UPDATE ') || lineUpper.includes('DELETE ')) &&
          !lineUpper.includes('WHERE') &&
          !lines.slice(i, i + 20).join(' ').toUpperCase().includes('WHERE')) {
        return {
          blocked: true,
          file: filePath,
          rule: 'sql-require-where',
          reason: 'UPDATE/DELETE utan WHERE-villkor',
          suggestion: 'Lägg till WHERE-villkor för att undvika att påverka alla rader'
        };
      }
    }
  }

  // Shell/Bash: blockera cat/echo av .env
  if (['sh', 'bash', 'zsh'].includes(ext) || filePath.includes('.sh')) {
    const envExpose = /\b(cat|echo|printf|head|tail|less|more)\s+[^\n]*\.env\b/i;
    if (envExpose.test(content)) {
      return {
        blocked: true,
        file: filePath,
        rule: 'no-env-expose',
        reason: 'Potentiell exponering av .env fil',
        suggestion: 'Använd `source .env` eller läs enskilda variabler med `grep`'
      };
    }
  }

  // Secrets: blockera uppenbara hårdkodade secrets
  const secretPatterns = [
    { pattern: /['"]sk-[a-zA-Z0-9]{20,}['"]/, name: 'OpenAI API key' },
    { pattern: /['"]sk-ant-[a-zA-Z0-9-]{20,}['"]/, name: 'Anthropic API key' },
    { pattern: /['"]cf-[a-zA-Z0-9_-]{20,}['"]/, name: 'Cloudflare token' },
    { pattern: /['"]ghp_[a-zA-Z0-9]{36,}['"]/, name: 'GitHub Personal Access Token' },
    { pattern: /['"]gho_[a-zA-Z0-9]{36,}['"]/, name: 'GitHub OAuth Token' },
    { pattern: /['"]glpat-[a-zA-Z0-9-]{20,}['"]/, name: 'GitLab Personal Access Token' },
    { pattern: /['"]xoxb-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{24,}['"]/, name: 'Slack Bot Token' },
    { pattern: /['"]AKIA[0-9A-Z]{16}['"]/, name: 'AWS Access Key ID' },
    { pattern: /password\s*[:=]\s*['"][^'"]{8,}['"](?!\s*\|\s*env)/i, name: 'Hardcoded password' },
  ];

  for (const { pattern, name } of secretPatterns) {
    if (pattern.test(content)) {
      return {
        blocked: true,
        file: filePath,
        rule: 'no-hardcoded-secrets',
        reason: `Potentiell hårdkodad secret upptäckt: ${name}`,
        suggestion: 'Använd miljövariabler för secrets.'
      };
    }
  }

  return { blocked: false };
}
