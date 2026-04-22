import { examplePrompts } from "../features/parser/examplePrompts";

interface RequirementInputProps {
  value: string;
  isLoading: boolean;
  statusMessage?: string | null;
  onChange: (value: string) => void;
  onSubmit: () => void;
}

export function RequirementInput({ value, isLoading, statusMessage, onChange, onSubmit }: RequirementInputProps) {
  return (
    <section className="hero-card">
      <div className="hero-layout">
        <div className="hero-main">
          <div className="hero-copy">
            <span className="eyebrow">Plain-English brief to architecture</span>
            <h1>ScaleCraft</h1>
            <p>Turn one product brief into a system architecture you can review with your team.</p>
          </div>

          <label className="input-label" htmlFor="requirement-text">
            Product Requirement
          </label>
          <textarea
            id="requirement-text"
            className="requirement-input"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder="Describe the product, traffic expectations, integrations, and any availability or scaling constraints."
            rows={8}
          />

          <div className="actions-row">
            <button className="primary-button" onClick={onSubmit} disabled={isLoading || value.trim().length < 20}>
              {isLoading ? "Generating..." : "Generate Architecture"}
            </button>
            {statusMessage ? <span className="status-inline">{statusMessage}</span> : null}
          </div>

          <div className="examples-row">
            {examplePrompts.map((prompt, index) => (
              <button key={prompt} className="example-chip" type="button" onClick={() => onChange(prompt)}>
                Example {index + 1}
              </button>
            ))}
          </div>
        </div>

        <aside className="hero-aside" aria-hidden="true">
          <div className="hero-orb" />
          <div className="hero-note hero-note-top">
            <span>System</span>
            <strong>Shape</strong>
          </div>
          <div className="hero-note hero-note-middle">
            <span>Service</span>
            <strong>Layout</strong>
          </div>
          <div className="hero-note hero-note-bottom">
            <span>Scaling</span>
            <strong>Notes</strong>
          </div>
        </aside>
      </div>
    </section>
  );
}
