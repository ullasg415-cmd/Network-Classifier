import { useState } from "react";
import { api } from "../api.js";
import { addHistory } from "../storage.js";
import UploadBox from "../components/UploadBox.jsx";
import ErrorNotice from "../components/ErrorNotice.jsx";
import NetworkResults from "../components/NetworkResults.jsx";
import TextResult from "../components/TextResult.jsx";
import VideoResult from "../components/VideoResult.jsx";

const MODES = {
  network: {
    label: "Network traffic",
    accept: ".pcap,.pcapng,.csv",
    hint: "A packet capture (.pcap, .pcapng) or a CSV of flows. IPFIX and NetFlow exports are not supported yet.",
    run: api.classifyNetwork,
  },
  text: {
    label: "Documents",
    accept: ".pdf,.docx,.txt",
    hint: "A PDF, Word (.docx) or plain text file.",
    run: api.classifyText,
  },
  video: {
    label: "Video",
    accept: ".mp4,.mov,.mkv,.avi,.webm",
    hint: "Upload a video file for visual scene classification.",
    run: api.classifyVideo,
  },
};

export default function ClassifyPage({ onSaved }) {
  const [mode, setMode] = useState("network");
  // Each flow keeps its own file, result and error, so switching tabs loses nothing.
  const [state, setState] = useState({ network: {}, text: {}, video: {} });
  const [busy, setBusy] = useState(false);

  const cur = state[mode];
  const patch = (m, values) => setState((s) => ({ ...s, [m]: { ...s[m], ...values } }));

  async function classify() {
    const m = mode;
    patch(m, { error: null });
    setBusy(true);
    try {
      const result = await MODES[m].run(cur.file);
      patch(m, { result });
      addHistory(m, result);
      onSaved?.();
    } catch (error) {
      patch(m, { error, result: null });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <h2>Classify</h2>
      <div className="tabs" role="tablist" aria-label="What to classify">
        {Object.entries(MODES).map(([id, m]) => (
          <button
            key={id}
            role="tab"
            aria-selected={mode === id}
            className={`tab${mode === id ? " is-on" : ""}`}
            onClick={() => setMode(id)}
          >
            {m.label}
          </button>
        ))}
      </div>

      <UploadBox
        accept={MODES[mode].accept}
        hint={MODES[mode].hint}
        file={cur.file}
        disabled={busy}
        onFile={(file) => patch(mode, { file, error: null })}
      />
      <div className="actions">
        <button className="btn btn--primary" disabled={!cur.file || busy} onClick={classify}>
          {busy ? "Classifying" : "Classify file"}
        </button>
      </div>

      <ErrorNotice error={cur.error} onDismiss={() => patch(mode, { error: null })} />
      {cur.result && mode === "network" && <NetworkResults data={cur.result} />}
      {cur.result && mode === "text" && <TextResult data={cur.result} />}
      {cur.result && mode === "video" && <VideoResult data={cur.result} />}
    </div>
  );
}
