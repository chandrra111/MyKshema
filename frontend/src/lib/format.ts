export function fmtDate(d?: string | null, opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" }) {
  if (!d) return "—";
  const dt = new Date(d.length === 10 ? `${d}T00:00:00` : d);
  if (isNaN(dt.getTime())) return d;
  return dt.toLocaleDateString("en-IN", opts);
}

export function fmtDateTime(d?: string | null) {
  if (!d) return "—";
  const dt = new Date(d);
  return dt.toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function relTime(d: string) {
  const diff = new Date(d).getTime() - Date.now();
  const abs = Math.abs(diff);
  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  if (abs < 3600e3) return rtf.format(Math.round(diff / 60e3), "minute");
  if (abs < 86400e3) return rtf.format(Math.round(diff / 3600e3), "hour");
  return rtf.format(Math.round(diff / 86400e3), "day");
}

export function fmtBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export const CATEGORY_LABEL: Record<string, string> = {
  prescription: "Prescription",
  blood_report: "Blood report",
  diagnostic_report: "Diagnostic report",
  xray: "X-ray",
  mri: "MRI",
  ct_scan: "CT scan",
  discharge_summary: "Discharge summary",
  consultation_note: "Consultation note",
  vaccination_record: "Vaccination record",
  other: "Other",
};

export const STATUS_LABEL: Record<string, string> = {
  active: "Prescribed · current",
  patient_reported: "Patient-reported",
  discontinued: "Discontinued",
  completed: "Completed",
  proposed: "Proposed (demo)",
};

export function cx(...c: (string | false | null | undefined)[]) {
  return c.filter(Boolean).join(" ");
}

export function initials(name: string) {
  return name.replace(/^Dr\.?\s+/, "").split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
}
