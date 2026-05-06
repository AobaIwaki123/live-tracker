import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

const ORB_DEFS = [
  { pos: [-2.5,  1.8, -2] as const, color: 0x7c3aed, r: 1.4 },
  { pos: [ 3.5, -0.8, -1] as const, color: 0xdb2777, r: 1.0 },
  { pos: [ 0.5, -2.8, -4] as const, color: 0x4338ca, r: 1.8 },
  { pos: [-4.0, -1.5, -3] as const, color: 0x9333ea, r: 0.8 },
]

const PHASE_OFFSETS = [0, Math.PI / 2, Math.PI, (3 * Math.PI) / 2]

function Orb({ def, phaseOffset }: { def: typeof ORB_DEFS[number], phaseOffset: number }) {
  const hazeRef = useRef<THREE.Mesh>(null)
  const coreRef = useRef<THREE.Mesh>(null)

  useFrame(({ clock }) => {
    const elapsed = clock.getElapsedTime()
    if (hazeRef.current) {
      const s = 1.0 + Math.sin(elapsed * 0.8 + phaseOffset) * 0.08
      hazeRef.current.scale.setScalar(s)
    }
    if (coreRef.current) {
      const s = 1.0 + Math.sin(elapsed * 1.2 + phaseOffset) * 0.12
      coreRef.current.scale.setScalar(s)
    }
  })

  return (
    <group position={def.pos}>
      {/* Haze */}
      <mesh ref={hazeRef}>
        <sphereGeometry args={[def.r, 32, 32]} />
        <meshBasicMaterial color={def.color} transparent opacity={0.12} />
      </mesh>
      {/* Core */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[def.r * 0.28, 16, 16]} />
        <meshBasicMaterial color={def.color} transparent opacity={0.7} />
      </mesh>
    </group>
  )
}

export default function Orbs() {
  return (
    <>
      {ORB_DEFS.map((def, i) => (
        <Orb key={i} def={def} phaseOffset={PHASE_OFFSETS[i]} />
      ))}
    </>
  )
}
