'use client';

import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Line, Html } from '@react-three/drei';
import { useRef, useMemo, useState, useEffect } from 'react';
import * as THREE from 'three';
import { useStars } from '@/lib/hooks';
import { useAstraStore } from '@/lib/store';
import { CLASS_COLORS } from '@/lib/utils';
import type { Star } from '@/lib/types';

// Convert Right Ascension (RA) and Declination (Dec) to Cartesian 3D coordinates
function raDecToVector3(ra: number, dec: number, radius = 25): [number, number, number] {
  const raRad = (ra * Math.PI) / 180;
  const decRad = (dec * Math.PI) / 180;

  // Spherical to Cartesian projection
  const x = radius * Math.cos(decRad) * Math.cos(raRad);
  const y = radius * Math.cos(decRad) * Math.sin(raRad);
  const z = radius * Math.sin(decRad);

  return [x, y, z];
}

function GridLines({ radius = 25 }: { radius?: number }) {
  const decRings = useMemo(() => {
    const rings = [];
    const decs = [-60, -30, 0, 30, 60];
    for (const dec of decs) {
      const decRad = (dec * Math.PI) / 180;
      const ringRadius = radius * Math.cos(decRad);
      const ringZ = radius * Math.sin(decRad);
      const points = [];
      for (let i = 0; i <= 64; i++) {
        const theta = (i / 64) * Math.PI * 2;
        points.push(new THREE.Vector3(ringRadius * Math.cos(theta), ringRadius * Math.sin(theta), ringZ));
      }
      rings.push(points);
    }
    return rings;
  }, [radius]);

  const raMeridians = useMemo(() => {
    const meridians = [];
    const ras = [0, 45, 90, 135, 180, 225, 270, 315];
    for (const ra of ras) {
      const raRad = (ra * Math.PI) / 180;
      const points = [];
      for (let i = -32; i <= 32; i++) {
        const decRad = (i / 32) * (Math.PI / 2);
        const x = radius * Math.cos(decRad) * Math.cos(raRad);
        const y = radius * Math.cos(decRad) * Math.sin(raRad);
        const z = radius * Math.sin(decRad);
        points.push(new THREE.Vector3(x, y, z));
      }
      meridians.push(points);
    }
    return meridians;
  }, [radius]);

  return (
    <group>
      {decRings.map((ring, idx) => (
        <Line key={`dec-${idx}`} points={ring} color="#1A2430" lineWidth={0.8} />
      ))}
      {raMeridians.map((meridian, idx) => (
        <Line key={`ra-${idx}`} points={meridian} color="#1A2430" lineWidth={0.8} />
      ))}
    </group>
  );
}

