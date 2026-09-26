import * as THREE from 'three'
import type { WalkthroughState } from './timeline'

/** Decorative backplates only. The complete product presentation lives in HTML. */
export function createScene(canvas: HTMLCanvasElement, onFailure: () => void) {
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: 'low-power' })
  renderer.setClearColor(0xffffff, 0)
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 40)
  camera.position.set(0, 0, 9)
  const ambient = new THREE.HemisphereLight(0xffffff, 0xb5b5b5, 2.7)
  scene.add(ambient)
  const light = new THREE.DirectionalLight(0xffffff, 3)
  light.position.set(-3, 6, 7)
  light.castShadow = true
  light.shadow.mapSize.set(512, 512)
  light.shadow.camera.left = -6
  light.shadow.camera.right = 6
  light.shadow.camera.top = 6
  light.shadow.camera.bottom = -6
  light.shadow.normalBias = 0.04
  light.shadow.radius = 4
  scene.add(light)
  const group = new THREE.Group()
  scene.add(group)
  const shape = new THREE.Shape()
  const x = -2.75, y = -1.875, w = 5.5, h = 3.75, radius = 0.12
  shape.moveTo(x + radius, y)
  shape.lineTo(x + w - radius, y)
  shape.quadraticCurveTo(x + w, y, x + w, y + radius)
  shape.lineTo(x + w, y + h - radius)
  shape.quadraticCurveTo(x + w, y + h, x + w - radius, y + h)
  shape.lineTo(x + radius, y + h)
  shape.quadraticCurveTo(x, y + h, x, y + h - radius)
  shape.lineTo(x, y + radius)
  shape.quadraticCurveTo(x, y, x + radius, y)
  const geometry = new THREE.ExtrudeGeometry(shape, { depth:0.02, bevelEnabled:false, curveSegments:6 })
  const materials = [0xf5f5f5, 0xececec, 0xe3e3e3].map(color => new THREE.MeshStandardMaterial({ color, roughness: 0.5, metalness: 0.05 }))
  const plates = materials.map((material, i) => {
    const plate = new THREE.Mesh(geometry, material)
    plate.position.z = -0.28 - i * 0.3
    plate.castShadow = true
    plate.receiveShadow = true
    group.add(plate)
    return plate
  })
  const floorGeometry = new THREE.PlaneGeometry(30, 30)
  const floorMaterial = new THREE.ShadowMaterial({ opacity: 0.025 })
  const floor = new THREE.Mesh(floorGeometry, floorMaterial)
  floor.rotation.x = -Math.PI / 2
  floor.position.y = -2.65
  floor.receiveShadow = true
  scene.add(floor)
  let disposed = false
  let width = 0
  let height = 0
  const lost = (event: Event) => { event.preventDefault(); onFailure() }
  canvas.addEventListener('webglcontextlost', lost)

  return {
    render(state: WalkthroughState, mobile: boolean) {
      if (disposed || document.hidden) return
      const start = performance.now()
      const w = canvas.clientWidth, h = canvas.clientHeight
      if (!w || !h) return
      const dpr = Math.min(window.devicePixelRatio || 1, mobile ? 1 : 1.5)
      if (w !== width || h !== height || renderer.getPixelRatio() !== dpr) {
        width = w; height = h
        renderer.setPixelRatio(dpr)
        renderer.setSize(w, h, false)
        camera.aspect = w / h
        camera.updateProjectionMatrix()
      }
      const restraint = mobile ? 0.35 : 1
      group.rotation.set(state.pitch * Math.PI / 180 * restraint, state.yaw * Math.PI / 180 * restraint, -state.roll * Math.PI / 180 * restraint)
      camera.position.z = mobile ? 10 : 9
      const worldHeight = 2 * camera.position.z * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))
      const worldWidth = worldHeight * camera.aspect
      const html = canvas.parentElement?.querySelector<HTMLElement>('.wt-stage-panel')
      if (html) {
        group.scale.set(html.offsetWidth / w * worldWidth / 5.5 * state.scale, html.offsetHeight / h * worldHeight / 3.75 * state.scale, 1)
        group.position.set(((html.offsetLeft + html.offsetWidth / 2 + state.x * restraint) / w - 0.5) * worldWidth, (0.5 - (html.offsetTop + html.offsetHeight / 2 + state.y * restraint) / h) * worldHeight, 0)
      }
      const separation = state.spread
      plates.forEach((plate, index) => {
        plate.position.x = index * separation
        plate.position.y = index * separation
        plate.position.z = -0.3 - index * (separation + 0.15)
      })
      camera.lookAt(0, 0, 0)
      renderer.render(scene, camera)
      // Read-only QA counters; duration is CPU submission time, not a universal FPS claim.
      canvas.dataset.renderMs = (performance.now() - start).toFixed(2)
      canvas.dataset.renders = String(Number(canvas.dataset.renders || 0) + 1)
      canvas.dataset.dpr = String(dpr)
    },
    dispose() {
      disposed = true
      canvas.removeEventListener('webglcontextlost', lost)
      geometry.dispose(); materials.forEach(material => material.dispose())
      floorGeometry.dispose(); floorMaterial.dispose()
      light.shadow.map?.dispose()
      renderer.dispose()
    },
  }
}
