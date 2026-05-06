import { useRef, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import { Image, Text } from '@react-three/drei'
import * as THREE from 'three'
import { useNavigate } from 'react-router-dom'

interface Artist {
  name: string
  display_name: string
  image_url: string
  theme_color?: string
}

interface ArtistCardProps {
  artist: Artist
  position: [number, number, number]
}

export default function ArtistCard({ artist, position }: ArtistCardProps) {
  const groupRef = useRef<THREE.Group>(null)
  const [hovered, setHovered] = useState(false)
  const navigate = useNavigate()

  const targetScale = hovered ? 1.05 : 1
  const targetZ = hovered ? position[2] + 0.5 : position[2]

  useFrame((_, delta) => {
    if (groupRef.current) {
      // Smooth scaling and movement
      groupRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), delta * 10)
      groupRef.current.position.z = THREE.MathUtils.lerp(groupRef.current.position.z, targetZ, delta * 10)
    }
  })

  return (
    <group
      ref={groupRef}
      position={position}
      onPointerOver={() => {
        setHovered(true)
        document.body.style.cursor = 'pointer'
      }}
      onPointerOut={() => {
        setHovered(false)
        document.body.style.cursor = 'auto'
      }}
      onClick={(e) => {
        e.stopPropagation()
        navigate(`/artist/${artist.name}`)
      }}
    >
      {/* 16:10 aspect ratio image approximately */}
      <Image
        url={artist.image_url}
        transparent
        opacity={1}
        scale={[3.2, 2.0]}
        position={[0, 0, 0]}
      />
      
      {/* Artist Name */}
      <Text
        position={[0, -1.3, 0.1]}
        fontSize={0.25}
        color={artist.theme_color || '#ffffff'}
        anchorX="center"
        anchorY="top"
        fontWeight="bold"
        outlineWidth={0.02}
        outlineColor="#000000"
      >
        {artist.display_name}
      </Text>
    </group>
  )
}
