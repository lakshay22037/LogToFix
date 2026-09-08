export default function Logo({ className = "" }) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-brand-400 to-brand-600 text-sm font-bold text-white shadow-lg shadow-brand-600/20">
        L
      </div>
      <span className="font-sans text-[15px] font-semibold tracking-tight text-white">
        Log<span className="text-brand-400">→</span>Fix
      </span>
    </div>
  );
}
