import type { ReactNode } from "react";

interface PageHeaderProps {
  icon?: string; // path under /icons/, e.g. "Travel/flights.svg"
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}

export default function PageHeader({ icon, title, description, actions }: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div className="flex items-start gap-3">
        {icon && (
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-100 to-brand-50">
            <img src={`/icons/${icon}`} alt="" className="h-5 w-5" aria-hidden="true" />
          </span>
        )}
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink-900">{title}</h1>
          {description && <p className="mt-1 max-w-2xl text-sm text-ink-500">{description}</p>}
        </div>
      </div>
      {actions}
    </div>
  );
}
