interface DeliverableCardProps {
  title: string;
  description: string;
  imageSrc: string;
  imageAlt: string;
  downloadHref: string;
}

export function DeliverableCard({
  title,
  description,
  imageSrc,
  imageAlt,
  downloadHref,
}: DeliverableCardProps) {
  return (
    <div className="flex flex-col overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-sm">
      <img src={imageSrc} alt={imageAlt} className="h-44 w-full border-b border-[var(--color-border)] object-cover object-top" loading="lazy" />
      <div className="flex flex-1 flex-col gap-3 p-5">
        <div>
          <h3 className="font-semibold text-[var(--color-navy)]">{title}</h3>
          <p className="mt-1 text-sm text-[var(--color-ink-secondary)]">{description}</p>
        </div>
        <a
          href={downloadHref}
          download
          className="mt-auto inline-flex items-center justify-center gap-2 rounded-md bg-[var(--color-navy)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-navy-light)]"
        >
          Download .xlsx
        </a>
      </div>
    </div>
  );
}
