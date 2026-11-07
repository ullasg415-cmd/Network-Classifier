import { useState } from "react";
import { clearHistory } from "../storage.js";
import { formatTime } from "../format.js";
import NetworkResults from "../components/NetworkResults.jsx";
import TextResult from "../components/TextResult.jsx";
import { LabelChip } from "../components/Chip.jsx";

function summary(entry) {
  if (entry.kind === "text") {
    return (
      <>
        <LabelChip label={entry.result.category} />
      </>
    );
  }
  const s = entry.result.summary;
  return (
    <span>
      {s.n_flows} flows, {s.n_unknown} unknown
    </span>
  );
}

export default function HistoryPage({ entries, onCleared }) {
  const [openId, setOpenId] = useState(null);

  return (
    <div className="page">
      <div className="page__head">
        <h2>History</h2>
        {entries.length > 0 && (
          <button
            className="btn btn--secondary"
            onClick={() => {
              if (window.confirm("Remove all saved results from this browser?")) {
                clearHistory();
                setOpenId(null);
                onCleared();
              }
            }}
          >
            Clear history
          </button>
        )}
      </div>
      <p className="muted">
        Results are saved in this browser only, so they stay after you refresh the page. They are not stored on the
        server.
      </p>

      {entries.length === 0 ? (
        <div className="empty">
          <p>Nothing here yet. Classify a file and its result will be saved.</p>
        </div>
      ) : (
        <ul className="history">
          {entries.map((e) => (
            <li key={e.id}>
              <button
                className="history__row"
                aria-expanded={openId === e.id}
                onClick={() => setOpenId(openId === e.id ? null : e.id)}
              >
                <span className="history__name">{e.filename || "(unnamed)"}</span>
                <span className="tag">{e.kind === "network" ? "network" : "document"}</span>
                <span className="history__summary">{summary(e)}</span>
                <span className="muted small">{formatTime(e.at)}</span>
              </button>
              {openId === e.id && (
                <div className="history__detail">
                  {e.kind === "network" ? (
                    <NetworkResults data={e.result} truncatedFrom={e.truncated ? e.totalFlows : null} />
                  ) : (
                    <TextResult data={e.result} />
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
