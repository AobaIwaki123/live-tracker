import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

const PARTICLE_COUNT = 500

function generateParticles() {
  const pos = new Float32Array(PARTICLE_COUNT * 3)
  const col = new Float32Array(PARTICLE_COUNT * 3)
  const siz = new Float32Array(PARTICLE_COUNT)

  const palette = [
    new THREE.Color(0xa855f7),
    new THREE.Color(0xec4899),
    new THREE.Color(0xffffff),
    new THREE.Color(0x818cf8),
    new THREE.Color(0xf0abfc),
    new THREE.Color(0x60a5fa),
  ]

  for (let i = 0; i < PARTICLE_COUNT; i++) {
    pos[i * 3]     = (Math.random() - 0.5) * 22
    pos[i * 3 + 1] = (Math.random() - 0.5) * 12
    pos[i * 3 + 2] = (Math.random() - 0.5) * 10 - 3
    
    const c = palette[Math.floor(Math.random() * palette.length)]
    col[i * 3]     = c.r
    col[i * 3 + 1] = c.g
    col[i * 3 + 2] = c.b
    
    siz[i] = Math.random() * 3 + 1
  }
  return { positions: pos, colors: col, sizes: siz }
}

export default function Particles() {
  const pointsRef = useRef<THREE.Points>(null)
  
  // Empty dependency array ensures it's only generated once,
  // and having it outside the useMemo callback body avoids purity lint errors.
  const { positions, colors, sizes } = useMemo(() => generateParticles(), [])

  useFrame((_, delta) => {
    if (!pointsRef.current) return
    const posArr = pointsRef.current.geometry.attributes.position.array as Float32Array
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      posArr[i * 3 + 2] -= 0.12 * delta
      if (posArr[i * 3 + 2] < -8) posArr[i * 3 + 2] = 2
    }
    pointsRef.current.geometry.attributes.position.needsUpdate = true
  })

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={PARTICLE_COUNT} args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" count={PARTICLE_COUNT} args={[colors, 3]} />
        <bufferAttribute attach="attributes-size" count={PARTICLE_COUNT} args={[sizes, 1]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.07}
        vertexColors
        transparent
        opacity={0.85}
        sizeAttenuation
      />
    </points>
  )
}
