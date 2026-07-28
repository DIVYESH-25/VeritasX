import React, { useEffect, useRef, useState } from 'react';
import { useCursorState } from '@/hooks/useCursorState';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  alpha: number;
  life: number;
  maxLife: number;
  color: string;
}

export const CyberCursor: React.FC = () => {
  const { cursorType } = useCursorState();
  const cursorDotRef = useRef<HTMLDivElement>(null);
  const cursorRingRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const posRef = useRef({ x: -100, y: -100 });
  const ringPosRef = useRef({ x: -100, y: -100 });
  const particlesRef = useRef<Particle[]>([]);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Activate custom cursor on fine pointers
    const isTouch = window.matchMedia('(pointer: coarse)').matches;
    if (isTouch) return;

    const cyanColor = '#00f3ff';

    const onMouseDown = (e: MouseEvent) => {
      // Small compact particle burst in signature cyan matching the cursor
      if (canvasRef.current) {
        const numParticles = 12;
        for (let i = 0; i < numParticles; i++) {
          const angle = (i / numParticles) * Math.PI * 2 + (Math.random() - 0.5) * 0.3;
          const speed = Math.random() * 2 + 1;
          particlesRef.current.push({
            x: e.clientX,
            y: e.clientY,
            vx: Math.cos(angle) * speed,
            vy: Math.sin(angle) * speed,
            size: Math.random() * 2 + 1,
            alpha: 1,
            life: 0,
            maxLife: Math.random() * 10 + 10,
            color: cyanColor,
          });
        }
      }
    };

    const onMouseMove = (e: MouseEvent) => {
      posRef.current = { x: e.clientX, y: e.clientY };
      if (!isVisible) setIsVisible(true);

      // Spawn subtle trail particle in signature cyan on mouse move
      if (canvasRef.current && Math.random() < 0.5) {
        particlesRef.current.push({
          x: e.clientX,
          y: e.clientY,
          vx: (Math.random() - 0.5) * 1.2,
          vy: (Math.random() - 0.5) * 1.2 - 0.3,
          size: Math.random() * 2 + 1,
          alpha: 0.7,
          life: 0,
          maxLife: Math.random() * 20 + 10,
          color: cyanColor,
        });
      }
    };

    const onMouseLeave = () => setIsVisible(false);
    const onMouseEnter = () => setIsVisible(true);

    window.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseleave', onMouseLeave);
    document.addEventListener('mouseenter', onMouseEnter);

    // Canvas particle loop & smooth cursor lerp loop
    let animId: number;
    const render = () => {
      // Smooth lerp for outer reticle ring
      ringPosRef.current.x += (posRef.current.x - ringPosRef.current.x) * 0.25;
      ringPosRef.current.y += (posRef.current.y - ringPosRef.current.y) * 0.25;

      if (cursorDotRef.current) {
        cursorDotRef.current.style.transform = `translate3d(${posRef.current.x}px, ${posRef.current.y}px, 0) translate(-50%, -50%)`;
      }
      if (cursorRingRef.current) {
        cursorRingRef.current.style.transform = `translate3d(${ringPosRef.current.x}px, ${ringPosRef.current.y}px, 0) translate(-50%, -50%)`;
      }

      // Draw particle trail canvas
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          const updatedParticles: Particle[] = [];

          for (let i = 0; i < particlesRef.current.length; i++) {
            const p = particlesRef.current[i];
            p.life += 1;
            p.x += p.vx;
            p.y += p.vy;
            p.vx *= 0.93; // Velocity drag
            p.vy *= 0.93;
            p.alpha = 1 - p.life / p.maxLife;

            if (p.life < p.maxLife && p.alpha > 0) {
              ctx.save();
              ctx.globalAlpha = Math.max(0, p.alpha);
              ctx.shadowColor = cyanColor;
              ctx.shadowBlur = 6;
              ctx.fillStyle = cyanColor;
              ctx.beginPath();
              ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
              ctx.fill();
              ctx.restore();
              updatedParticles.push(p);
            }
          }
          particlesRef.current = updatedParticles;
        }
      }

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    // Resize Canvas handler
    const handleResize = () => {
      if (canvasRef.current) {
        canvasRef.current.width = window.innerWidth;
        canvasRef.current.height = window.innerHeight;
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseleave', onMouseLeave);
      document.removeEventListener('mouseenter', onMouseEnter);
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animId);
    };
  }, [isVisible]);

  if (!isVisible) return null;

  // Sleek, professional, circular reticle states without awkward text tags or diamond rotation
  const getRingClasses = () => {
    switch (cursorType) {
      case 'button':
        return 'w-12 h-12 border-2 border-cyan-400 bg-cyan-400/10 shadow-[0_0_20px_rgba(0,243,255,0.5)] rounded-full scale-110';
      case 'card':
        return 'w-16 h-16 border border-cyan-400/80 bg-cyan-400/10 shadow-[0_0_25px_rgba(0,243,255,0.4)] rounded-full';
      case 'image':
      case 'scan':
        return 'w-20 h-20 border-2 border-cyan-400 border-dashed bg-cyan-400/5 shadow-[0_0_25px_rgba(0,243,255,0.5)] rounded-full';
      case 'text':
        return 'w-5 h-8 border-l-2 border-r-2 border-cyan-400 bg-transparent rounded-none';
      default:
        return 'w-10 h-10 border border-cyan-400/60 shadow-[0_0_15px_rgba(0,243,255,0.3)] rounded-full';
    }
  };

  return (
    <div className="pointer-events-none fixed inset-0 z-50 overflow-hidden">
      {/* Particle Trail Canvas */}
      <canvas
        ref={canvasRef}
        className="pointer-events-none absolute inset-0 z-40 opacity-80"
      />

      {/* Core Glowing Dot */}
      <div
        ref={cursorDotRef}
        className="fixed left-0 top-0 z-50 transition-transform duration-75 ease-out"
      >
        <div className="relative flex items-center justify-center">
          <div className="h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_10px_#00f3ff,0_0_20px_#00f3ff]" />
        </div>
      </div>

      {/* Outer Sleek Reticle Ring */}
      <div
        ref={cursorRingRef}
        className="fixed left-0 top-0 z-50 transition-all duration-300 ease-out"
      >
        <div
          className={`relative flex items-center justify-center transition-all duration-300 ${getRingClasses()}`}
        >
          {/* Subtle reticle ticks for image scan state */}
          {(cursorType === 'image' || cursorType === 'scan') && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="h-full w-[1px] bg-cyan-400/30" />
              <div className="absolute h-[1px] w-full bg-cyan-400/30" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
