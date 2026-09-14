export function Spinner({ label }: { label?: string }) {
  return (
    <div className="spinner-wrap">
      <span className="spinner" aria-hidden="true" />
      {label && <span className="spinner-label">{label}</span>}
    </div>
  );
}

export function PageSpinner() {
  return (
    <div className="page-loading">
      <Spinner label="Loading…" />
    </div>
  );
}

export function ButtonSpinner() {
  return <span className="spinner spinner-sm" aria-hidden="true" />;
}
