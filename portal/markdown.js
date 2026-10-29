"use strict";

function markdownInline(parent, value) {
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g;
  let offset = 0;
  for (const match of value.matchAll(pattern)) {
    parent.append(value.slice(offset, match.index));
    const token = match[0];
    let element;
    if (token.startsWith("[")) {
      const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
      element = document.createElement("span");
      element.textContent = link[1];
      element.title = link[2];
      if (URL.canParse(link[2])) {
        const url = new URL(link[2]);
        if (["https:", "http:"].includes(url.protocol)) {
          element = document.createElement("a");
          element.href = url.href;
          element.target = "_blank";
          element.rel = "noopener noreferrer";
          element.textContent = link[1];
        }
      }
    } else {
      const width = token.startsWith("**") ? 2 : 1;
      element = document.createElement(token.startsWith("`") ? "code" : width === 2 ? "strong" : "em");
      element.textContent = token.slice(width, -width);
    }
    parent.append(element);
    offset = match.index + token.length;
  }
  parent.append(value.slice(offset));
}

function renderMarkdown(target, source) {
  const lines = source.replace(/\r\n?/g, "\n").split("\n");
  const blocks = [];
  let index = 0;
  if (lines[0] === "---") {
    const end = lines.indexOf("---", 1);
    if (end > 0) index = end + 1;
  }
  const cells = (line) => line.trim().replace(/^\||\|$/g, "").split(/(?<!\\)\|/)
    .map((cell) => cell.trim().replace(/\\\|/g, "|"));
  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) { index++; continue; }
    const fence = /^\s*(`{3,}|~{3,})(.*)$/.exec(line);
    if (fence) {
      const code = [];
      index++;
      while (index < lines.length && !lines[index].trim().startsWith(fence[1])) code.push(lines[index++]);
      index++;
      const pre = document.createElement("pre");
      const content = document.createElement("code");
      content.textContent = code.join("\n");
      pre.append(content);
      blocks.push(pre);
      continue;
    }
    if (/^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(lines[index + 1] || "") && line.includes("|")) {
      const table = document.createElement("table");
      const row = (text, header) => {
        const tr = document.createElement("tr");
        for (const value of cells(text)) {
          const cell = document.createElement(header ? "th" : "td");
          markdownInline(cell, value);
          tr.append(cell);
        }
        return tr;
      };
      const head = document.createElement("thead");
      head.append(row(line, true));
      table.append(head);
      const body = document.createElement("tbody");
      index += 2;
      while (index < lines.length && lines[index].includes("|") && lines[index].trim())
        body.append(row(lines[index++], false));
      table.append(body);
      blocks.push(table);
      continue;
    }
    const heading = /^(#{1,6})\s+(.+)$/.exec(line);
    if (heading) {
      const element = document.createElement(`h${heading[1].length}`);
      markdownInline(element, heading[2]);
      blocks.push(element);
      index++;
      continue;
    }
    if (/^\s*([-*_])(?:\s*\1){2,}\s*$/.test(line)) {
      blocks.push(document.createElement("hr")); index++; continue;
    }
    const list = /^\s*(?:([-+*])|(\d+)[.)])\s+/.exec(line);
    if (list) {
      const element = document.createElement(list[2] ? "ol" : "ul");
      if (list[2]) element.start = Number(list[2]);
      const pattern = list[2] ? /^\s*\d+[.)]\s+/ : /^\s*[-+*]\s+/;
      while (index < lines.length && pattern.test(lines[index])) {
        const item = document.createElement("li");
        markdownInline(item, lines[index++].replace(pattern, ""));
        element.append(item);
      }
      blocks.push(element);
      continue;
    }
    const quote = /^>\s?(.*)$/.exec(line);
    const element = document.createElement(quote ? "blockquote" : "p");
    markdownInline(element, quote ? quote[1] : line);
    blocks.push(element);
    index++;
  }
  target.replaceChildren(...blocks);
}
