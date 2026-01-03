import { SimplexNoise } from '@paper-design/shaders-react'

export default function App() {
  return (
    <div style={{ position: 'fixed', inset: 0 }}>
      <SimplexNoise
        width="100%"
        height="100%"
        colors={["#4449cf", "#ffd1e0", "#f94346", "#ffd36b", "#ffffff"]}
        stepsPerColor={2}
        softness={0}
        speed={0.5}
        scale={0.6}
        fit="cover"
        maxPixelCount={2200000}
      />
    </div>
  )
}
