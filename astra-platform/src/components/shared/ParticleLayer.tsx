'use client';

import React, { useEffect, useRef } from 'react';
import { useAstraStore } from '@/lib/store';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  alpha: number;
  alphaSpeed: number;
}

export function ParticleLayer() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { qualityState } = useAstraStore();

  useEffect(() => {
    if (qualityState === 'low') return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    // Max 200 particles for high quality, 60 for medium quality
    const maxParticles = qualityState === 'high' ? 200 : 60;
    const particles: Particle[] = [];

    // Initialize particles
    for (let i = 0; i < maxParticles; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.12, // slow movement
        vy: (Math.random() - 0.5) * 0.12,
        size: Math.random() * 1.2 + 0.4, // very small
        alpha: Math.random() * 0.6 + 0.1, // sparse/transparent
        alphaSpeed: (Math.random() * 0.005 + 0.002) * (Math.random() > 0.5 ? 1 : -1),
      });
    }

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);

    const animate = () => {
      ctx.clearRect(0, 0, width, height);

      // Draw and update particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        // Draw particle (soft glow/blurred circular dust)
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(110, 168, 254, ${p.alpha})`; // subtle light blue star color
        ctx.fill();

        // Update positions
        p.x += p.vx;
        p.y += p.vy;

        // Wrap around boundaries
        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        // Animate slow twinkle/fade effect
        p.alpha += p.alphaSpeed;
        if (p.alpha <= 0.05 || p.alpha >= 0.7) {
          p.alphaSpeed = -p.alphaSpeed;
        }
      }

      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, [qualityState]);

  if (qualityState === 'low') {
    return null;
  }

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-0"
      style={{ mixBlendMode: 'screen' }}
    />
  );
}
