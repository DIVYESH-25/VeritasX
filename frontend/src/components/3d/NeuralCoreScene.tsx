import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

// Ultra-clean slow moving signature cyan particles background (#00E5FF)
const SlowMovingSpaceParticles: React.FC<{ count?: number }> = ({ count = 1600 }) => {
  const pointsRef = useRef<THREE.Points>(null);

  // Generate 3D particles in 100% signature #00E5FF cyan
  const [positions, colors] = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const col = new Float32Array(count * 3);
    const cyanColor = new THREE.Color('#00E5FF');

    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 34;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 22;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 16;

      col[i * 3] = cyanColor.r;
      col[i * 3 + 1] = cyanColor.g;
      col[i * 3 + 2] = cyanColor.b;
    }
    return [pos, col];
  }, [count]);

  useFrame((state, delta) => {
    if (pointsRef.current) {
      // Slow moving ambient particle drift
      pointsRef.current.rotation.y += delta * 0.006;
      pointsRef.current.rotation.x += delta * 0.003;

      // Gentle cursor tilt reactivity
      const targetX = state.pointer.x * 0.35;
      const targetY = state.pointer.y * 0.35;
      pointsRef.current.rotation.y += (targetX - pointsRef.current.rotation.y) * 0.03;
      pointsRef.current.rotation.x += (-targetY - pointsRef.current.rotation.x) * 0.03;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.036}
        vertexColors
        transparent
        opacity={0.75}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
};

export const NeuralCoreScene: React.FC = () => {
  return (
    <div className="absolute inset-0 w-full h-full pointer-events-none overflow-hidden flex items-center justify-center">
      <Canvas
        camera={{ position: [0, 0, 8], fov: 55 }}
        className="absolute inset-0 w-full h-full"
      >
        <ambientLight intensity={0.8} />
        <pointLight position={[0, 0, 5]} intensity={1.5} color="#00E5FF" />

        <SlowMovingSpaceParticles count={1600} />
      </Canvas>
    </div>
  );
};
