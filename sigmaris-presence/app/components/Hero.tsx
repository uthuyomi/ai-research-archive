// app/components/Hero.tsx
import Container from "./Container";

export default function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-zinc-800/80">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(34,211,238,0.18),_transparent_60%),radial-gradient(circle_at_bottom,_rgba(59,130,246,0.14),_transparent_55%)]" />
      <Container className="relative py-20 md:py-28 lg:py-32">
        <p className="text-xs font-semibold tracking-[0.25em] uppercase text-zinc-400 mb-4">
          AI PERSONAS × ROBOTICS
        </p>
        <h1 className="text-4xl md:text-5xl lg:text-6xl font-semibold tracking-tight mb-6">
          AI that doesn&apos;t just respond
          <span className="block text-cyan-300">— it exists.</span>
        </h1>
        <p className="max-w-2xl text-sm md:text-base text-zinc-300/80 mb-8 leading-relaxed">
          The Sigmaris Presence Project explores the next interface for AI: not
          just language, but presence. A long-lived AI persona designed to
          maintain continuity, safety, and psychological comfort — even when it
          eventually gains a body.
        </p>
      </Container>
    </section>
  );
}
