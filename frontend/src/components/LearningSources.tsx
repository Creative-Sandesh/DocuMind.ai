import type { Source } from "../types/chat";

function LearningSources({ sources, numbers }: { sources: Source[]; numbers?: number[] }) {
  const selected = numbers ? numbers.map((number) => ({ source: sources[number - 1], number })).filter((item) => item.source) : sources.map((source, index) => ({ source, number: index + 1 }));
  if (!selected.length) return null;
  return <div className="learning-sources">
    <h4>Sources</h4>
    <ul>{selected.map(({ source, number }) => <li key={`${number}-${source.chunk_id}`}>
      <strong>[{number}] {source.filename}</strong>
      {source.page_number != null && <span> · Page {source.page_number}</span>}
      {source.section_title && <span> · {source.section_title}</span>}
      <details><summary>View excerpt</summary><p>{source.text}</p></details>
    </li>)}</ul>
  </div>;
}

export default LearningSources;
