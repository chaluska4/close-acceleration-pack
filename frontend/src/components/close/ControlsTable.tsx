import { Badge } from "../ui/Badge";
import { controlStatusStyle } from "../../lib/status";
import type { ControlRow } from "../../lib/types";

const CATEGORY_CLASS: Record<ControlRow["category"], string> = {
  Completeness: "bg-slate-100 text-slate-600",
  Accuracy: "bg-[var(--color-accent-light)] text-[var(--color-accent)]",
  Authorization: "bg-amber-50 text-amber-700",
};

export function ControlsTable({ controls }: { controls: ControlRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[780px] text-sm">
        <caption className="sr-only">
          Controls log with category, process area, status, evidence retained, and follow-up action
        </caption>
        <thead>
          <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wide text-[var(--color-ink-muted)]">
            <th scope="col" className="py-2 pr-4 font-semibold">
              Control
            </th>
            <th scope="col" className="py-2 pr-4 font-semibold">
              Category
            </th>
            <th scope="col" className="py-2 pr-4 font-semibold">
              Process Area
            </th>
            <th scope="col" className="py-2 pr-4 font-semibold">
              Status
            </th>
            <th scope="col" className="py-2 pr-4 font-semibold">
              Evidence Retained
            </th>
            <th scope="col" className="py-2 pl-0 font-semibold">
              Follow-up Action
            </th>
          </tr>
        </thead>
        <tbody>
          {controls.map((control) => {
            const style = controlStatusStyle(control.status);
            return (
              <tr key={control.control_id} className="border-b border-[var(--color-border)] align-top last:border-0">
                <th scope="row" className="py-3 pr-4 text-left font-medium text-[var(--color-navy)]">
                  {control.control_id}
                </th>
                <td className="py-3 pr-4">
                  <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${CATEGORY_CLASS[control.category]}`}>
                    {control.category}
                  </span>
                </td>
                <td className="py-3 pr-4 text-[var(--color-ink-secondary)]">{control.process_area}</td>
                <td className="py-3 pr-4">
                  <Badge className={style.badgeClass} dotClassName={style.dotClass}>
                    {style.label}
                  </Badge>
                </td>
                <td className="max-w-xs py-3 pr-4 text-xs text-[var(--color-ink-secondary)]">{control.evidence_ref}</td>
                <td className="max-w-xs py-3 pl-0 text-xs text-[var(--color-ink-secondary)]">
                  {control.exception_remediation}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
