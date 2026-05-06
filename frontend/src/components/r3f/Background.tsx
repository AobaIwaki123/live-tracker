import Particles from './Particles'
import Orbs from './Orbs'
import Rings from './Rings'

export default function Background() {
  return (
    <group>
      <Particles />
      <Orbs />
      <Rings />
    </group>
  )
}
