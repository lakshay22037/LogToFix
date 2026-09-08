export default function AmbientBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden bg-canvas">
      {/* ambient glow blobs — kept below blur-3xl (Tailwind's max) so peak intensity stays visible */}
      <div className="absolute -top-24 left-1/2 h-[500px] w-[700px] -translate-x-1/2 rounded-full bg-brand-500 opacity-30 blur-3xl" />
      <div className="absolute top-1/4 -right-20 h-[350px] w-[350px] rounded-full bg-fuchsia-500 opacity-20 blur-3xl" />
      <div className="absolute bottom-0 -left-16 h-[300px] w-[300px] rounded-full bg-brand-400 opacity-20 blur-3xl" />

      {/* dot grid, on top of the glow so it reads clearly */}
      <div
        className="absolute inset-0 opacity-40"
        style={{
          backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.09) 1px, transparent 1px)",
          backgroundSize: "28px 28px",
        }}
      />
    </div>
  );
}
