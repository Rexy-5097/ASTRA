'use client';

import React, { useRef, useMemo, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useAstraStore } from '@/lib/store';
import { usePathname } from 'next/navigation';

// ── 1. Starfield Component ──────────────────────────────────────────────
function StarsField({ count = 1000 }: { count?: number }) {
  const pointsRef = useRef<THREE.Points>(null);

  // Generate star positions, twinkle states, and sizes
  const [positions, twinkleData, sizes, twinklingIndices] = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const sizes = new Float32Array(count);
    
    // twinkleData: speed in x, phase in y, threshold in z (only 2% of stars twinkle)
    const twinkle = new Float32Array(count * 3);
    const indices: number[] = [];

    for (let i = 0; i < count; i++) {
      // Distribute stars in a large sphere
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const r = 40 + Math.random() * 80; // Distance from camera

      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = -r * Math.cos(phi); // Position behind scene

      // Star size: tiny, between 0.04 and 0.14
      sizes[i] = 0.04 + Math.random() * 0.1;

      // 2% twinkle rate
      const isTwinkling = Math.random() < 0.02;
      if (isTwinkling) {
        twinkle[i * 3] = 0.5 + Math.random() * 1.5; // speed
        twinkle[i * 3 + 1] = Math.random() * Math.PI * 2; // phase
        twinkle[i * 3 + 2] = 1; // flag
        indices.push(i);
      } else {
        twinkle[i * 3] = 0;
        twinkle[i * 3 + 1] = 0;
        twinkle[i * 3 + 2] = 0;
      }
    }
    return [pos, twinkle, sizes, indices];
  }, [count]);

  const geometryRef = useRef<THREE.BufferGeometry>(null);

  useFrame((state) => {
    if (!pointsRef.current) return;

    // Slowly rotate the entire star field
    pointsRef.current.rotation.y = state.clock.getElapsedTime() * 0.002;
    pointsRef.current.rotation.x = state.clock.getElapsedTime() * 0.0007;

    // Animate twinkling stars (loops only over the 2% twinkling stars)
    const time = state.clock.getElapsedTime();
    const geo = pointsRef.current.geometry;
    const sizeAttr = geo.getAttribute('size') as THREE.BufferAttribute;
    
    if (sizeAttr && twinklingIndices.length > 0) {
      for (const i of twinklingIndices) {
        const speed = twinkleData[i * 3];
        const phase = twinkleData[i * 3 + 1];
        // Oscillate size between 30% and 120% of original size
        const baseSize = sizes[i];
        const factor = 0.45 + 0.55 * Math.sin(time * speed + phase);
        sizeAttr.setX(i, baseSize * factor);
      }
      sizeAttr.needsUpdate = true;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry ref={geometryRef}>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
        <bufferAttribute
          attach="attributes-size"
          args={[sizes, 1]}
        />
      </bufferGeometry>
      <pointsMaterial
        color="#D7DEE7"
        size={0.15}
        sizeAttenuation={true}
        transparent={true}
        opacity={0.85}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

// ── 2. Interstellar Black Hole (Gargantua Shader) ─────────────────────────
const BlackHoleShader = {
  uniforms: {
    u_time: { value: 0 },
    u_resolution: { value: new THREE.Vector2() }
  },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform float u_time;
    uniform vec2 u_resolution;
    varying vec2 vUv;

    // Pseudo-random noise functions for plasma accretion flow
    float rand(vec2 n) { 
      return fract(sin(dot(n, vec2(12.9898, 4.1414))) * 43758.5453);
    }

    float noise(vec2 p) {
      vec2 ip = floor(p);
      vec2 u = fract(p);
      u = u * u * (3.0 - 2.0 * u);
      float res = mix(
        mix(rand(ip), rand(ip + vec2(1.0, 0.0)), u.x),
        mix(rand(ip + vec2(0.0, 1.0)), rand(ip + vec2(1.0, 1.0)), u.x), u.y
      );
      return res * res;
    }

    // FBM (Fractional Brownian Motion) for richer accretion dust lanes
    float fbm(vec2 p) {
      float v = 0.0;
      float a = 0.5;
      vec2 shift = vec2(100.0);
      mat2 rot = mat2(cos(0.5), sin(0.5), -sin(0.5), cos(0.5));
      for (int i = 0; i < 3; ++i) {
        v += a * noise(p);
        p = rot * p * 2.0 + shift;
        a *= 0.5;
      }
      return v;
    }

    void main() {
      // Offset center to 36% of X to align with the empty layout space
      vec2 uv = (gl_FragCoord.xy - vec2(0.36 * u_resolution.x, 0.5 * u_resolution.y)) / u_resolution.y;
      
      // Setup Raymarching
      const int MAX_STEPS = 45;
      const float STEP_SIZE = 0.11;
      
      // Camera position: tilted slightly above the disk plane
      vec3 ro = vec3(0.0, 0.38, 3.2);
      
      // Ray direction for this pixel
      vec3 rd = normalize(vec3(uv.x, uv.y, -1.0));
      
      // Tilt camera down slightly
      float pitch = -0.11;
      float cosP = cos(pitch);
      float sinP = sin(pitch);
      float dy = rd.y * cosP - rd.z * sinP;
      float dz = rd.y * sinP + rd.z * cosP;
      rd.y = dy;
      rd.z = dz;
      rd = normalize(rd);
      
      vec3 p = ro;
      vec4 finalCol = vec4(0.0);
      
      // Gravitational lensing strength
      float h2 = 0.22;
      
      for (int i = 0; i < MAX_STEPS; i++) {
        float r2 = dot(p, p);
        float r = sqrt(r2);
        
        // Event Horizon
        if (r < 0.20) {
          finalCol = mix(finalCol, vec4(0.0, 0.0, 0.0, 1.0), 1.0 - finalCol.a);
          break;
        }
        
        // Ray bending towards singularity
        vec3 force = -p * (1.5 * h2 / (r2 * r2 * r));
        rd = normalize(rd + force * STEP_SIZE);
        
        vec3 next_p = p + rd * STEP_SIZE;
        
        // Check intersection with accretion disk plane (Y = 0)
        if (p.y * next_p.y < 0.0) {
          float t = -p.y / rd.y;
          vec3 intersect = p + rd * t;
          float dist = length(intersect.xz);
          
          // Accretion disk boundary
          if (dist > 0.35 && dist < 1.6) {
            float angle = atan(intersect.z, intersect.x);
            
            // Relativistic Doppler Beaming
            // Left side (negative x) rotates towards us -> brighter
            // Right side (positive x) rotates away -> dimmer
            float doppler = 1.0 + 0.35 * (intersect.x / dist);
            float boost = pow(1.0 / doppler, 3.5);
            
            // Dynamic accretion disk texture (FBM + rotation)
            vec2 noiseCoords = vec2(dist * 6.5 - u_time * 1.8, angle * 8.0 - u_time * 1.1);
            float plasma = fbm(noiseCoords) * 0.65 + noise(noiseCoords * 2.5 + u_time) * 0.35;
            
            // Density profile: falls off near event horizon and outer edge
            float density = smoothstep(0.35, 0.50, dist) * smoothstep(1.6, 1.0, dist);
            float diskDensity = plasma * density * boost * 0.85;
            
            // Deep cinematic orange/gold/red color map
            vec3 baseColor = vec3(1.0, 0.36, 0.05); // Hot orange
            vec3 coreGold = vec3(1.0, 0.88, 0.45); // Bright gold
            vec3 edgeRed = vec3(0.42, 0.05, 0.01); // Deep rumble red
            
            // Relativistic color shift based on Doppler factor
            vec3 diskColor;
            if (doppler < 1.0) {
              // Blue-shifted (hotter/whiter)
              diskColor = mix(baseColor, coreGold, (1.0 - doppler) * 1.4);
              diskColor += vec3(0.1, 0.25, 0.6) * (1.0 - doppler) * 0.6; // subtle blue-white shift
            } else {
              // Red-shifted (cooler/darker red)
              diskColor = mix(baseColor, edgeRed, (doppler - 1.0) * 1.2);
            }
            
            // Accumulate layer color and opacity
            float alpha = diskDensity * 0.32;
            vec4 layer = vec4(diskColor * diskDensity, alpha);
            finalCol += layer * (1.0 - finalCol.a);
            
            if (finalCol.a > 0.98) {
              break;
            }
          }
        }
        
        p = next_p;
      }
      
      // If the ray escapes, render background stars warped by lensing
      if (finalCol.a < 1.0) {
        // Starfield noise based on the bent ray direction
        vec3 normalRd = normalize(rd);
        float starNoise = rand(floor(normalRd.xy * 280.0)) * rand(floor(normalRd.yz * 280.0));
        float starVal = smoothstep(0.993, 1.0, starNoise);
        
        // Add star colors to background
        vec3 stars = vec3(starVal * 0.8);
        finalCol.rgb += stars * (1.0 - finalCol.a) * 0.45;
      }
      
      // Corona glow around the event horizon (simulates glowing gas scattering)
      float rScreen = length(uv);
      float corona = 0.003 / (abs(rScreen - 0.19) + 0.008);
      corona = clamp(corona, 0.0, 0.65);
      finalCol.rgb += vec3(1.0, 0.38, 0.05) * corona * (1.0 - finalCol.a) * 0.4;
      
      gl_FragColor = vec4(finalCol.rgb, 1.0);
    }
  `
};

function BlackHoleEffect() {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const { size, viewport } = useThree();

  useFrame((state) => {
    if (materialRef.current) {
      materialRef.current.uniforms.u_time.value = state.clock.getElapsedTime();
      materialRef.current.uniforms.u_resolution.value.set(size.width, size.height);
    }
  });

  return (
    <mesh scale={[viewport.width, viewport.height, 1]}>
      <planeGeometry />
      <shaderMaterial
        ref={materialRef}
        args={[BlackHoleShader]}
        depthWrite={false}
        depthTest={false}
        transparent={true}
      />
    </mesh>
  );
}

// ── 3. Subtle Cosmic Haze ───────────────────────────────────────────────
function VolumetricHaze() {
  return (
    <>
      <fogExp2 attach="fog" args={['#05070B', 0.003]} />
      <ambientLight intensity={0.15} />
    </>
  );
}

// ── 4. Master Backdrop Component ────────────────────────────────────────
export function CosmicBackground() {
  const pathname = usePathname();
  const { qualityState } = useAstraStore();
  const videoRef = useRef<HTMLVideoElement>(null);

  // Programmatically trigger video playback to guarantee autoplay is active
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.play().catch((err) => {
        console.warn("Autoplay block or video load failure: ", err);
      });
    }
  }, [pathname]);

  if (qualityState === 'low') {
    return (
      <div className="fixed inset-0 z-0 bg-[#05070B] pointer-events-none" />
    );
  }

  const isHomepage = pathname === '/';
  const isTargetPage = pathname.startsWith('/target/');
  const opacity = isTargetPage ? 0.35 : isHomepage ? 0.65 : 0.50;

  const videoSrc = useMemo(() => {
    if (pathname === '/') return '/blackhole.mp4';
    if (pathname === '/search') return '/earth.mp4';
    if (pathname === '/analysis') return '/solar-system.mp4';
    if (pathname === '/dataset') return '/star-cluster.mp4';
    if (pathname === '/model') return '/galaxy.mp4';
    if (pathname === '/research') return '/nebula.mp4';
    if (pathname === '/mission-replay') return '/pulsar.mp4';
    if (pathname === '/osint') return '/satellite.mp4';
    if (pathname === '/visualization') return '/space-dust.mp4';
    if (pathname.startsWith('/target/')) return '/space-dust.mp4';
    return '/space-backdrop.mp4';
  }, [pathname]);

  return (
    <div 
      className="fixed inset-0 z-0 pointer-events-none transition-opacity duration-1000 bg-[#05070B] overflow-hidden"
      style={{ opacity }}
    >
      <video
        ref={videoRef}
        key={videoSrc}
        autoPlay
        loop
        muted
        playsInline
        className="absolute inset-0 w-full h-full object-cover scale-[1.03]"
        style={{ filter: 'brightness(0.25) blur(4px) saturate(0.6)' }}
      >
        <source src={videoSrc} type="video/mp4" />
      </video>
      {/* 80% Dark overlay & Vignette */}
      <div className="absolute inset-0 bg-[#05070B]/80 pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-t from-[#05070B] via-transparent to-[#05070B] pointer-events-none" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_30%,#05070B_95%)] pointer-events-none" />
    </div>
  );
}
