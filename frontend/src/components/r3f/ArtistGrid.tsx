import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { useScroll } from '@react-three/drei'
import * as THREE from 'three'
import { useArtists } from '@/hooks/useArtists'
import ArtistCard from './ArtistCard'

export default function ArtistGrid() {
  const { data: artists } = useArtists()
  const groupRef = useRef<THREE.Group>(null)
  const scroll = useScroll()

  useFrame(() => {
    if (groupRef.current) {
      // scroll.offset goes from 0 to 1 as you scroll down.
      // We want to move the grid UP (positive Y) as you scroll down.
      // Adjust the multiplier (e.g., 10) based on how many artists there are to ensure you can reach the bottom.
      const scrollY = scroll.offset * 15
      groupRef.current.position.y = -1.5 + scrollY
    }
  })

  if (!artists) return null

  // Calculate positions for a grid layout in 3D
  // 3 columns, spacing of 4 units X, 3.5 units Y
  const cols = 3
  const spacingX = 4
  const spacingY = 3.5
  
  // Center the grid by applying an offset based on total columns
  const offsetX = -((cols - 1) * spacingX) / 2

  return (
    <group ref={groupRef} position={[0, -1.5, 0]}>
      {artists.map((artist, index) => {
        const row = Math.floor(index / cols)
        const col = index % cols
        
        const x = offsetX + col * spacingX
        const y = -(row * spacingY)
        const z = 0

        return (
          <ArtistCard
            key={artist.name}
            artist={artist}
            position={[x, y, z]}
          />
        )
      })}
    </group>
  )
}