function StarGlobeScene({ stars }: { stars: Star[] }) {
  const { selectedStar, setSelectedStar } = useAstraStore();
  const [hoveredStar, setHoveredStar] = useState<Star | null>(null);
  const groupRef = useRef<THREE.Group>(null);
  const controlsRef = useRef<any>(null);
  
  // Ref for pulsing selector ring
  const pulseRef = useRef<THREE.Mesh>(null);

  // Slow rotation when no star is selected
  useFrame((state, delta) => {
    if (groupRef.current && !selectedStar) {
      groupRef.current.rotation.z += delta * 0.015;
    }
  });

  // Soft camera interpolation to zoom in on selected star coordinates
  useFrame((state) => {
    if (selectedStar && controlsRef.current) {
      const pos = raDecToVector3(selectedStar.ra, selectedStar.dec, 25);
      const targetVec = new THREE.Vector3(...pos);
      
      // Interpolate controls target focus point
      controlsRef.current.target.lerp(targetVec, 0.05);

      // Compute camera position (offset out to radius of 36)
      const camTargetVec = targetVec.clone().normalize().multiplyScalar(36);
      state.camera.position.lerp(camTargetVec, 0.05);
      
      controlsRef.current.update();
    }

    // Animate selected glow pulsing
    if (pulseRef.current) {
      const time = state.clock.getElapsedTime();
      const scale = 1.0 + 0.15 * Math.sin(time * 6);
      pulseRef.current.scale.set(scale, scale, scale);
    }
  });

  const starPoints = useMemo(() => {
    return stars.map((s) => {
      const pos = raDecToVector3(s.ra, s.dec, 25);
      const color = CLASS_COLORS[s.astra_class] || '#6B7280';
      return { star: s, position: pos, color };
    });
  }, [stars]);

  const selectIndicator = useMemo(() => {
    if (!selectedStar) return null;
    return raDecToVector3(selectedStar.ra, selectedStar.dec, 25.05);
  }, [selectedStar]);

  return (
    <>
      <OrbitControls 
        ref={controlsRef}
        enableDamping 
        dampingFactor={0.05} 
        maxDistance={60} 
        minDistance={10} 
      />

      <group ref={groupRef}>
        {/* Reference grid overlay */}
        <GridLines radius={25} />

        {/* Axis markers */}
        <Line points={[new THREE.Vector3(-28, 0, 0), new THREE.Vector3(28, 0, 0)]} color="#1A2430" lineWidth={0.5} />
        <Line points={[new THREE.Vector3(0, -28, 0), new THREE.Vector3(0, 28, 0)]} color="#1A2430" lineWidth={0.5} />
        <Line points={[new THREE.Vector3(0, 0, -28), new THREE.Vector3(0, 0, 28)]} color="#1A2430" lineWidth={0.5} />

        {/* Star points */}
        {starPoints.map(({ star, position, color }) => {
          const isSelected = selectedStar?.tic_id === star.tic_id;
          const isHovered = hoveredStar?.tic_id === star.tic_id;
          const size = isSelected ? 0.35 : isHovered ? 0.25 : 0.12;

          return (
            <mesh
              key={star.tic_id}
              position={position}
              onClick={(e) => {
                e.stopPropagation();
                setSelectedStar(star);
              }}
              onPointerOver={(e) => {
                e.stopPropagation();
                setHoveredStar(star);
              }}
              onPointerOut={(e) => {
                e.stopPropagation();
                if (hoveredStar?.tic_id === star.tic_id) setHoveredStar(null);
              }}
            >
              <sphereGeometry args={[size, 8, 8]} />
              <meshBasicMaterial color={color} />
              
              {isHovered && (
                <Html distanceFactor={15}>
                  <div className="bg-[#0C1118]/95 border border-[#1A2430] text-[10px] text-[#D7DEE7] px-2 py-1.5 rounded shadow-lg pointer-events-none font-mono whitespace-nowrap z-50">
                    <p className="font-bold text-[#6EA8FE]">TIC {star.tic_id}</p>
                    <p className="text-[9px] text-[#8B97A7] mt-0.5">{star.astra_class.toUpperCase()}</p>
                    <p className="text-[9px] text-[#5A6878]">Period: {star.period.toFixed(4)} d</p>
                  </div>
                </Html>
              )}
            </mesh>
          );
        })}

        {/* Selected target pulsing halo */}
        {selectIndicator && (
          <mesh position={selectIndicator} ref={pulseRef}>
            <ringGeometry args={[0.5, 0.7, 32]} />
            <meshBasicMaterial 
              color="#6EA8FE" 
              side={THREE.DoubleSide} 
              transparent 
              opacity={0.7} 
            />
          </mesh>
        )}
      </group>
    </>
  );
}

export default function StarGlobe({ stars }: { stars: Star[] }) {
  const { selectedStar } = useAstraStore();

  return (
    <div className="w-full h-full relative border border-white/5 rounded overflow-hidden" style={{ minHeight: '380px' }}>
      <Canvas camera={{ position: [0, 0, 42], fov: 60 }} gl={{ antialias: true }}>
        <color attach="background" args={['#05070B']} />
        <ambientLight intensity={1.5} />
        <StarGlobeScene stars={stars} />
      </Canvas>
      <div className="absolute bottom-3 left-3 bg-[#0C1118]/85 border border-white/5 p-2.5 rounded text-[10px] font-mono text-[#8B97A7] pointer-events-none select-none">
        <p className="text-[#6EA8FE] font-bold">CELESTIAL GLOBE</p>
        <p className="mt-0.5">Left-Click + Drag: Rotate</p>
        <p>Scroll: Zoom</p>
        {selectedStar && (
          <p className="text-[#56D364] mt-1">LOCKED ON TIC {selectedStar.tic_id}</p>
        )}
      </div>
    </div>
  );
}
