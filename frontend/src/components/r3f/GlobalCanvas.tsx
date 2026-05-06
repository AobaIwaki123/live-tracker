import { Canvas } from '@react-three/fiber'
import * as THREE from 'three'
import { useLocation } from 'react-router-dom'
import { ScrollControls } from '@react-three/drei'
import Background from './Background'
import ArtistGrid from './ArtistGrid'

export default function GlobalCanvas() {
  const location = useLocation()
  const isHome = location.pathname === '/'

  return (
    <div className="fixed inset-0 z-[-1] bg-[#050010]">
      <Canvas
        camera={{ position: [0, 0, 7], fov: 60 }}
        gl={{
          antialias: true,
          alpha: false,
          toneMapping: THREE.ACESFilmicToneMapping,
        }}
        dpr={Math.min(window.devicePixelRatio, 2)}
      >
        <color attach="background" args={[0x080012]} />
        <Background />
        
        {isHome && (
          <ScrollControls pages={3} damping={0.25} distance={1}>
            <ArtistGrid />
          </ScrollControls>
        )}
      </Canvas>
    </div>
  )
}
