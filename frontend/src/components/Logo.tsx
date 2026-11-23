export function LogoMark({ className = "h-9 w-9" }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={className} aria-hidden="true">
      <defs>
        <linearGradient id="mk-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#2DC7B1" />
          <stop offset="1" stopColor="#0B897C" />
        </linearGradient>
      </defs>
      <rect width="40" height="40" rx="11" fill="#0F2344" />
      <path d="M20 31s-9.5-5.6-9.5-12.4A5.3 5.3 0 0 1 20 15.4a5.3 5.3 0 0 1 9.5 3.2C29.5 25.4 20 31 20 31Z" fill="url(#mk-g)" />
      <path d="M12.5 21h4l1.6-3 2.6 6 1.8-3.6h5" fill="none" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Logo({ light = false, tagline = false }: { light?: boolean; tagline?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <LogoMark />
      <div className="leading-tight">
        <p className={`text-lg font-semibold tracking-tight ${light ? "text-white" : "text-navy-900"}`}>
          My<span className="text-teal-500">Kshema</span>
        </p>
        {tagline && <p className={`text-[11px] ${light ? "text-navy-200" : "text-slate-500"}`}>Your Health. Your History. Your Well-being.</p>}
      </div>
    </div>
  );
}
