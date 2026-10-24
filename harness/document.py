# -*- coding: utf-8 -*-
"""
Markdown-Native Document & Report Exporter for GoldTrader.
Architecture:
- Native UTF-8 Markdown (.md) export into ./output/ (Single Source of Truth)
- Strict Prohibition of ASCII tables (+----+), ASCII trees (├──), and ASCII box art
- Preservation of Mathematical and Quantitative Formulas (LaTeX / KaTeX)
- Strict Prohibition of Machine-Local Paths (C:, D:, file:// URIs) in saved documents
- Separation of Concerns: Clean Saved Files vs Chat-Only PDF/Printing Advisory
- Subprocess multi-line execution safety (sys.executable + NamedTemporaryFile)
"""

from __future__ import annotations
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional

logger = logging.getLogger("GoldTrader.DocumentExporter")

BOX_DRAWING_REGEX = re.compile(r"[\u2500-\u257F]")
ASCII_BOX_BORDER_REGEX = re.compile(r"^\s*(?:\+[=\-+]{2,}\+\s*)+$")
ASCII_FLOWCHART_ARROW_REGEX = re.compile(r"(?:\[.+?\]|\|.+?\|)\s*(?:-{2,}>|={2,}>)\s*(?:\[.+?\]|\|.+?\|)")
ASCII_TREE_REGEX = re.compile(r"[\u251C\u2514\u2502\u2500]?\s*[├└][─\-]+")
MARKDOWN_TABLE_SEPARATOR_REGEX = re.compile(r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$")
MERMAID_BLOCK_REGEX = re.compile(r"```mermaid\s*\n.*?```", re.DOTALL | re.IGNORECASE)
LOCAL_DRIVE_REGEX = re.compile(r"\b[A-Za-z]:[\\/][^\s\)\"\'>]*")
LOCAL_FILE_URI_REGEX = re.compile(r"file:\/\/[^\s\)\"\'>]*", re.IGNORECASE)



def detect_local_file_references(text: str) -> List[Dict[str, Any]]:
    """
    Detects forbidden machine-local absolute drive paths (e.g. C:, D:) and file:// URIs.
    Documents must only use repository-relative paths (e.g. ./output/...) or clean basenames.
    """
    violations: List[Dict[str, Any]] = []
    lines = text.splitlines()

    for idx, line in enumerate(lines, 1):
        clean_line = line.strip()
        # Find drive paths (e.g. C:\, D:/)
        for m in LOCAL_DRIVE_REGEX.finditer(clean_line):
            violations.append({
                "line": idx,
                "content": clean_line,
                "type": "local_drive_path",
                "matched": m.group(0),
                "recommendation": "Do not reference local drive letters (C:, D:). Use repository-relative paths (e.g. ./output/...) or basenames.",
            })
        # Find file:// URIs
        for m in LOCAL_FILE_URI_REGEX.finditer(clean_line):
            violations.append({
                "line": idx,
                "content": clean_line,
                "type": "local_file_uri",
                "matched": m.group(0),
                "recommendation": "Do not reference file:// URIs in saved documents. Use repository-relative paths or clean basenames.",
            })

    return violations


def sanitize_local_file_references(text: str, repo_root: Optional[Path] = None) -> Tuple[str, List[str]]:
    """
    Sanitizes forbidden machine-local drive letters (C:, D:) and file:// URIs in markdown text.
    Replaces repo-internal paths with repository-relative paths (./...) and external paths with basenames.
    """
    fixes: List[str] = []
    root = (repo_root or Path.cwd()).resolve()
    root_str = str(root).replace("\\", "/")
    
    # 1. Markdown link format: [label](file:///... or C:\...) -> [label](./relative or filename)
    def fix_md_link(match: re.Match) -> str:
        label = match.group(1)
        uri = match.group(2)
        # Strip file:/// or file://
        clean_path = re.sub(r"^file:\/{2,3}", "", uri, flags=re.IGNORECASE)
        clean_norm = clean_path.replace("\\", "/")
        if clean_norm.lower().startswith(root_str.lower()):
            rel_part = clean_norm[len(root_str):].lstrip("/")
            rel_path = f"./{rel_part}" if not rel_part.startswith("./") else rel_part
            fixes.append(f"Sanitized markdown link URI to relative: {rel_path}")
            return f"[{label}]({rel_path})"
        base = Path(clean_path).name
        fixes.append(f"Sanitized local link URI '{uri}' to basename '{base}'")
        return f"[{label}]({base})"

    sanitized = re.sub(
        r"\[([^\]]+)\]\(((?:file:\/\/\S*|[A-Za-z]:[\\/][^\)]*))\)",
        fix_md_link,
        text,
    )

    # 2. Raw file:// URIs: file:///C:/... -> ./... or basename
    def fix_raw_uri(match: re.Match) -> str:
        uri = match.group(0)
        clean_path = re.sub(r"^file:\/{2,3}", "", uri, flags=re.IGNORECASE)
        clean_norm = clean_path.replace("\\", "/")
        if clean_norm.lower().startswith(root_str.lower()):
            rel_part = clean_norm[len(root_str):].lstrip("/")
            rel_path = f"./{rel_part}" if not rel_part.startswith("./") else rel_part
            fixes.append(f"Sanitized raw file URI to relative: {rel_path}")
            return rel_path
        base = Path(clean_path).name
        fixes.append(f"Sanitized raw file URI to basename: {base}")
        return base

    sanitized = LOCAL_FILE_URI_REGEX.sub(fix_raw_uri, sanitized)

    # 3. Raw drive paths: C:\Ai_code\GoldTrader\... -> ./... or D:\... -> basename
    def fix_drive_path(match: re.Match) -> str:
        path_str = match.group(0)
        norm = path_str.replace("\\", "/")
        if norm.lower().startswith(root_str.lower()):
            rel_part = norm[len(root_str):].lstrip("/")
            rel_path = f"./{rel_part}" if not rel_part.startswith("./") else rel_part
            fixes.append(f"Sanitized repo-local path to relative: {rel_path}")
            return rel_path
        base = Path(path_str).name
        fixes.append(f"Sanitized external local path to basename: {base}")
        return base

    sanitized = LOCAL_DRIVE_REGEX.sub(fix_drive_path, sanitized)

    return sanitized, fixes


def detect_ascii_tables_or_diagrams(text: str) -> List[Dict[str, Any]]:
    violations: List[Dict[str, Any]] = []
    lines = text.splitlines()
    in_mermaid = False

    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.lower().startswith("```mermaid"):
            in_mermaid = True
            continue
        if in_mermaid and stripped.startswith("```"):
            in_mermaid = False
            continue
        if in_mermaid:
            continue

        clean_line = re.sub(r"`[^`\n]+`", "", stripped)
        if not clean_line:
            continue

        if ASCII_BOX_BORDER_REGEX.match(clean_line):
            violations.append({
                "line": idx,
                "content": stripped,
                "type": "ascii_table_border",
                "recommendation": "Replace ASCII border table with standard Markdown table (| ... |).",
            })
        elif ASCII_TREE_REGEX.search(clean_line):
            violations.append({
                "line": idx,
                "content": stripped,
                "type": "ascii_tree_diagram",
                "recommendation": "Use Mermaid flowchart (flowchart TD/LR) instead of ASCII tree structure.",
            })
        elif BOX_DRAWING_REGEX.search(clean_line):
            violations.append({
                "line": idx,
                "content": stripped,
                "type": "box_drawing_characters",
                "recommendation": "Use Mermaid diagram (```mermaid ... ```) for diagrams or Markdown table (| ... |) for tables.",
            })
        elif ASCII_FLOWCHART_ARROW_REGEX.search(clean_line):
            violations.append({
                "line": idx,
                "content": stripped,
                "type": "ascii_flowchart_arrow",
                "recommendation": "Convert ASCII arrow flowchart into a native Mermaid diagram (flowchart TD/LR).",
            })

    return violations


def audit_document_formatting(markdown_text: str) -> Dict[str, Any]:
    mermaid_matches = MERMAID_BLOCK_REGEX.findall(markdown_text)
    table_separator_count = sum(
        1 for line in markdown_text.splitlines() if MARKDOWN_TABLE_SEPARATOR_REGEX.match(line)
    )
    ascii_violations = detect_ascii_tables_or_diagrams(markdown_text)
    local_path_violations = detect_local_file_references(markdown_text)
    all_violations = ascii_violations + local_path_violations
    passed = len(all_violations) == 0

    return {
        "passed": passed,
        "has_mermaid": len(mermaid_matches) > 0,
        "mermaid_block_count": len(mermaid_matches),
        "has_markdown_table": table_separator_count > 0,
        "markdown_table_count": table_separator_count,
        "violations": all_violations,
        "ascii_violation_count": len(ascii_violations),
        "local_path_violation_count": len(local_path_violations),
        "violation_count": len(all_violations),
        "summary": "Document formatting fully compliant (Mermaid & Markdown tables, zero local file path references)"
        if passed
        else f"Found {len(all_violations)} formatting violations ({len(ascii_violations)} ASCII, {len(local_path_violations)} local file path references).",
    }


def get_pdf_export_guidance() -> str:
    """
    Returns standardized guidance for chat responses on how to print or
    export Markdown documents to PDF using modern tools with full
    LaTeX / KaTeX math and Mermaid rendering.
    IMPORTANT: This string should ONLY be shown in Chat Responses,
    and NEVER written into saved files in ./output/*.md.
    """
    return (
        "> 💡 **คำแนะนำสำหรับการพิมพ์หรือแปลงเป็น PDF (Printing & PDF Export Guide):**\n"
        "> รายงานและสเปกนี้ถูกจัดทำในรูปแบบ Markdown (`.md`) UTF-8 มาตรฐาน เพื่อรักษาความถูกต้องของสูตรคำนวณและแผนภาพ\n"
        ">\n"
        "> หากต้องการพิมพ์เป็นเอกสารหรือบันทึกเป็น PDF แนะนำให้เปิดไฟล์ `.md` ใน `./output/` ผ่านโปรแกรมดังต่อไปนี้:\n"
        "> 1. **Obsidian** (แนะนำสูงสุด): เปิดไฟล์ `.md` แล้วเลือกเมนู `Export to PDF` (รองรับภาษาไทย, แผนภาพ Mermaid และสูตร $\\LaTeX$ อัตโนมัติ 100%)\n"
        "> 2. **VS Code**: ติดตั้งส่วนขยาย *Markdown PDF* หรือ *Markdown Preview Enhanced* แล้วคลิกขวาเลือก `Export (pdf)`\n"
        "> 3. **Typora**: เลือกเมนู `File -> Export -> PDF` จัดหน้าเอกสารได้สวยงามตามมาตรฐานงานสารบรรณ\n"
        "> 4. **Google Chrome / Microsoft Edge**: ติดตั้ง Extension เช่น *Markdown Viewer* หรือเปิดดูผ่าน GitHub แล้วกด `Ctrl + P` (Print -> Save as PDF)\n"
    )


def export_markdown_document(
    title: str,
    markdown_content: str,
    filename: str,
    output_dir: Optional[Path] = None,
    include_pdf_guidance: bool = False,
) -> Path:
    """
    Saves document into ./output/<filename>.md with UTF-8 encoding.
    Enforces Clean Document Protocol: PDF/Print guidance is excluded from saved files
    by default (include_pdf_guidance=False).
    """
    base_dir = output_dir or (Path.cwd() / "output")
    base_dir.mkdir(parents=True, exist_ok=True)

    if not filename.endswith(".md"):
        filename += ".md"

    target_file = base_dir / filename

    content_parts = []
    stripped_content = markdown_content.strip()
    if not stripped_content.startswith("# "):
        content_parts.append(f"# {title}\n")
    content_parts.append(stripped_content)

    if include_pdf_guidance:
        content_parts.append("\n---\n")
        content_parts.append(get_pdf_export_guidance())

    full_text = "\n\n".join(content_parts) + "\n"

    # Strict Local Path Ban: Automatically sanitize any local drive letters (C:, D:) or file:// URIs
    sanitized_text, path_fixes = sanitize_local_file_references(full_text, repo_root=base_dir.parent)
    if path_fixes:
        for fix in path_fixes:
            logger.warning(f"Local Path Ban applied on export: {fix}")
    full_text = sanitized_text

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(full_text)

    logger.info(f"Exported clean markdown document to: {target_file}")
    return target_file


def run_safe_python_script(
    script_code: str,
    args: Optional[List[str]] = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as f:
        f.write(script_code)
        temp_script_path = Path(f.name)

    try:
        cmd = [sys.executable, str(temp_script_path)]
        if args:
            cmd.extend(args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result
    finally:
        temp_script_path.unlink(missing_ok=True)
