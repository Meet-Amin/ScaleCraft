import type { ReactNode } from "react";

interface SectionCardProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
}

export function SectionCard({ title, subtitle, actions, children }: SectionCardProps) {
  return (
    <section className="section-card">
      <div className="section-header-row">
        <div className="section-header">
          <h2>{title}</h2>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        {actions ? <div className="section-actions">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}
