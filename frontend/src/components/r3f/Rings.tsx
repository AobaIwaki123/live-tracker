import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

const RING_DEFS = [
  { pos: [ 2.2,  0.3, -0.5] as const, rx: 1.1, ry:  0.3, r: 1.9, tube: 0.04,  color: 0xa855f7, op: 0.35, rzSpeed:  0.003 },
  { pos: [-2.8, -0.4, -1  ] as const, rx: 0.8, ry: -0.5, r: 1.4, tube: 0.03,  color: 0xec4899, op: 0.28, rzSpeed: -0.004 },
  { pos: [ 0.5,  2.0, -2  ] as const, rx: 1.5, ry:  0.8, r: 2.2, tube: 0.035, color: 0x818cf8, op: 0.20, rzSpeed:  0.002 },
]

function Ring({ def }: { def: typeof RING_DEFS[number] }) {
  const meshRef = useRef<THREE.Mesh>(null)

  useFrame((_, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.z += (def.rzSpeed * 60) * delta
    }
  })

  return (
    <mesh ref={meshRef} position={def.pos} rotation={[def.rx, def.ry, 0]}>
      <torusGeometry args={[def.r, def.tube, 16, 100]} />
      <meshBasicMaterial color={def.color} transparent opacity={def.op} />
    </mesh>
  )
}

export default function Rings() {
  return (
    <>
      {RING_DEFS.map((def, i) => (
        <Ring key={i} def={def} />
      ))}
    </>
  )
}
