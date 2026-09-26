export const chapters = [
  { id: 'intro', label: 'Introduction', weight: 1 },
  { id: 'discover', label: 'Discovery', weight: 1 },
  { id: 'scenarios', label: 'Scenarios', weight: 1.4 },
  { id: 'assumptions', label: 'Assumptions', weight: 1.4 },
  { id: 'news', label: 'News', weight: 1.25 },
  { id: 'evidence', label: 'Evidence', weight: 1 },
  { id: 'portfolio', label: 'Portfolio', weight: 1 },
  { id: 'insights', label: 'AI Insights', weight: 1 },
  { id: 'continue', label: 'FinSight', weight: 1 },
] as const

export const clamp = (n: number, min = 0, max = 1) => Math.max(min, Math.min(max, n))
export const smooth = (n: number) => { const t = clamp(n); return t * t * (3 - 2 * t) }
export const totalWeight = chapters.reduce((sum, chapter) => sum + chapter.weight, 0)
export const chapterStart = (index: number) => chapters.slice(0, index).reduce((sum, chapter) => sum + chapter.weight, 0) / totalWeight

// Shared boundary poses. Each chapter travels from one pose to the next; unlike
// an entrance-only animation, every scroll increment changes the composition.
const poses = [
  { yaw:-18, pitch:12, roll:-4, scale:0.78, x:40, y:28, spread:0.3 },
  { yaw:7, pitch:-3, roll:2, scale:0.97, x:-12, y:-18, spread:0.06 },
  { yaw:-8, pitch:4, roll:-2, scale:0.94, x:18, y:12, spread:0.08 },
  { yaw:13, pitch:8, roll:2, scale:0.88, x:-20, y:-14, spread:0.24 },
  { yaw:0, pitch:0, roll:0, scale:0.98, x:0, y:0, spread:0.05 },
  { yaw:-12, pitch:9, roll:-2, scale:0.88, x:10, y:12, spread:0.4 },
  { yaw:10, pitch:-4, roll:2, scale:0.92, x:-8, y:-14, spread:0.08 },
  { yaw:-6, pitch:5, roll:-2, scale:0.9, x:14, y:8, spread:0.14 },
  { yaw:0, pitch:0, roll:0, scale:0.9, x:0, y:12, spread:0.22 },
  { yaw:0, pitch:0, roll:0, scale:1, x:0, y:-10, spread:0.02 },
]

// Pure and reversible. No previous frame, clock, financial formula or account state.
export function sampleTimeline(progress: number, sampleCount = 25) {
  const position = clamp(progress) * totalWeight
  let start = 0
  let index = chapters.length - 1
  for (let i = 0; i < chapters.length; i++) {
    if (position < start + chapters[i].weight || i === chapters.length - 1) { index = i; break }
    start += chapters[i].weight
  }
  const local = clamp((position - start) / chapters[index].weight)
  const action = local
  const reveal = 0.2 * local + 0.8 * smooth(local)
  const scenario = index === 2 ? Math.min(2, Math.floor(action * 3)) : 1
  const calculatorSample = index === 3 ? Math.round(action * (sampleCount - 1)) : 0
  const day = index === 4 ? Math.min(6, Math.floor(action * 7)) : 0
  const from = poses[index], to = poses[index + 1]
  const blend = (key: keyof typeof from) => from[key] + (to[key] - from[key]) * reveal
  return {
    progress: clamp(progress), index, local, action, reveal, scenario, calculatorSample, day,
    query: index === 1 ? 'AAPL'.slice(0, Math.floor(action * 5)) : 'AAPL',
    added: index === 6 && action >= 0.35,
    yaw:blend('yaw'), pitch:blend('pitch'), roll:blend('roll'),
    scale:blend('scale'), x:blend('x'), y:blend('y'), spread:blend('spread'),
  }
}

export type WalkthroughState = ReturnType<typeof sampleTimeline>
