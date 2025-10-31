# Repository Guidelines

## Project Structure & Module Organization
This repository currently centers on `cap2.md`, a Markdown chapter that pairs the English narrative with Portuguese chapter headings. Keep each chapter in its own Markdown file at the repository root, using level-two headings (`##`) for chapter titles and preserving numeric order. If you introduce supporting materials, place them in a sibling `assets/` directory and reference them with relative paths.

## Build, Test, and Development Commands
This is a text-first project, so no build pipeline runs by default. Use `npx markdownlint cap2.md` to catch structural issues such as heading gaps or stray whitespace, and run `npx markdownlint "cap*.md"` after adding new chapters. When refining translations, `vale cap2.md` (if Vale is installed) helps maintain consistent tone and vocabulary.

## Coding Style & Naming Conventions
Write Markdown with hard wraps disabled; keep entire paragraphs on single lines to match the existing source excerpt. Use sentence case for headings, except for canonical bilingual chapter titles (for example, `## Capítulo Segundo.`). Introduce inline translations or notes using blockquotes prefixed with language tags (e.g., `> PT:`) and avoid HTML unless Markdown cannot express the intended structure.

## Testing Guidelines
Proofread each submission for alignment between the English source and any Portuguese notes; mismatches should be called out in PR descriptions. Before opening a PR, lint the touched files with the commands above and ensure spell-checkers flag no unresolved terms. Record outstanding ambiguities in a trailing checklist within the PR for reviewers to resolve.

## Commit & Pull Request Guidelines
There is no established git history, so follow an imperative scope-first style such as `Add glossary for chapter two`. Group unrelated fixes into separate commits to keep reviews focused. Pull requests should include a brief summary, direct links to the affected chapter headings, and—if you adjust translated passages—a comparison snippet or rationale for the adaptation. Request at least one review before merging and confirm lint results in the PR thread.

## Translation Workflow Tips
Source passages should stay faithful to the original prose; prefer footnotes for cultural context rather than in-line rewrites. When unsure about terminology, log the candidate terms in the PR body so future contributors can build a shared glossary. Preserve any archaic spellings present in the source unless modernization is the stated goal and the change is clearly explained.
