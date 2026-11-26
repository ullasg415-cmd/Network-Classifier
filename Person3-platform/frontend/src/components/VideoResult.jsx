export default function VideoResult({ data }) {
  const confidence = Number(data.confidence ?? 0);
  const percent = confidence <= 1 ? confidence * 100 : confidence;

  return (
    <section className="results" aria-live="polite">
      <h3>Video classification result</h3>
      <p><strong>Category:</strong> {data.category || data.best_guess || "Unknown"}</p>
      <p><strong>Confidence:</strong> {percent.toFixed(1)}%</p>
      <p><strong>Model:</strong> {data.model_version || "Not specified"}</p>
      <p><strong>Source:</strong> {data.source || "Not specified"}</p>
      {data.duration_seconds != null && <p><strong>Duration:</strong> {Number(data.duration_seconds).toFixed(1)} seconds</p>}
      {data.frame_count != null && <p><strong>Frames analysed:</strong> {data.frame_count}</p>}
      {data.audio_detected != null && <p><strong>Audio detected:</strong> {data.audio_detected ? "Yes" : "No"}</p>}
      {data.audio_assisted != null && <p><strong>Audio assisted:</strong> {data.audio_assisted ? "Yes" : "No"}</p>}
      {Array.isArray(data.top_k) && data.top_k.length > 0 && (
        <>
          <h4>Other predictions</h4>
          <ul>
            {data.top_k.map((item, index) => (
              <li key={item.category || item.label || index}>
                {item.category || item.label || "Prediction"}: {((Number(item.confidence ?? item.score ?? 0) <= 1
                  ? Number(item.confidence ?? item.score ?? 0) * 100
                  : Number(item.confidence ?? item.score ?? 0))).toFixed(1)}%
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
