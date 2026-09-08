import React from 'react';

/**
 * Renders formatted Markdown elements (Headers, Tables, Lists, Bold Text).
 */
export default function MarkdownRenderer({ content }) {
  if (!content) return <p style={{ color: 'var(--ink-muted)' }}>No content available for this section.</p>;

  // Split into lines for basic markdown parsing
  const lines = content.split('\n');
  const elements = [];
  let tableRows = [];
  let inTable = false;
  let listItems = [];
  let inList = false;

  const flushList = (key) => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`list-${key}`} style={{ margin: '0.75rem 0 1.25rem 1.25rem', lineHeight: '1.65' }}>
          {listItems.map((item, i) => (
            <li key={i} style={{ marginBottom: '0.4rem', color: 'var(--ink)' }}>
              {renderInline(item)}
            </li>
          ))}
        </ul>
      );
      listItems = [];
      inList = false;
    }
  };

  const flushTable = (key) => {
    if (tableRows.length > 0) {
      const headerRow = tableRows[0];
      const bodyRows = tableRows.slice(1).filter(r => !r.every(c => c.trim().match(/^:?-+:?$/)));

      elements.push(
        <div key={`table-${key}`} style={{ overflowX: 'auto', margin: '1rem 0 1.5rem 0' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem', border: '2px solid var(--border-dark)' }}>
            <thead>
              <tr style={{ background: 'var(--card-alt-bg)', borderBottom: '2px solid var(--border-dark)' }}>
                {headerRow.map((h, i) => (
                  <th key={i} style={{ padding: '0.65rem 0.85rem', textAlign: 'left', fontWeight: 700, borderRight: '1px solid var(--border-dark)' }}>
                    {renderInline(h.trim())}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {bodyRows.map((row, rIdx) => (
                <tr key={rIdx} style={{ borderBottom: '1px solid var(--border-dark)', background: rIdx % 2 === 0 ? 'var(--card-bg)' : 'var(--card-alt-bg)' }}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} style={{ padding: '0.6rem 0.85rem', borderRight: '1px solid var(--border-dark)' }}>
                      {renderInline(cell.trim())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      tableRows = [];
      inTable = false;
    }
  };

  const renderInline = (text) => {
    // Process bold **text**
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, pIdx) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={pIdx} style={{ fontWeight: 700, color: 'var(--ink)' }}>{part.slice(2, -2)}</strong>;
      }
      // Process italic *text*
      if (part.startsWith('*') && part.endsWith('*') && !part.startsWith('**')) {
        return <em key={pIdx} style={{ color: 'var(--ink-muted)' }}>{part.slice(1, -1)}</em>;
      }
      return part;
    });
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();

    // Table line: starts and ends with |
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      if (inList) flushList(idx);
      inTable = true;
      const cells = trimmed.split('|').slice(1, -1);
      tableRows.push(cells);
      return;
    } else if (inTable) {
      flushTable(idx);
    }

    // List item: starts with * or -
    if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
      inList = true;
      listItems.push(trimmed.slice(2));
      return;
    } else if (inList) {
      flushList(idx);
    }

    // Heading 3
    if (trimmed.startsWith('### ')) {
      elements.push(
        <h4 key={idx} style={{ fontSize: '1.15rem', fontWeight: 700, margin: '1.25rem 0 0.5rem 0', color: 'var(--ink)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span style={{ width: '8px', height: '8px', background: 'var(--accent, #C85A17)', display: 'inline-block' }}></span>
          {renderInline(trimmed.slice(4))}
        </h4>
      );
      return;
    }

    // Heading 2
    if (trimmed.startsWith('## ')) {
      elements.push(
        <h3 key={idx} style={{ fontSize: '1.3rem', fontWeight: 800, margin: '1.5rem 0 0.6rem 0', color: 'var(--ink)' }}>
          {renderInline(trimmed.slice(3))}
        </h3>
      );
      return;
    }

    // Regular paragraph
    if (trimmed) {
      elements.push(
        <p key={idx} style={{ marginBottom: '0.85rem', lineHeight: '1.65', color: 'var(--ink)', fontSize: '0.94rem' }}>
          {renderInline(trimmed)}
        </p>
      );
    }
  });

  if (inTable) flushTable('final');
  if (inList) flushList('final');

  return <div>{elements}</div>;
}
