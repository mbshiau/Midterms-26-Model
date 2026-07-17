import { useEffect, useRef } from "react";

export interface GooeyTextSegment {
  text: string;
  color?: string;
}

// A plain string renders in the default (--text-primary) color; an array of
// segments lets one phrase mix colors (e.g. a blue "Dems" and a red "GOP"
// half of the same line).
export type GooeyTextEntry = string | GooeyTextSegment[];

interface GooeyTextProps {
  texts: GooeyTextEntry[];
  morphTime?: number;
  cooldownTime?: number;
  className?: string;
  textClassName?: string;
}

function cn(...classes: (string | undefined | false)[]): string {
  return classes.filter(Boolean).join(" ");
}

function renderEntry(el: HTMLSpanElement, entry: GooeyTextEntry) {
  el.replaceChildren();
  if (typeof entry === "string") {
    el.textContent = entry;
    return;
  }
  for (const segment of entry) {
    const span = document.createElement("span");
    span.textContent = segment.text;
    if (segment.color) span.style.color = segment.color;
    el.appendChild(span);
  }
}

// Ported from a shadcn-style "gooey text morphing" component. This project
// isn't a shadcn/Next.js app (no `@/lib/utils` cn helper, no `--foreground`
// token, no "use client" runtime) -- adapted to plain Tailwind + this app's
// own CSS custom properties instead of pulling in shadcn's scaffolding for
// one component.
export function GooeyText({
  texts,
  morphTime = 1,
  cooldownTime = 0.25,
  className,
  textClassName,
}: GooeyTextProps) {
  const text1Ref = useRef<HTMLSpanElement>(null);
  const text2Ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    let textIndex = texts.length - 1;
    let time = new Date();
    let morph = 0;
    let cooldown = cooldownTime;
    let frame: number;

    const setMorph = (fraction: number) => {
      if (!text1Ref.current || !text2Ref.current) return;
      text2Ref.current.style.filter = `blur(${Math.min(8 / fraction - 8, 100)}px)`;
      text2Ref.current.style.opacity = `${Math.pow(fraction, 0.4) * 100}%`;

      fraction = 1 - fraction;
      text1Ref.current.style.filter = `blur(${Math.min(8 / fraction - 8, 100)}px)`;
      text1Ref.current.style.opacity = `${Math.pow(fraction, 0.4) * 100}%`;
    };

    const doCooldown = () => {
      morph = 0;
      if (!text1Ref.current || !text2Ref.current) return;
      text2Ref.current.style.filter = "";
      text2Ref.current.style.opacity = "100%";
      text1Ref.current.style.filter = "";
      text1Ref.current.style.opacity = "0%";
    };

    const doMorph = () => {
      morph -= cooldown;
      cooldown = 0;
      let fraction = morph / morphTime;

      if (fraction > 1) {
        cooldown = cooldownTime;
        fraction = 1;
      }

      setMorph(fraction);
    };

    function animate() {
      frame = requestAnimationFrame(animate);
      const newTime = new Date();
      const shouldIncrementIndex = cooldown > 0;
      const dt = (newTime.getTime() - time.getTime()) / 1000;
      time = newTime;

      cooldown -= dt;

      if (cooldown <= 0) {
        if (shouldIncrementIndex) {
          textIndex = (textIndex + 1) % texts.length;
          if (text1Ref.current && text2Ref.current) {
            renderEntry(text1Ref.current, texts[textIndex % texts.length]);
            renderEntry(text2Ref.current, texts[(textIndex + 1) % texts.length]);
          }
        }
        doMorph();
      } else {
        doCooldown();
      }
    }

    // Populate both spans immediately -- otherwise they stay empty (a
    // blank header) until the *first* cooldown elapses, which is glaring
    // at a multi-second cooldownTime rather than the demo's default 0.25s.
    if (text1Ref.current && text2Ref.current) {
      renderEntry(text1Ref.current, texts[textIndex % texts.length]);
      renderEntry(text2Ref.current, texts[(textIndex + 1) % texts.length]);
    }
    doCooldown();
    animate();
    return () => cancelAnimationFrame(frame);
  }, [texts, morphTime, cooldownTime]);

  return (
    <div className={cn("relative", className)}>
      <svg className="absolute h-0 w-0" aria-hidden="true" focusable="false">
        <defs>
          <filter id="gooey-text-threshold">
            <feColorMatrix
              in="SourceGraphic"
              type="matrix"
              values="1 0 0 0 0
                      0 1 0 0 0
                      0 0 1 0 0
                      0 0 0 255 -140"
            />
          </filter>
        </defs>
      </svg>

      <div
        className="flex items-center justify-center"
        style={{ filter: "url(#gooey-text-threshold)" }}
      >
        <span
          ref={text1Ref}
          className={cn("absolute inline-block select-none text-center", textClassName)}
          style={{ color: "var(--text-primary)" }}
        />
        <span
          ref={text2Ref}
          className={cn("absolute inline-block select-none text-center", textClassName)}
          style={{ color: "var(--text-primary)" }}
        />
      </div>
    </div>
  );
}
