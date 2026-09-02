function SourceList({ sources }) {
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <div className="sources-container">
      <div className="sources-title">
        Sources
      </div>

      <div className="sources-list">
        {sources.map((source, index) => (
          <div
            className="source-card"
            key={`${source.document_id}-${index}`}
          >
            <div className="source-number">
              {index + 1}
            </div>

            <div className="source-info">
              <div className="source-name">
                {source.title}
              </div>

              <div className="source-meta">
                {source.category}

                {source.subcategory
                  ? ` · ${source.subcategory}`
                  : ""}
              </div>

              {source.url && (
                <a
                  className="source-link"
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  View source
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default SourceList;